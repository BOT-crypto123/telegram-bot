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

TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
URL = os.environ.get("RENDER_EXTERNAL_URL","").strip().rstrip("/")

# V45.8 CONCENTRADO 29 DIARIOS - 4 MONEDAS
SYMBOLS_CG = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}
SYMBOLS_YF = {"XAUUSD":"GC=F"}
ALL_SYMS = ["BTC","ETH","SOL","XAUUSD"]

CAPITAL = 5000
BOLA_N1 = 500
BOLA_N2 = 750
TP_PCT = 1.5
TRAIL_PCT = 1.0
SL_PCT = -12.0
RSI_BUY = 44
AGRESIVIDAD = 7.8

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
TZ_MX = pytz.timezone("America/Mexico_City")
STATE_FILE="/tmp/state.json"
POS_FILE="/tmp/positions.json"
GAIN_FILE="/tmp/gains.json"

def load_json(f, d):
    try: return json.load(open(f))
    except: return d
def save_json(f, data):
    try: json.dump(data, open(f,"w"))
    except: pass

chart_cache={}
data_cache={"prices":{},"rsis":{},"time":0}

def rsi_calc(s,p=14):
    try:
        d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean(); rs=g/l; return 100-(100/(1+rs))
    except: return pd.Series([50]*len(s))

def get_kraken(sym):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}", timeout=6).json()
        k=list(r['result'].keys())[0]; return float(r['result'][k]['c'][0])
    except: return None
def get_cg_price(sym):
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={SYMBOLS_CG[sym]}&vs_currencies=usd", timeout=6).json()
        return float(r[SYMBOLS_CG[sym]]['usd'])
    except: return None
def get_history_cg(sym):
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/coins/{SYMBOLS_CG[sym]}/market_chart?vs_currency=usd&days=5", timeout=10).json()
        df=pd.DataFrame(r['prices'], columns=['t','Close']); df['t']=pd.to_datetime(df['t'], unit='ms'); df=df.set_index('t'); df=df.resample('15min').last().dropna()
        return df if len(df)>20 else None
    except: return None
def get_yahoo_direct(ticker):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=15m&range=5d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        res=r['chart']['result'][0]; closes=res['indicators']['quote'][0]['close']; times=res['timestamp']
        df=pd.DataFrame({'Close':closes}, index=pd.to_datetime(times, unit='s')).dropna()
        return df if len(df)>10 else None
    except: return None

def get_all_data():
    if time.time()-data_cache["time"]<15 and data_cache["prices"]: return data_cache["prices"], data_cache["rsis"]
    prices, rsis={}, {}
    for k in ["BTC","ETH","SOL"]:
        pr = get_kraken(k) or get_cg_price(k) or 0
        prices[k]=pr
        df=get_history_cg(k)
        rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if df is not None and len(df)>14 else 50.0
    for k,tick in SYMBOLS_YF.items():
        df=get_yahoo_direct(tick)
        if df is not None and len(df)>0:
            prices[k]=float(df['Close'].iloc[-1]); rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if len(df)>14 else 50.0
        else:
            prices[k]=0; rsis[k]=50.0
    data_cache.update({"prices":prices,"rsis":rsis,"time":time.time()}); return prices, rsis

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<60: return chart_cache[sym][1]
    try:
        df=None
        if sym in ["BTC","ETH","SOL"]: df=get_history_cg(sym)
        else: df=get_yahoo_direct(SYMBOLS_YF[sym])
        if df is None or len(df)<20:
            pr,_=get_all_data(); price=pr.get(sym,0)
            fig, ax = plt.subplots(figsize=(10,5))
            ax.text(0.5,0.5,f"{sym}\n${price:.2f}\nAPI limit - 20s\nV45.8 7.8 TP{TP_PCT}% Trail{TRAIL_PCT}% RSI<{RSI_BUY}", ha='center', va='center', fontsize=18, transform=ax.transAxes)
            ax.set_axis_off()
            buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=120,bbox_inches='tight'); plt.close(fig); buf.seek(0)
            data=buf.getvalue(); chart_cache[sym]=(now,data); return data
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        pos=load_json(POS_FILE, {}).get(sym)
        price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1])
        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,6),gridspec_kw={'height_ratios':[3,1]},sharex=True)
        ax1.plot(df['Close'],linewidth=2.2,label='Precio'); ax1.plot(df['SMA20'],linewidth=1,alpha=.7,label='SMA20'); ax1.plot(df['SMA50'],linewidth=1,alpha=.7,label='SMA50')
        entradas=df[df['RSI']<RSI_BUY]; ax1.scatter(entradas.index, entradas['Close'], marker='^', color='green', s=80, label=f'ENTRADAS RSI<{RSI_BUY}')
        if pos: ax1.axhline(pos['entry'], color='orange', ls='--', linewidth=2, label=f"Entrada ${pos['entry']:.2f} Bola ${pos['bola']}")
        ax1.set_title(f"{sym} ${price:.2f} RSI {r:.1f} | V45.8 7.8 TP{TP_PCT}% Trail{TRAIL_PCT}% SL{SL_PCT}% Bola {BOLA_N1}/{BOLA_N2}"); ax1.legend(fontsize=8); ax1.grid(True,alpha=.3)
        ax2.plot(df['RSI'],label='RSI'); ax2.axhline(RSI_BUY,color='green',ls='--',label=f'Compra {RSI_BUY}'); ax2.axhline(70,color='red',ls='--'); ax2.set_ylim(0,100); ax2.legend(fontsize=8); ax2.grid(True,alpha=.3)
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=135,bbox_inches='tight'); plt.close(fig); buf.seek(0); data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e:
        print(f"chart {sym} {e}")
        try:
            fig, ax = plt.subplots(figsize=(10,5)); ax.text(0.5,0.5,f"Error {sym}\n{e}", ha='center', va='center', transform=ax.transAxes); ax.set_axis_off()
            buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=120); plt.close(fig); buf.seek(0); return buf.getvalue()
        except: plt.close('all'); return None

