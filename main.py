import os, time, io, requests, json, threading
from flask import Flask, Response, render_template_string, redirect, request
import telebot
from telebot import types
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

TOKEN=os.environ.get("TELEGRAM_TOKEN","").strip()
URL=os.environ.get("RENDER_EXTERNAL_URL","").strip().rstrip("/")
CHAT_ID_FILE="/tmp/chat_id.txt"
ALL_SYMS=["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]
SYMBOLS_YF={"XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
CAPITAL=5000; BOLA_BASE1=500; BOLA_BASE2=750; BOLA_NY_BASE=1750
TP_PCT=1.5; TRAIL_PCT=1.0; SL_PCT=-12.0; RSI_BUY=44; NY_PCT=0.15
TOPE_B1=1500; TOPE_B2=2250; TOPE_NY=4000

bot=telebot.TeleBot(TOKEN, threaded=False)
app=Flask(__name__)

# ========== FIX RENDER 404 - NO TOCAR ==========
@app.route('/', methods=['GET','POST','HEAD'])
def home_root():
    pr,rs,dfs=get_all_data(); pos=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0,"loss_streak":0}); b1,b2,bny,total=get_bolas_snowball(); hist=load_json(HIST_FILE, [])
    return render_template_string(HTML_DASH, syms=ALL_SYMS, auto=load_json(STATE_FILE,{"auto":False}).get("auto",False), hora=datetime.now(TZ_MX).strftime("%H:%M:%S"), positions=pos, gains=gains, b1=b1, b2=b2, bny=bny, prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()}, historial=hist)

@app.route('/<path:path>', methods=['GET','POST','HEAD'])
def catch_all(path):
    return "OK", 200
# ===============================================

TZ_MX=pytz.timezone("America/Mexico_City")
TZ_NY=pytz.timezone("America/New_York")
STATE_FILE="/tmp/state.json"; POS_FILE="/tmp/positions.json"; GAIN_FILE="/tmp/gains.json"; NY_FILE="/tmp/ny.json"; HIST_FILE="/tmp/historial.json"

def load_json(f,d):
    try: return json.load(open(f))
    except: return d
def save_json(f,data):
    try: json.dump(data, open(f,"w"))
    except: pass
def notify(msg):
    try:
        if os.path.exists(CHAT_ID_FILE):
            cid=open(CHAT_ID_FILE).read().strip()
            if cid: bot.send_message(int(cid), msg)
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

def get_kraken_history(sym, days=8):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        interval = 15 if days<=3 else (60 if days<=5 else 240)
        url=f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
        r=requests.get(url, timeout=12).json()
        ohlc=None
        for key,val in r['result'].items():
            if key!='last' and isinstance(val, list) and len(val)>0: ohlc=val; break
        if not ohlc: return None
        df=pd.DataFrame(ohlc, columns=['time','open','high','low','close','vwap','vol','count'])
        df['Close']=df['close'].astype(float); df['High']=df['high'].astype(float); df['Low']=df['low'].astype(float); df['Open']=df['open'].astype(float)
        df['time']=pd.to_datetime(df['time'], unit='s'); df=df.set_index('time')
        cutoff = datetime.now(pytz.utc) - timedelta(days=days+1)
        df = df[df.index >= cutoff]
        return df.tail(500)
    except: return None

def get_yahoo_direct(ticker, days=8):
    try:
        range_str = "10d" if days<=8 else "1mo"
        interval = "5m" if days<=1 else ("15m" if days<=3 else "60m")
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_str}"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12).json()
        res=r['chart']['result'][0]; q=res['indicators']['quote'][0]
        df=pd.DataFrame({'Close':q['close'],'High':q['high'],'Low':q['low'],'Open':q['open']}, index=pd.to_datetime(res['timestamp'], unit='s', utc=True)).dropna()
        cutoff = datetime.now(pytz.utc) - timedelta(days=days+1)
        df = df[df.index >= cutoff]
        return df if len(df)>10 else None
    except: return None

