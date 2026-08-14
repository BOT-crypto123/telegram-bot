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
import numpy as np

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
        for k,v in r['result'].items():
            if k!='last': return float(v['c'][0])
        return None
    except: return None

def get_kraken_history(sym):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        url=f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        r=requests.get(url, timeout=12).json()
        ohlc=None
        for key,val in r['result'].items():
            if key!='last' and isinstance(val, list) and len(val)>0: ohlc=val; break
        if not ohlc: return None
        df=pd.DataFrame(ohlc, columns=['time','open','high','low','close','vwap','vol','count'])
        df['Close']=df['close'].astype(float); df['High']=df['high'].astype(float); df['Low']=df['low'].astype(float); df['Open']=df['open'].astype(float)
        df['time']=pd.to_datetime(df['time'], unit='s'); df=df.set_index('time')
        return df.tail(250)
    except Exception as e: print(f"kh {sym} {e}"); return None

def get_yahoo_direct(ticker):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=5d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12).json()
        res=r['chart']['result'][0]; q=res['indicators']['quote'][0]
        df=pd.DataFrame({'Close':q['close'],'High':q['high'],'Low':q['low'],'Open':q['open']}, index=pd.to_datetime(res['timestamp'], unit='s')).dropna()
        return df if len(df)>10 else None
    except: return None

def get_all_data():
    if time.time()-data_cache["time"]<12 and data_cache["prices"]: return data_cache["prices"], data_cache["rsis"], data_cache.get("dfs",{})
    prices, rsis, dfs={}, {}, {}
    for k in ["BTC","ETH","SOL"]:
        pr=get_kraken_price(k) or 0; prices[k]=pr
        df=get_kraken_history(k); dfs[k]=df
        rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if df is not None and len(df)>14 else 50.0
    for k,tick in SYMBOLS_YF.items():
        df=get_yahoo_direct(tick); dfs[k]=df
        if df is not None and len(df)>0:
            prices[k]=float(df['Close'].iloc[-1]); rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if len(df)>14 else 50.0
        else: prices[k]=0; rsis[k]=50.0
    data_cache.update({"prices":prices,"rsis":rsis,"dfs":dfs,"time":time.time()}); return prices, rsis, dfs

