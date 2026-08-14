import os, time, io, requests, json, threading
from flask import Flask, Response, render_template_string, redirect, request
import telebot
from telebot import types
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz
from datetime import datetime
import pandas as pd

TOKEN=os.environ.get("TELEGRAM_TOKEN","").strip(); URL=os.environ.get("RENDER_EXTERNAL_URL","").strip().rstrip("/")
ALL_SYMS=["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]
SYMBOLS_YF={"XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
CAPITAL=5000; BOLA_N1=500; BOLA_N2=750; BOLA_NY=1750; TP_PCT=1.5; TRAIL_PCT=1.0; SL_PCT=-12.0; RSI_BUY=44; NY_PCT=0.15

bot=telebot.TeleBot(TOKEN, threaded=False); app=Flask(__name__)
TZ_MX=pytz.timezone("America/Mexico_City"); TZ_NY=pytz.timezone("America/New_York")
STATE_FILE="/tmp/state.json"; POS_FILE="/tmp/positions.json"; GAIN_FILE="/tmp/gains.json"; NY_FILE="/tmp/ny.json"

def load_json(f,d):
    try: return json.load(open(f))
    except: return d
def save_json(f,data):
    try: json.dump(data, open(f,"w"))
    except: pass

chart_cache={}; data_cache={"prices":{},"rsis":{},"time":0}

def rsi_calc(s,p=14):
    try: d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean(); rs=g/l; return 100-(100/(1+rs))
    except: return pd.Series([50]*len(s))

def get_kraken_price(sym):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}", timeout=6).json()
        # result keys: XXBTZUSD etc
        for k,v in r['result'].items():
            if k!='last': return float(v['c'][0])
        return None
    except: return None

def get_kraken_history(sym):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        url=f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        r=requests.get(url, timeout=12).json()
        if 'result' not in r: return None
        ohlc=None
        for key,val in r['result'].items():
            if key!='last' and isinstance(val, list) and len(val)>0:
                ohlc=val; break
        if not ohlc: return None
        # ohlc = [time, open, high, low, close, vwap, vol, count]
        df=pd.DataFrame(ohlc, columns=['time','open','high','low','close','vwap','vol','count'])
        df['Close']=df['close'].astype(float); df['High']=df['high'].astype(float); df['Low']=df['low'].astype(float)
        df['time']=pd.to_datetime(df['time'], unit='s'); df=df.set_index('time')
        return df[['Close','High','Low']].tail(200)
    except Exception as e:
        print(f"kh {sym} {e}")
        return None

def get_yahoo_direct(ticker):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=5d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12).json()
        res=r['chart']['result'][0]; q=res['indicators']['quote'][0]
        df=pd.DataFrame({'Close':q['close'],'High':q['high'],'Low':q['low']}, index=pd.to_datetime(res['timestamp'], unit='s')).dropna()
        return df if len(df)>10 else None
    except Exception as e:
        print(f"yahoo {ticker} {e}")
        return None