def get_all_data(days=3):
    if time.time()-data_cache["time"]<12 and data_cache["prices"] and days==3:
        return data_cache["prices"], data_cache["rsis"], data_cache.get("dfs",{})
    prices, rsis, dfs={}, {}, {}
    for k in ["BTC","ETH","SOL"]:
        pr=get_kraken_price(k) or 0; prices[k]=pr; df=get_kraken_history(k, days=days); dfs[k]=df
        rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if df is not None and len(df)>14 else 50.0
    for k,tick in SYMBOLS_YF.items():
        df=get_yahoo_direct(tick, days=days); dfs[k]=df
        if df is not None and len(df)>0: prices[k]=float(df['Close'].iloc[-1]); rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if len(df)>14 else 50.0
        else: prices[k]=0; rsis[k]=50.0
    if days==3:
        data_cache.update({"prices":prices,"rsis":rsis,"dfs":dfs,"time":time.time()})
    return prices, rsis, dfs

def get_bolas_snowball():
    gains=load_json(GAIN_FILE, {"total":0,"trades":0})
    total=max(0, gains.get("total",0))
    b1=min(BOLA_BASE1 + total, TOPE_B1); b2=min(BOLA_BASE2 + total*1.5, TOPE_B2); bny=min(BOLA_NY_BASE + total*2, TOPE_NY)
    return round(b1,2), round(b2,2), round(bny,2), total

def detectar_lineas_automaticas(df, num_lineas=25):
    try:
        highs = df['High'].rolling(5, center=True).max(); lows = df['Low'].rolling(5, center=True).min()
        niveles = []
        for i in range(5, len(df)-5):
            if df['High'].iloc[i] == highs.iloc[i]: niveles.append(float(df['High'].iloc[i]))
            if df['Low'].iloc[i] == lows.iloc[i]: niveles.append(float(df['Low'].iloc[i]))
        niveles_unicos = []
        for n in niveles:
            encontrado=False
            for u in niveles_unicos:
                if abs(n-u['precio'])/u['precio']<0.0035:
                    u['rebotes']+=1; u['precio']=(u['precio']+n)/2; encontrado=True; break
            if not encontrado: niveles_unicos.append({'precio':n, 'rebotes':1})
        return sorted(niveles_unicos, key=lambda x: x['rebotes'], reverse=True)[:num_lineas]
    except: return []

def analizar_entrada_con_lineas(sym, precio, df):
    lineas = detectar_lineas_automaticas(df, 20); mejor = None
    for lin in lineas:
        dist = abs(precio - lin['precio'])/precio*100
        if dist < 0.6:
            fuerza = min(95, lin['rebotes']*12 + (0.6-dist)*25)
            if fuerza > 60: mejor = {'linea': lin['precio'], 'rebotes': lin['rebotes'], 'fuerza': fuerza, 'dist': dist, 'total_lineas': len(lineas)}; break
    return mejor

def chalan_confirma(sym, precio, df):
    lineas_chalan = detectar_lineas_automaticas(df, num_lineas=30)
    for lin in lineas_chalan:
        dist = abs(precio - lin['precio'])/precio*100
        if dist < 0.7:
            fuerza_chalan = min(95, lin['rebotes']*11)
            return {'confirma': fuerza_chalan>62, 'fuerza': fuerza_chalan, 'rebotes': lin['rebotes'], 'linea': lin['precio']}
    return {'confirma': False, 'fuerza': 0, 'rebotes':0, 'linea':0}