def chart_bytes_pro(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<40: return chart_cache[sym][1]
    try:
        _,_,dfs=get_all_data(); df=dfs.get(sym)
        if df is None or len(df)<30:
            pr,rs,_=get_all_data(); price=pr.get(sym,0)
            fig, ax=plt.subplots(figsize=(12,6)); ax.text(0.5,0.5,f"{sym}\n${price:.2f}\nCargando PRO...", ha='center', va='center', fontsize=18, transform=ax.transAxes); ax.set_axis_off()
            buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=130,bbox_inches='tight'); plt.close(fig); buf.seek(0); data=buf.getvalue(); chart_cache[sym]=(now,data); return data

        # INDICADORES PRO
        df['RSI']=rsi_calc(df['Close'])
        df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean(); df['SMA200']=df['Close'].rolling(100).mean()
        df['EMA20']=df['Close'].ewm(span=20).mean(); df['EMA50']=df['Close'].ewm(span=50).mean()
        df['STD']=df['Close'].rolling(20).std(); df['BB_UP']=df['SMA20']+2*df['STD']; df['BB_LOW']=df['SMA20']-2*df['STD']

        pos=load_json(POS_FILE, {}).get(sym); price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1]); ny=load_json(NY_FILE, {}).get(sym,{})

        # GRAFICA PRO 3 PANELES
        fig, (ax1, ax2, ax3) = plt.subplots(3,1,figsize=(13,8), gridspec_kw={'height_ratios':[3,1,1]}, sharex=True)

        # PANEL 1 - PRECIO + TODAS LAS LINEAS
        ax1.plot(df.index, df['Close'], linewidth=2.4, color='white', label=f'Precio ${price:.2f}')
        ax1.plot(df.index, df['SMA20'], linewidth=1.2, color='#f1c40f', alpha=0.9, label='SMA20')
        ax1.plot(df.index, df['SMA50'], linewidth=1.2, color='#e74c3c', alpha=0.9, label='SMA50')
        ax1.plot(df.index, df['SMA200'], linewidth=1, color='#8e44ad', alpha=0.6, label='SMA100')
        ax1.plot(df.index, df['EMA20'], linewidth=1, color='#3498db', ls='--', alpha=0.8, label='EMA20')
        ax1.plot(df.index, df['EMA50'], linewidth=1, color='#2ecc71', ls='--', alpha=0.8, label='EMA50')
        # Bollinger
        ax1.fill_between(df.index, df['BB_UP'], df['BB_LOW'], color='gray', alpha=0.1, label='Bollinger')
        ax1.plot(df.index, df['BB_UP'], linewidth=0.6, color='gray', alpha=0.5); ax1.plot(df.index, df['BB_LOW'], linewidth=0.6, color='gray', alpha=0.5)

        # Entradas RSI
        entradas=df[df['RSI']<44]
        ax1.scatter(entradas.index, entradas['Close'], marker='^', color='#00ff00', s=100, edgecolors='black', zorder=5, label=f'RSI<{44} $29')
        # Salidas TP
        salidas=df[df['RSI']>70]
        ax1.scatter(salidas.index, salidas['Close'], marker='v', color='#ff0000', s=80, zorder=5, label='RSI>70 VENTA')

        # LINEAS NY
        if sym in ["NVDA","TSLA"] and ny:
            if 'high' in ny: ax1.axhline(ny['high'], color='#9b59b6', ls='--', lw=2.5, label=f"E1 HIGH ${ny['high']:.2f} MORADA")
            if 'low' in ny: ax1.axhline(ny['low'], color='#3498db', ls='--', lw=2.5, label=f"E1 LOW ${ny['low']:.2f} AZUL")
            if 'triple' in ny: ax1.axhline(ny['triple'], color='#f39c12', ls=':', lw=2.5, label=f"E2 Triple ${ny['triple']:.2f} NARANJA")
            if 'ob' in ny: ax1.axhline(ny['ob'], color='#e67e22', ls='-.', lw=2, label=f"Order Block ${ny['ob']:.2f}")

        # Posicion
        if pos:
            ax1.axhline(pos['entry'], color='#f1c40f', ls='-', lw=2.5, label=f"TU ENTRADA ${pos['entry']:.2f} Bola ${pos['bola']} {pos['strat']}")
            # TP y SL lineas
            tp_line=pos['entry']*1.015; sl_line=pos['entry']*0.88
            ax1.axhline(tp_line, color='#2ecc71', ls=':', lw=1.5, alpha=0.7, label=f"TP 1.5% ${tp_line:.2f}")
            ax1.axhline(sl_line, color='#e74c3c', ls=':', lw=1.5, alpha=0.7, label=f"SL -12% ${sl_line:.2f}")
            # Trail
            max_p=pos.get('max', pos['entry']); trail_line=max_p*0.99
            if max_p>pos['entry']: ax1.axhline(trail_line, color='#2ecc71', ls='-.', lw=1.2, alpha=0.6, label=f"Trail 1% ${trail_line:.2f}")

        ax1.set_title(f"{sym} ${price:.2f} RSI {r:.1f} | V46.2 PRO - MAQUINA 7.8+NY - TP{TP_PCT}% Trail{TRAIL_PCT}% SL{SL_PCT}%", fontsize=11, color='white', fontweight='bold')
        ax1.legend(fontsize=6.5, loc='upper left', ncol=3, facecolor='#161b22', edgecolor='white'); ax1.grid(True, alpha=0.2, color='white'); ax1.set_facecolor('#0d1117'); ax1.tick_params(colors='white')

        # PANEL 2 - RSI PRO
        ax2.plot(df.index, df['RSI'], color='#9b59b6', linewidth=1.5, label='RSI')
        ax2.axhline(44, color='#00ff00', ls='--', lw=1.5, label='Compra 44'); ax2.axhline(70, color='#ff0000', ls='--', lw=1.2, label='Venta 70'); ax2.axhline(30, color='green', ls=':', lw=1, alpha=0.5); ax2.axhline(50, color='white', ls=':', lw=0.8, alpha=0.3)
        ax2.fill_between(df.index, 0, 44, color='green', alpha=0.1); ax2.fill_between(df.index, 70, 100, color='red', alpha=0.1)
        ax2.set_ylim(0,100); ax2.legend(fontsize=7, loc='upper left'); ax2.grid(True, alpha=0.2); ax2.set_facecolor('#0d1117'); ax2.tick_params(colors='white')

        # PANEL 3 - VOLUMEN / Momentum
        mom=df['Close'].diff(5); ax3.bar(df.index, mom, color=np.where(mom>0, '#2ecc71', '#e74c3c'), alpha=0.6, label='Momentum 5')
        ax3.axhline(0, color='white', lw=0.8); ax3.legend(fontsize=7); ax3.grid(True, alpha=0.2); ax3.set_facecolor('#0d1117'); ax3.tick_params(colors='white')

        fig.patch.set_facecolor('#0d1117'); buf=io.BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e:
        print(f"chart pro {sym} {e}"); import traceback; traceback.print_exc()
        fig, ax=plt.subplots(figsize=(12,6)); ax.text(0.5,0.5,f"Error {sym}\n{e}\nV46.2 PRO", ha='center', va='center', transform=ax.transAxes, color='white'); ax.set_facecolor('#0d1117'); fig.patch.set_facecolor('#0d1117')
        buf=io.BytesIO(); plt.savefig(buf, format='png', dpi=120); plt.close(fig); buf.seek(0); return buf.getvalue()