def get_all_data():
    if time.time()-data_cache["time"]<12 and data_cache["prices"]: return data_cache["prices"], data_cache["rsis"], data_cache.get("dfs",{})
    prices, rsis, dfs={}, {}, {}
    for k in ["BTC","ETH","SOL"]:
        pr=get_kraken_price(k) or 0; prices[k]=pr
        df=get_kraken_history(k); dfs[k]=df
        if df is not None and len(df)>14:
            rsis[k]=float(rsi_calc(df['Close']).iloc[-1])
        else:
            rsis[k]=50.0
    for k,tick in SYMBOLS_YF.items():
        df=get_yahoo_direct(tick); dfs[k]=df
        if df is not None and len(df)>0:
            prices[k]=float(df['Close'].iloc[-1])
            rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if len(df)>14 else 50.0
        else:
            prices[k]=0; rsis[k]=50.0
    data_cache.update({"prices":prices,"rsis":rsis,"dfs":dfs,"time":time.time()})
    return prices, rsis, dfs

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<45:
        return chart_cache[sym][1]
    try:
        _,_,dfs = get_all_data()
        df = dfs.get(sym)
        if df is None or len(df)<20:
            pr,rs,_ = get_all_data()
            price = pr.get(sym,0); rsi = rs.get(sym,0)
            fig, ax = plt.subplots(figsize=(10,5))
            ax.text(0.5,0.5,f"{sym}\n${price:.2f} RSI {rsi:.1f}\nCargando historial...\nV46.1 DUAL", ha='center', va='center', fontsize=18, transform=ax.transAxes)
            ax.set_axis_off()
            buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=120,bbox_inches='tight'); plt.close(fig); buf.seek(0)
            data=buf.getvalue(); chart_cache[sym]=(now,data); return data

        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        pos=load_json(POS_FILE, {}).get(sym); price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1])
        ny=load_json(NY_FILE, {})

        fig, (ax1, ax2) = plt.subplots(2,1,figsize=(11,6), gridspec_kw={'height_ratios':[3,1]}, sharex=True)
        ax1.plot(df.index, df['Close'], linewidth=2.2, label='Precio')
        ax1.plot(df.index, df['SMA20'], linewidth=1, alpha=.7, label='SMA20')
        ax1.plot(df.index, df['SMA50'], linewidth=1, alpha=.7, label='SMA50')
        entradas=df[df['RSI']<RSI_BUY]
        ax1.scatter(entradas.index, entradas['Close'], marker='^', color='green', s=90, label=f'RSI<{RSI_BUY} $29')
        if sym in ["NVDA","TSLA"] and sym in ny:
            if 'high' in ny[sym]: ax1.axhline(ny[sym]['high'], color='purple', ls='--', lw=2, label=f"E1 HIGH ${ny[sym]['high']:.2f}")
            if 'low' in ny[sym]: ax1.axhline(ny[sym]['low'], color='blue', ls='--', lw=2, label=f"E1 LOW ${ny[sym]['low']:.2f}")
            if 'triple' in ny[sym]: ax1.axhline(ny[sym]['triple'], color='orange', ls=':', lw=2, label=f"E2 Triple ${ny[sym]['triple']:.2f}")
        if pos:
            ax1.axhline(pos['entry'], color='orange', ls='--', lw=2, label=f"Entrada ${pos['entry']:.2f} Bola ${pos['bola']}")
        ax1.set_title(f"{sym} ${price:.2f} RSI {r:.1f} | V46.1 DUAL 7.8+NY TP{TP_PCT}% Trail{TRAIL_PCT}% SL{SL_PCT}%")
        ax1.legend(fontsize=7, loc='upper left'); ax1.grid(True, alpha=.3)
        ax2.plot(df.index, df['RSI'], label='RSI'); ax2.axhline(RSI_BUY, color='green', ls='--', label=f'Compra {RSI_BUY}'); ax2.axhline(70, color='red', ls='--'); ax2.set_ylim(0,100); ax2.legend(fontsize=8); ax2.grid(True, alpha=.3)
        buf=io.BytesIO(); plt.savefig(buf, format='png', dpi=135, bbox_inches='tight'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e:
        print(f"chart {sym} {e}")
        try:
            fig, ax = plt.subplots(figsize=(10,5))
            ax.text(0.5,0.5,f"{sym}\nError: {e}\nV46.1", ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off(); buf=io.BytesIO(); plt.savefig(buf, format='png', dpi=120); plt.close(fig); buf.seek(0); return buf.getvalue()
        except: plt.close('all'); return None

def trading_loop():
    while True:
        try:
            if not load_json(STATE_FILE, {"auto":False}).get("auto", False): time.sleep(10); continue
            prices, rsis, dfs = get_all_data()
            positions=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); ny_data=load_json(NY_FILE, {})
            now_ny=datetime.now(TZ_NY); today=now_ny.strftime("%Y-%m-%d")
            for sym in ALL_SYMS:
                pr=prices.get(sym,0); r=rsis.get(sym,50); df=dfs.get(sym)
                if pr==0 or df is None: continue
                if sym in positions:
                    entry=positions[sym]['entry']; bola=positions[sym]['bola']; max_p=positions[sym].get('max', pr)
                    if pr>max_p: positions[sym]['max']=pr; max_p=pr
                    profit=(pr-entry)/entry*100; trail_drop=(max_p-pr)/max_p*100 if max_p>0 else 0
                    if profit>=TP_PCT or trail_drop>=TRAIL_PCT or profit<=SL_PCT:
                        ganancia=(pr-entry)/entry*bola; gains["total"]+=ganancia; gains["trades"]+=1; save_json(GAIN_FILE, gains)
                        del positions[sym]; save_json(POS_FILE, positions); continue
                # COMPRAS $29
                if sym in ["BTC","ETH","SOL","XAUUSD"]:
                    if r<RSI_BUY and len([s for s in positions if s in ["BTC","ETH","SOL","XAUUSD"]])<2:
                        # Bola correcta: primera $500, segunda $750
                        count=len([s for s in positions if s in ["BTC","ETH","SOL","XAUUSD"]])
                        bola=BOLA_N1 if count==0 else BOLA_N2
                        positions[sym]={'entry':pr, 'max':pr, 'bola':bola, 'strat':'RSI7.8', 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions)
                # COMPRAS NY solo en horario
                if sym in ["NVDA","TSLA"] and now_ny.hour>=7 and now_ny.hour<16:
                    if now_ny.hour==9 and now_ny.minute>=30 and now_ny.minute<35:
                        h=float(df['High'].iloc[-1]); l=float(df['Low'].iloc[-1])
                        ny_data.setdefault(sym, {}); ny_data[sym]['date']=today; ny_data[sym]['high']=h; ny_data[sym]['low']=l; save_json(NY_FILE, ny_data)
                    if 9<=now_ny.hour<=10:
                        if sym in ny_data and ny_data[sym].get('date')==today and 'high' in ny_data[sym]:
                            high=ny_data[sym]['high']; low=ny_data[sym]['low']
                            if (pr>high*(1+NY_PCT/100) or pr<low*(1-NY_PCT/100)) and sym not in positions:
                                positions[sym]={'entry':pr, 'max':pr, 'bola':BOLA_NY, 'strat':'E1 NY', 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions)
            save_json(POS_FILE, positions)
        except Exception as e: print(f"loop {e}")
        time.sleep(20)
threading.Thread(target=trading_loop, daemon=True).start()

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:620px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:620px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff;position:relative}.price{font-size:20px;font-weight:900;color:#58a6ff}.pos{position:absolute;top:6px;right:6px;background:#238636;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px}.strat{position:absolute;bottom:6px;right:6px;background:#8957e5;color:#fff;font-size:9px;padding:2px 6px;border-radius:8px}.box{max-width:620px;margin:18px auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;text-align:left;font-size:13px}.gain{color:#3fb950;font-weight:900}</style></head><body>
<div class="top"><div><b>MAQUINA V46.1 DUAL 7.8 + NY FIX</b><br><small>Cap $5000 | $29: $500/$750 RSI44 TP1.5 Trail1 | NY: $1750 9:30 Triple</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | V46.1 DUAL $29 + NY 1750 | Kraken FIX graficas vivas</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}">{% if s in positions %}<span class="pos">EN POS</span><span class="strat">{{positions[s].strat}}</span>{% endif %}<h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div>{% if s in positions %}<small>Ent ${{"%.2f"|format(positions[s].entry)}} Bola ${{positions[s].bola}}</small>{% endif %}{% if s in ny and s in ["NVDA","TSLA"] %}<br><small style="color:#d2a8ff">E1 H ${{"%.2f"|format(ny[s].high) if ny[s].high is defined else 0}} L ${{"%.2f"|format(ny[s].low) if ny[s].low is defined else 0}}</small>{% endif %}</a>{% endfor %}
</div>
<div class="box">
<b>📊 ENTRADAS Y GANANCIAS - V46.1 DUAL</b><br><br>
{% if positions %}{% for s,p in positions.items() %}🟢 {{s}} [{{p.strat}}]: Ent ${{"%.2f"|format(p.entry)}} | Ahora ${{prices[s]}} | Bola ${{p.bola}} | {{ "%.2f"|format((prices[s]|replace('$','')|replace('CARGANDO','0')|float - p.entry)/p.entry*100 if prices[s]!='CARGANDO' else 0) }}%<br>{% endfor %}{% else %}Sin posiciones - Esperando RSI<44 para $29 o ruptura 9:30 NY (solo dia)<br>{% endif %}<br>
<b>💰 GANANCIA HOY:</b> <span class="gain">${{"%.2f"|format(gains.total)}} en {{gains.trades}} trades</span><br>
<b>Estrategia:</b> $29 RSI<44 24/7 | NY E1/E2 solo 7:30AM-4PM MX (9:30-4PM NY)<br>
<b>Gráficas:</b> Toca tarjeta = viva SMA20/50 + flechas verdes + HIGH/LOW morada/azul
</div>
</body></html>"""

@app.route('/')
def home():
    pr,rs,dfs=get_all_data(); pos=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); ny=load_json(NY_FILE, {})
    return render_template_string(HTML, syms=ALL_SYMS, auto=load_json(STATE_FILE,{"auto":False}).get("auto",False), hora=datetime.now(TZ_MX).strftime("%H:%M:%S"), positions=pos, gains=gains, ny=ny, prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})
@app.route('/toggle')
def tog(): s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); return redirect('/')
@app.route('/chart/<sym>')
def ch(sym):
    d=chart_bytes(sym.upper())
    return Response(d,mimetype='image/png') if d else ("Error",500)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook(): json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''
@bot.message_handler(commands=['start','balance'])
def start(m):
    pos=load_json(POS_FILE,{}); auto=load_json(STATE_FILE,{"auto":False}).get("auto",False); pr,rs,_=get_all_data(); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); txt=""
    for s,p in pos.items(): txt+=f"\n{s} [{p.get('strat','')}]: ${p['entry']:.2f}->{pr.get(s,0):.2f} Bola ${p['bola']}"
    if not txt: txt="\nSin posiciones"
    msg=f"✅ V46.1 DUAL 7.8+NY FIX\n{'🟢AUTO ON' if auto else '🔴AUTO OFF'} Cap ${CAPITAL}\n$29: RSI<{RSI_BUY} Bola {BOLA_N1}/{BOLA_N2} 24/7\nNY: E1+E2 Bola ${BOLA_NY} solo dia 7:30-16:00 MX\nGanancia: ${gains['total']:.2f} {gains['trades']} trades{txt}\n{URL}"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if auto else 'OFF'}","DASHBOARD"); bot.send_message(m.chat.id, msg, reply_markup=kb)
@bot.message_handler(func=lambda m: True)
def allh(m):
    t=m.text.upper().strip()
    if "AUTO" in t: s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); bot.send_message(m.chat.id,f"{'🟢AUTO ON V46.1' if s['auto'] else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in ALL_SYMS: d=chart_bytes(t); pr,rs,_=get_all_data(); bot.send_photo(m.chat.id,d,caption=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} V46.1") if d else bot.send_message(m.chat.id,f"{t} cargando")
try:
    if URL: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V46.1 OK")
except Exception as e: print(e)
app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