def chart_bytes_pro(sym, days=3):
    now=time.time(); cache_key=f"{sym}_{days}"
    if cache_key in chart_cache and now-chart_cache[cache_key][0]<25: return chart_cache[cache_key][1]
    try:
        _,_,dfs=get_all_data(days=days); df=dfs.get(sym); b1,b2,bny,total_gain=get_bolas_snowball()
        if df is None or len(df)<30:
            pr,rs,_=get_all_data(); price=pr.get(sym,0)
            fig, ax=plt.subplots(figsize=(12,6)); ax.text(0.5,0.5,f"{sym} ${price:.2f}\nMAQUINA DINERO {days}D", ha='center', va='center', fontsize=18, transform=ax.transAxes); ax.set_axis_off()
            buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=130,bbox_inches='tight'); plt.close(fig); buf.seek(0); data=buf.getvalue(); chart_cache[cache_key]=(now,data); return data
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean(); df['SMA100']=df['Close'].rolling(100).mean()
        df['EMA20']=df['Close'].ewm(span=20).mean(); df['EMA50']=df['Close'].ewm(span=50).mean(); df['STD']=df['Close'].rolling(20).std(); df['BB_UP']=df['SMA20']+2*df['STD']; df['BB_LOW']=df['SMA20']-2*df['STD']
        pos=load_json(POS_FILE, {}).get(sym); price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1]); ny=load_json(NY_FILE, {}).get(sym,{}); lineas = detectar_lineas_automaticas(df, 15)
        fig, (ax1, ax2, ax3) = plt.subplots(3,1,figsize=(13,8), gridspec_kw={'height_ratios':[3,1,1]}, sharex=True)
        ax1.plot(df.index, df['Close'], linewidth=2.4, color='white', label=f'${price:.2f} {days}D')
        ax1.plot(df.index, df['SMA20'], linewidth=1.2, color='#f1c40f', label='SMA20'); ax1.plot(df.index, df['SMA50'], linewidth=1.2, color='#e74c3c', label='SMA50')
        for lin in lineas[:6]:
            alpha = 0.3 + (lin['rebotes']/10)
            ax1.axhline(lin['precio'], color='#00ff88' if lin['rebotes']>=4 else '#ffaa00', ls='-', lw=0.8+lin['rebotes']*0.2, alpha=alpha, label=f"Linea ${lin['precio']:.2f} {lin['rebotes']}R")
        if sym in ["NVDA","TSLA"] and ny:
            if 'high' in ny: ax1.axhline(ny['high'], color='#9b59b6', ls='--', lw=2.5, label=f"E1 HIGH ${ny['high']:.2f}")
            if 'low' in ny: ax1.axhline(ny['low'], color='#3498db', ls='--', lw=2.5, label=f"E1 LOW ${ny['low']:.2f}")
        if pos:
            ax1.axhline(pos['entry'], color='#f1c40f', ls='-', lw=2.5, label=f"ENTRADA ${pos['entry']:.2f} Bola ${pos['bola']}")
            tp_line=pos['entry']*1.015; sl_line=pos['entry']*0.88; ax1.axhline(tp_line, color='#2ecc71', ls=':', lw=1.5, alpha=0.7, label=f"TP 1.5% ${tp_line:.2f}"); ax1.axhline(sl_line, color='#e74c3c', ls=':', lw=1.5, alpha=0.7, label=f"SL -12% ${sl_line:.2f}")
        ax1.set_title(f"💰 MAQUINA + CHALAN V47 {sym} ${price:.2f} RSI {r:.1f} | {days}D | Lineas:{len(lineas)} | Bola ${b1}/${b2}", fontsize=10, color='white', fontweight='bold')
        ax1.legend(fontsize=5.5, loc='upper left', ncol=3, facecolor='#161b22', edgecolor='white'); ax1.grid(True, alpha=0.2, color='white'); ax1.set_facecolor('#0d1117'); ax1.tick_params(colors='white')
        ax2.plot(df.index, df['RSI'], color='#9b59b6', linewidth=1.5); ax2.axhline(44, color='#00ff00', ls='--', lw=1.5); ax2.axhline(70, color='#ff0000', ls='--', lw=1.2); ax2.set_ylim(0,100); ax2.grid(True, alpha=0.2); ax2.set_facecolor('#0d1117'); ax2.tick_params(colors='white')
        mom=df['Close'].diff(5); ax3.bar(df.index, mom, color=np.where(mom>0, '#2ecc71', '#e74c3c'), alpha=0.6); ax3.axhline(0, color='white', lw=0.8); ax3.grid(True, alpha=0.2); ax3.set_facecolor('#0d1117'); ax3.tick_params(colors='white')
        fig.patch.set_facecolor('#0d1117'); buf=io.BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[cache_key]=(now,data); return data
    except Exception as e:
        print(f"chart {sym} {e}"); return None