def trading_loop():
    while True:
        try:
            if not load_json(STATE_FILE, {"auto":False}).get("auto", False): time.sleep(10); continue
            prices, rsis, dfs=get_all_data(); positions=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); ny_data=load_json(NY_FILE, {})
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
                if sym in ["BTC","ETH","SOL","XAUUSD"]:
                    if r<RSI_BUY and len([s for s in positions if s in ["BTC","ETH","SOL","XAUUSD"]])<2:
                        count=len([s for s in positions if s in ["BTC","ETH","SOL","XAUUSD"]]); bola=BOLA_N1 if count==0 else BOLA_N2
                        positions[sym]={'entry':pr, 'max':pr, 'bola':bola, 'strat':'RSI7.8', 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions)
                if sym in ["NVDA","TSLA"] and 7<=now_ny.hour<16:
                    if now_ny.hour==9 and 30<=now_ny.minute<35:
                        h=float(df['High'].iloc[-1]); l=float(df['Low'].iloc[-1])
                        ny_data.setdefault(sym, {}); ny_data[sym]['date']=today; ny_data[sym]['high']=h; ny_data[sym]['low']=l; save_json(NY_FILE, ny_data)
                    if 9<=now_ny.hour<=10 and sym in ny_data and ny_data[sym].get('date')==today and 'high' in ny_data[sym]:
                        high=ny_data[sym]['high']; low=ny_data[sym]['low']
                        if (pr>high*(1+NY_PCT/100) or pr<low*(1-NY_PCT/100)) and sym not in positions:
                            positions[sym]={'entry':pr, 'max':pr, 'bola':BOLA_NY, 'strat':'E1 NY', 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions)
            save_json(POS_FILE, positions)
        except Exception as e: print(f"loop {e}")
        time.sleep(20)