def trading_loop():
    while True:
        try:
            if not load_json(STATE_FILE, {"auto":False}).get("auto", False): time.sleep(10); continue
            prices, rsis = get_all_data()
            positions = load_json(POS_FILE, {})
            gains = load_json(GAIN_FILE, {"total":0,"trades":0})
            for sym in ALL_SYMS:
                pr=prices.get(sym,0); r=rsis.get(sym,50)
                if pr==0: continue
                if sym in positions:
                    entry=positions[sym]['entry']; bola=positions[sym]['bola']; max_p=positions[sym].get('max', pr)
                    if pr>max_p: positions[sym]['max']=pr; max_p=pr
                    profit=(pr-entry)/entry*100; trail_drop=(max_p-pr)/max_p*100 if max_p>0 else 0
                    # VENTA TP 1.5% o Trail 1% o SL -12%
                    if profit>=TP_PCT or trail_drop>=TRAIL_PCT or profit<=SL_PCT:
                        ganancia_usd = (pr-entry)/entry * bola
                        gains["total"]+=ganancia_usd; gains["trades"]+=1; save_json(GAIN_FILE, gains)
                        try:
                            if profit>=0: bot.send_message(int(os.environ.get("CHAT_ID","0")), f"🔴 VENTA {sym} ${pr:.2f} Profit {profit:.2f}% ${ganancia_usd:.2f} Bola ${bola} | Total ${gains['total']:.2f}")
                        except: pass
                        del positions[sym]; save_json(POS_FILE, positions)
                else:
                    # COMPRA RSI<44 + Bola escalonada 7.8
                    if r < RSI_BUY:
                        # Si ya tiene 1 posicion en perdida, usa bola 750
                        bola = BOLA_N1
                        # Checa si hay perdida reciente para usar N2
                        for s,p in positions.items():
                            if (pr - p['entry'])/p['entry']*100 < -3:
                                bola = BOLA_N2
                                break
                        if len(positions)>=2: # Max 2 posiciones para concentrar y llegar a 29
                            continue
                        positions[sym]={'entry':pr, 'max':pr, 'bola':bola, 'time':str(datetime.now(TZ_MX))}
                        save_json(POS_FILE, positions)
                        try: bot.send_message(int(os.environ.get("CHAT_ID","0")), f"🟢 COMPRA 7.8 {sym} ${pr:.2f} RSI {r:.1f} Bola ${bola}")
                        except: pass
            save_json(POS_FILE, positions)
        except Exception as e: print(f"loop {e}")
        time.sleep(20)