def trading_loop():
    while True:
        try:
            if not load_json(STATE_FILE, {"auto":False}).get("auto", False): time.sleep(10); continue
            prices, rsis, dfs=get_all_data(); positions=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0,"loss_streak":0}); ny_data=load_json(NY_FILE, {}); hist=load_json(HIST_FILE, [])
            b1,b2,bny,total_gain=get_bolas_snowball()
            if gains.get("loss_streak",0)>=3:
                save_json(STATE_FILE, {"auto":False}); notify(f"🚨 PROTECCION 3 PERDIDAS - MAQUINA + CHALAN OFF"); time.sleep(30); continue
            now_ny=datetime.now(TZ_NY); today=now_ny.strftime("%Y-%m-%d")
            for sym in ALL_SYMS:
                pr=prices.get(sym,0); r=rsis.get(sym,50); df=dfs.get(sym)
                if pr==0 or df is None: continue
                if sym in positions:
                    entry=positions[sym]['entry']; bola=positions[sym]['bola']; max_p=positions[sym].get('max', pr)
                    if pr>max_p: positions[sym]['max']=pr; max_p=pr
                    profit=(pr-entry)/entry*100; trail_drop=(max_p-pr)/max_p*100 if max_p>0 else 0
                    if profit>=TP_PCT or trail_drop>=TRAIL_PCT or profit<=SL_PCT:
                        ganancia=(pr-entry)/entry*bola; gains["total"]+=ganancia; gains["trades"]+=1
                        is_win = ganancia>0
                        if is_win: gains["loss_streak"]=0
                        else: gains["loss_streak"]=gains.get("loss_streak",0)+1
                        save_json(GAIN_FILE, gains); hist.append({"sym":sym, "entry":entry, "exit":pr, "bola":bola, "gan":round(ganancia,2), "strat":positions[sym].get('strat',''), "time":str(datetime.now(TZ_MX))}); save_json(HIST_FILE, hist[-100:])
                        del positions[sym]; save_json(POS_FILE, positions); notify(f"{'🟢 GANANCIA' if is_win else '🔴 PERDIDA'} {sym} {positions.get(sym,{}).get('strat','')}\nGan ${ganancia:.2f} Total ${gains['total']:.2f}"); continue
                if sym in ["BTC","ETH","SOL","XAUUSD"]:
                    analisis = analizar_entrada_con_lineas(sym, pr, df)
                    if analisis and analisis['fuerza']>68 and r<50:
                        if sym not in positions:
                            conf = chalan_confirma(sym, pr, df)
                            if conf['confirma'] and conf['fuerza']>70:
                                bola_final = min(b2*2.2, TOPE_B2*1.5); strat = f"V47 DOBLE {analisis['rebotes']}R+{conf['rebotes']}R F{analisis['fuerza']:.0f}%"
                                notify(f"💰💰 DOBLE CANDADO {sym} Linea ${analisis['linea']:.2f} MAQ {analisis['rebotes']}R {analisis['fuerza']:.0f}% + CHALAN {conf['rebotes']}R {conf['fuerza']:.0f}% → Bola ${bola_final}")
                            else:
                                bola_final = b1; strat = f"V47 MAQUINA {analisis['rebotes']}R F{analisis['fuerza']:.0f}%"
                            positions[sym]={'entry':pr, 'max':pr, 'bola':bola_final, 'strat':strat, 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions)
                if sym in ["NVDA","TSLA"] and 7<=now_ny.hour<16:
                    if now_ny.hour==9 and 30<=now_ny.minute<35:
                        h=float(df['High'].iloc[-1]); l=float(df['Low'].iloc[-1]); rng=h-l; ny_data.setdefault(sym, {}); ny_data[sym]['date']=today; ny_data[sym]['high']=h; ny_data[sym]['low']=l; ny_data[sym]['triple_high']=h+rng*1.5; ny_data[sym]['triple_low']=l-rng*1.5; ny_data[sym]['e1_done']=False; save_json(NY_FILE, ny_data)
                    if sym in ny_data and ny_data[sym].get('date')==today and 'high' in ny_data[sym]:
                        high=ny_data[sym]['high']; low=ny_data[sym]['low']; t_high=ny_data[sym].get('triple_high', high*1.02); t_low=ny_data[sym].get('triple_low', low*0.98)
                        if 9<=now_ny.hour<=11 and not ny_data[sym].get('e1_done', False) and sym not in positions:
                            if pr>high*(1+NY_PCT/100) or pr<low*(1-NY_PCT/100):
                                positions[sym]={'entry':pr, 'max':pr, 'bola':bny, 'strat':'E1 Break', 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions); ny_data[sym]['e1_done']=True; save_json(NY_FILE, ny_data); notify(f"🟣 ENTRADA NY E1 {sym} High ${high:.2f} Low ${low:.2f} Bola NY ${bny}")
                        if 11<=now_ny.hour<15 and sym not in positions:
                            if pr>t_high or pr<t_low:
                                positions[sym]={'entry':pr, 'max':pr, 'bola':bny, 'strat':'E2 Triple', 'time':str(datetime.now(TZ_MX))}; save_json(POS_FILE, positions); notify(f"🟡 ENTRADA NY E2 TRIPLE {sym} Triple ${t_high:.2f}/${t_low:.2f} Bola ${bny}")
            save_json(POS_FILE, positions)
        except Exception as e: print(f"loop {e}")
        time.sleep(15)