threading.Thread(target=trading_loop, daemon=True).start()

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="25">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:680px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:680px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff;position:relative}.price{font-size:20px;font-weight:900;color:#58a6ff}.pos{position:absolute;top:6px;right:6px;background:#238636;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px}.strat{position:absolute;bottom:6px;right:6px;background:#8957e5;color:#fff;font-size:9px;padding:2px 6px;border-radius:8px}.box{max-width:680px;margin:18px auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;text-align:left;font-size:13px}.gain{color:#3fb950;font-weight:900}.pro{color:#f1c40f;font-weight:900}</style></head><body>
<div class="top"><div><b class="pro">MAQUINA V46.2 PRO EN VIVO</b><br><small>Cap $5000 | $29: $500/$750 RSI44 TP1.5 Trail1 | NY: $1750 E1 9:30 + E2 Triple | PRO SMA/EMA/BB</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | V46.2 PRO - TODAS LAS LINEAS VIVAS | Kraken FIX</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}">{% if s in positions %}<span class="pos">EN POS</span><span class="strat">{{positions[s].strat}}</span>{% endif %}<h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div>{% if s in positions %}<small>Ent ${{"%.2f"|format(positions[s].entry)}} Bola ${{positions[s].bola}}</small>{% endif %}{% if s in ny and s in ["NVDA","TSLA"] %}<br><small style="color:#d2a8ff">E1 H ${{"%.2f"|format(ny[s].high) if ny[s].high is defined else 0}} L ${{"%.2f"|format(ny[s].low) if ny[s].low is defined else 0}}</small>{% endif %}</a>{% endfor %}
</div>
<div class="box">
<b>📊 ENTRADAS Y GANANCIAS - V46.2 PRO</b><br><br>
{% if positions %}{% for s,p in positions.items() %}🟢 {{s}} [{{p.strat}}]: Ent ${{"%.2f"|format(p.entry)}} | Ahora ${{prices[s]}} | Bola ${{p.bola}} | {{ "%.2f"|format((prices[s]|replace('$','')|replace('CARGANDO','0')|float - p.entry)/p.entry*100 if prices[s]!='CARGANDO' else 0) }}%<br>{% endfor %}{% else %}Sin posiciones - Esperando RSI<44 para $29 o ruptura 9:30 NY<br>{% endif %}<br>
<b>💰 GANANCIA HOY:</b> <span class="gain">${{"%.2f"|format(gains.total)}} en {{gains.trades}} trades</span><br>
<b class="pro">🔥 MODO PRO EN VIVO - TODAS LAS LINEAS:</b><br>
- Blanca: Precio | Amarilla: SMA20 | Roja: SMA50 | Morada: SMA100<br>
- Azul --: EMA20 | Verde --: EMA50 | Gris: Bollinger Bands<br>
- Verde ^: Entradas RSI<44 | Rojo v: Ventas RSI>70<br>
- Morada --: E1 HIGH NY | Azul --: E1 LOW NY | Naranja :: Triple | Naranja -.: Order Block<br>
- Amarilla -: Tu Entrada + Bola | Verde :: TP 1.5% | Rojo :: SL -12% | Verde -.: Trail 1%<br>
- RSI abajo: verde compra 44, rojo venta 70 + Momentum<br>
</div>
</body></html>"""

@app.route('/')
def home():
    pr,rs,dfs=get_all_data(); pos=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); ny=load_json(NY_FILE, {})
    return render_template_string(HTML, syms=ALL_SYMS, auto=load_json(STATE_FILE,{"auto":False}).get("auto",False), hora=datetime.now(TZ_MX).strftime("%H:%M:%S"), positions=pos, gains=gains, ny=ny, prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})
@app.route('/toggle')
def tog(): s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); return redirect('/')
@app.route('/chart/<sym>')
def ch(sym): d=chart_bytes_pro(sym.upper()); return Response(d,mimetype='image/png') if d else ("Error",500)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook(): json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''
@bot.message_handler(commands=['start','balance'])
def start(m):
    pos=load_json(POS_FILE,{}); auto=load_json(STATE_FILE,{"auto":False}).get("auto",False); pr,rs,_=get_all_data(); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); txt=""
    for s,p in pos.items(): txt+=f"\n{s} [{p.get('strat','')}]: ${p['entry']:.2f}->{pr.get(s,0):.2f} Bola ${p['bola']}"
    if not txt: txt="\nSin posiciones"
    msg=f"✅ V46.2 PRO EN VIVO\n{'🟢AUTO ON' if auto else '🔴AUTO OFF'} Cap ${CAPITAL}\n$29 RSI<{RSI_BUY} 24/7 | NY E1+E2 ${BOLA_NY} solo dia\nGanancia: ${gains['total']:.2f} {gains['trades']} trades{txt}\n{URL}"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if auto else 'OFF'}","DASHBOARD"); bot.send_message(m.chat.id, msg, reply_markup=kb)
@bot.message_handler(func=lambda m: True)
def allh(m):
    t=m.text.upper().strip()
    if "AUTO" in t: s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); bot.send_message(m.chat.id,f"{'🟢AUTO ON PRO' if s['auto'] else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in ALL_SYMS: d=chart_bytes_pro(t); pr,rs,_=get_all_data(); bot.send_photo(m.chat.id,d,caption=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} PRO") if d else bot.send_message(m.chat.id,f"{t} cargando")
try:
    if URL: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V46.2 PRO OK")
except Exception as e: print(e)
app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