threading.Thread(target=trading_loop, daemon=True).start()

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:580px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:580px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff;position:relative}.price{font-size:20px;font-weight:900;color:#58a6ff}.pos{position:absolute;top:6px;right:6px;background:#238636;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px}.box{max-width:580px;margin:18px auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;text-align:left;font-size:14px}.gain{color:#3fb950;font-weight:900}</style></head><body>
<div class="top"><div><b>MAQUINA V45.8 7.8 - $29</b><br><small>Cap $5000 Bola $500/$750 RSI<44 TP1.5 Trail1 SL-12% 4 monedas</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | V34 CONCENTRADO 29 DIARIOS | Agresividad 7.8</p>
<div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}">{% if s in positions %}<span class="pos">EN POS</span>{% endif %}<h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div>{% if s in positions %}<small>Ent ${{"%.2f"|format(positions[s].entry)}} Bola ${{positions[s].bola}}</small>{% endif %}</a>{% endfor %}
</div>
<div class="box">
<b>📊 ENTRADAS Y GANANCIAS - 7.8 $29 DIARIOS</b><br><br>
{% if positions %}
{% for s,p in positions.items() %}
🟢 {{s}}: Entrada ${{"%.2f"|format(p.entry)}} | Ahora ${{prices[s]}} | Bola ${{p.bola}} | Profit {{ "%.2f"|format((prices[s]|replace('$','')|replace('CARGANDO','0')|float - p.entry)/p.entry*100 if prices[s]!='CARGANDO' else 0) }}%<br>
{% endfor %}
{% else %}
Sin posiciones - esperando RSI < {{rsi_buy}} para entrar con Bola $500<br><small>Objetivo 5 trades x $6 = $30 día</small>
{% endif %}
<br><br>
<b>💰 GANANCIA HOY:</b> <span class="gain">${{"%.2f"|format(gains.total)}} en {{gains.trades}} trades</span><br>
<b>Estrategia:</b> TP {{tp}}% Trail {{trail}}% SL {{sl}}% | Cap ${{cap}} | Agresividad {{agr}}<br>
<b>Modo:</b> 4 monedas concentrado para $29 diarios (BTC ETH SOL XAUUSD)<br>
<b>Gráficas:</b> Toca tarjeta = viva SMA20/50 + flechas verdes
</div>
</body></html>"""

@app.route('/')
def home():
    pr,rs=get_all_data(); pos=load_json(POS_FILE, {}); gains=load_json(GAIN_FILE, {"total":0,"trades":0})
    return render_template_string(HTML, syms=ALL_SYMS, auto=load_json(STATE_FILE,{"auto":False}).get("auto",False), hora=datetime.now(TZ_MX).strftime("%H:%M:%S"),
        positions=pos, gains=gains, tp=TP_PCT, trail=TRAIL_PCT, sl=SL_PCT, rsi_buy=RSI_BUY, cap=CAPITAL, agr=AGRESIVIDAD,
        prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})
@app.route('/toggle')
def tog():
    s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); return redirect('/')
@app.route('/chart/<sym>')
def ch(sym):
    d=chart_bytes(sym.upper())
    if d: return Response(d,mimetype='image/png')
    fig, ax = plt.subplots(figsize=(8,4)); ax.text(0.5,0.5,f"{sym} cargando...", ha='center', va='center'); ax.set_axis_off()
    buf=io.BytesIO(); plt.savefig(buf,format='png'); plt.close(fig); buf.seek(0); return Response(buf.getvalue(),mimetype='image/png')
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''

@bot.message_handler(commands=['start','balance'])
def start(m):
    pos=load_json(POS_FILE,{}); auto=load_json(STATE_FILE,{"auto":False}).get("auto",False); pr,rs=get_all_data(); gains=load_json(GAIN_FILE, {"total":0,"trades":0}); txt_pos=""
    for s,p in pos.items():
        prof=(pr.get(s,0)-p['entry'])/p['entry']*100 if pr.get(s,0)>0 else 0; txt_pos+=f"\n{s}: ${p['entry']:.2f}->{pr.get(s,0):.2f} ({prof:.2f}%) Bola ${p['bola']}"
    if not txt_pos: txt_pos="\nSin posiciones - esperando RSI<44"
    txt=f"✅ V45.8 7.8 $29 DIARIOS\n{'🟢AUTO ON' if auto else '🔴AUTO OFF'} Cap ${CAPITAL} Bola ${BOLA_N1}/${BOLA_N2}\nRSI<{RSI_BUY} TP{TP_PCT}% Trail{TRAIL_PCT}% SL{SL_PCT}%\nGanancia Hoy: ${gains['total']:.2f} en {gains['trades']} trades\n{txt_pos}\n{URL}"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=2); kb.add("BTC","ETH","SOL","XAUUSD"); kb.add(f"AUTO {'ON' if auto else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id, txt, reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    t=m.text.upper().strip()
    if "AUTO" in t:
        s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s)
        bot.send_message(m.chat.id,f"{'🟢AUTO ON 7.8 $29 activo' if s['auto'] else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in ALL_SYMS:
        d=chart_bytes(t); pr,rs=get_all_data()
        cap=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} V45.8 7.8 TP{TP_PCT}% Trail{TRAIL_PCT}%"
        bot.send_photo(m.chat.id,d,caption=cap) if d else bot.send_message(m.chat.id,cap)

try:
    if URL: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V45.8 7.8 OK")
except Exception as e: print(e)
app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