threading.Thread(target=trading_loop, daemon=True).start()

HTML_DASH="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="30"><style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:700px;margin:auto;background:#161b22;border:1px solid #00ff88;border-radius:12px;padding:14px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:700px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff;position:relative}.price{font-size:20px;font-weight:900;color:#58a6ff}.pos{position:absolute;top:6px;right:6px;background:#238636;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px}.box{max-width:700px;margin:18px auto;background:#161b22;border:1px solid #00ff88;border-radius:12px;padding:12px;text-align:left;font-size:13px}.gain{color:#3fb950;font-weight:900;font-size:18px}.snow{color:#00ff88;font-weight:900}</style></head><body><div class="top"><div><b style="color:#00ff88;font-size:16px">💰 MAQUINA DE HACER DINERO + CHALAN V47 💰</b><br><small>Bola ${{b1}}/{{b2}} NY ${{bny}} | Gan ${{"%.2f"|format(gains.total)}} | Perd {{gains.loss_streak}}</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div><p>{{hora}} | V47 DOBLE CANDADO AUTO-LINEAS | LIVE</p><div class="grid">{% for s in syms %}<a class="card" href="/view/{{s}}">{% if s in positions %}<span class="pos">EN POS ${{positions[s].bola}}</span>{% endif %}<h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div>{% if s in positions %}<small>{{positions[s].strat}} Ent ${{"%.2f"|format(positions[s].entry)}}</small>{% endif %}</a>{% endfor %}</div><div class="box"><b style="color:#00ff88">💰 V47 DOBLE CANDADO</b><br>MAQUINA analiza + CHALAN confirma = Bola GRANDE<br>{% if positions %}{% for s,p in positions.items() %}🟢 {{s}} [{{p.strat}}]: Ent ${{"%.2f"|format(p.entry)}} | Ahora ${{prices[s]}} | Bola ${{p.bola}}<br>{% endfor %}{% else %}Sin posiciones - MAQUINA + CHALAN escaneando lineas...<br>{% endif %}<br><b>💰 GANANCIA:</b> <span class="gain">${{"%.2f"|format(gains.total)}} en {{gains.trades}} trades</span></div></body></html>"""

HTML_VIEW="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:10px}.btns{max-width:680px;margin:10px auto;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}.btn{padding:10px 18px;border-radius:20px;border:1px solid #00ff88;background:#161b22;color:#fff;font-weight:900;text-decoration:none;cursor:pointer}.btn.active{background:#00ff88;color:#000}img{max-width:100%;border-radius:12px;border:1px solid #30363d;margin-top:12px}a.back{color:#58a6ff;text-decoration:none}</style><script>function setDays(d){document.getElementById('chart').src='/chart/{{sym}}?d='+d+'&t='+Date.now(); document.querySelectorAll('.btn').forEach(b=>b.classList.remove('active')); document.getElementById('btn'+d).classList.add('active')}</script></head><body><a class="back" href="/">← Volver V47</a><h2>💰 {{sym}} - V47 DOBLE CANDADO</h2><div class="btns"><a id="btn1" class="btn" onclick="setDays(1)">1 DIA</a><a id="btn3" class="btn active" onclick="setDays(3)">3 DIAS</a><a id="btn5" class="btn" onclick="setDays(5)">5 DIAS</a><a id="btn8" class="btn" onclick="setDays(8)">8 DIAS</a></div><img id="chart" src="/chart/{{sym}}?d=3" /><p><small>V47 Lineas verdes/naranjas | Bola ${{b1}}/{{b2}} NY ${{bny}} | Gan ${{gain}}</small></p></body></html>"""

@app.route('/view/<sym>')
def view(sym):
    b1,b2,bny,total=get_bolas_snowball(); gains=load_json(GAIN_FILE, {"total":0,"trades":0})
    return render_template_string(HTML_VIEW, sym=sym.upper(), b1=b1, b2=b2, bny=bny, gain=f"{gains['total']:.2f}")

@app.route('/toggle')
def tog(): s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); return redirect('/')

@app.route('/chart/<sym>')
def ch(sym):
    days=int(request.args.get('d','3'))
    if days not in [1,3,5,8]: days=3
    d=chart_bytes_pro(sym.upper(), days=days); return Response(d,mimetype='image/png') if d else ("Error",500)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string)
    try:
        if update.message: open(CHAT_ID_FILE,"w").write(str(update.message.chat.id))
    except: pass
    bot.process_new_updates([update]); return 'OK', 200

@bot.message_handler(commands=['start','balance','historial'])
def start(m):
    try: open(CHAT_ID_FILE,"w").write(str(m.chat.id))
    except: pass
    pos=load_json(POS_FILE,{}); auto=load_json(STATE_FILE,{"auto":False}).get("auto",False); pr,rs,_=get_all_data(); gains=load_json(GAIN_FILE, {"total":0,"trades":0,"loss_streak":0}); b1,b2,bny,total=get_bolas_snowball()
    txt=""
    for s,p in pos.items(): txt+=f"\n{s} [{p.get('strat','')}]: ${p['entry']:.2f}->{pr.get(s,0):.2f} Bola ${p['bola']}"
    if not txt: txt="\nSin posiciones"
    msg=f"💰 MAQUINA + CHALAN V47 DOBLE CANDADO\n{'🟢AUTO ON' if auto else '🔴AUTO OFF'} Cap ${CAPITAL}+${total:.2f}\nBola ${b1}/${b2} NY ${bny}\nGan ${gains['total']:.2f} {gains['trades']} trades\n{txt}\n{URL}"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if auto else 'OFF'}","DASHBOARD"); bot.send_message(m.chat.id, msg, reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    try: open(CHAT_ID_FILE,"w").write(str(m.chat.id))
    except: pass
    t=m.text.upper().strip()
    if "AUTO" in t: s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); bot.send_message(m.chat.id,f"{'🟢AUTO ON V47' if s['auto'] else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in ALL_SYMS:
        b1,b2,bny,total=get_bolas_snowball(); bot.send_message(m.chat.id, f"{URL}/view/{t}\nV47 DOBLE CANDADO")
        d=chart_bytes_pro(t, days=3); pr,rs,_=get_all_data()
        if d: bot.send_photo(m.chat.id,d,caption=f"💰 V47 {t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} | Lineas auto")

try:
    if URL: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V47 OK - MAQUINA + CHALAN LIVE")
except Exception as e: print(e)

app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
