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
SYMBOLS_CG = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}
SYMBOLS_YF = {"XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
ALL_SYMS = ["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]

CAPITAL = 5000
BOLA = [500,750,1000]
TP_PCT = 1.5
TRAIL_PCT = 3.0
RSI_BUY = 45

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
TZ_MX = pytz.timezone("America/Mexico_City")
STATE_FILE="/tmp/state.json"
POS_FILE="/tmp/positions.json"

def load_json(f, d):
    try: return json.load(open(f))
    except: return d
def save_json(f, data):
    try: json.dump(data, open(f,"w"))
    except: pass

chart_cache={}
data_cache={"prices":{},"rsis":{},"time":0}

def rsi_calc(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean(); rs=g/l; return 100-(100/(1+rs))

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
        df=pd.DataFrame(r['prices'], columns=['t','Close']); df['t']=pd.to_datetime(df['t'], unit='ms'); df=df.set_index('t'); df=df.resample('15min').last().dropna(); return df
    except: return None
def get_yahoo_direct(ticker):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=15m&range=5d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        res=r['chart']['result'][0]; closes=res['indicators']['quote'][0]['close']; times=res['timestamp']
        df=pd.DataFrame({'Close':closes}, index=pd.to_datetime(times, unit='s')).dropna(); return df if len(df)>20 else None
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
        if sym in ["BTC","ETH","SOL"]: df=get_history_cg(sym)
        else: df=get_yahoo_direct(SYMBOLS_YF[sym])
        if df is None or len(df)<30: return None
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        pos=load_json(POS_FILE, {}).get(sym)
        price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1])
        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,6),gridspec_kw={'height_ratios':[3,1]},sharex=True)
        ax1.plot(df['Close'],linewidth=2.2,label='Precio'); ax1.plot(df['SMA20'],linewidth=1,alpha=.7,label='SMA20'); ax1.plot(df['SMA50'],linewidth=1,alpha=.7,label='SMA50')
        entradas=df[df['RSI']<RSI_BUY]; ax1.scatter(entradas.index, entradas['Close'], marker='^', color='green', s=80, label=f'ENTRADAS RSI<{RSI_BUY}')
        if pos: ax1.axhline(pos['entry'], color='orange', ls='--', linewidth=2, label=f"Tu Entrada ${pos['entry']:.2f}")
        ax1.set_title(f"{sym} ${price:.2f} RSI {r:.1f} | TP{TP_PCT}% Trail{TRAIL_PCT}% Cap${CAPITAL} Bola{BOLA}"); ax1.legend(fontsize=8); ax1.grid(True,alpha=.3)
        ax2.plot(df['RSI'],label='RSI'); ax2.axhline(45,color='green',ls='--'); ax2.axhline(70,color='red',ls='--'); ax2.set_ylim(0,100); ax2.grid(True,alpha=.3)
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=135,bbox_inches='tight'); plt.close(fig); buf.seek(0); data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e: print(e); plt.close('all'); return None

def trading_loop():
    while True:
        try:
            if not load_json(STATE_FILE, {"auto":False}).get("auto", False): time.sleep(10); continue
            prices, rsis = get_all_data()
            positions = load_json(POS_FILE, {})
            for sym in ALL_SYMS:
                pr=prices.get(sym,0); r=rsis.get(sym,50)
                if pr==0: continue
                if sym in positions:
                    entry=positions[sym]['entry']; max_p=positions[sym].get('max', pr)
                    if pr>max_p: positions[sym]['max']=pr; max_p=pr
                    profit=(pr-entry)/entry*100; trail_drop=(max_p-pr)/max_p*100 if max_p>0 else 0
                    if profit>=TP_PCT or trail_drop>=TRAIL_PCT:
                        del positions[sym]; save_json(POS_FILE, positions)
                else:
                    if r < RSI_BUY:
                        bola = BOLA[len(positions)%3]
                        positions[sym]={'entry':pr, 'max':pr, 'bola':bola, 'time':str(datetime.now(TZ_MX))}
                        save_json(POS_FILE, positions)
            save_json(POS_FILE, positions)
        except Exception as e: print(f"loop {e}")
        time.sleep(30)
threading.Thread(target=trading_loop, daemon=True).start()

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:580px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:580px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff;position:relative}.price{font-size:20px;font-weight:900;color:#58a6ff}.pos{position:absolute;top:6px;right:6px;background:#238636;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px}.box{max-width:580px;margin:18px auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;text-align:left;font-size:14px}</style></head><body>
<div class="top"><div><b>MAQUINA V45.6 FULL</b><br><small>Cap $5000 Bola $500/750/1000 RSI<45 TP1.5 Trail3 SMA20/50</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | Kraken+CG+YahooDirect | Estrategia Activa</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}">{% if s in positions %}<span class="pos">EN POS</span>{% endif %}<h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div>{% if s in positions %}<small>Ent ${{"%.2f"|format(positions[s].entry)}} Bola ${{positions[s].bola}}</small>{% endif %}</a>{% endfor %}
</div>
<div class="box"><b>📊 ENTRADAS Y GANANCIAS - ESTRATEGIA INTACTA</b><br><br>
{% if positions %}
{% for s,p in positions.items() %}
🟢 {{s}}: Entrada ${{"%.2f"|format(p.entry)}} | Ahora ${{prices[s]}} | Bola ${{p.bola}} | Profit {{ "%.2f"|format((prices[s]|replace('$','')|replace('CARGANDO','0')|float - p.entry)/p.entry*100 if prices[s]!='CARGANDO' else 0) }}% | TP {{tp}}% Trail {{trail}}%<br>
{% endfor %}
{% else %}
Sin posiciones abiertas.<br>Esperando RSI < {{rsi_buy}} para COMPRAR automático.<br><small>Cuando baje, entra con Bola $500 -> $750 -> $1000. Vende con TP 1.5% o Trail 3%.</small>
{% endif %}
<br><br><b>Historial:</b> No se borra, guardado en {{pos_file}} | <b>Gráficas:</b> Toca tarjeta = viva con SMA20/50 + flechas verdes
</div>
</body></html>"""

@app.route('/')
def home():
    pr,rs=get_all_data(); pos=load_json(POS_FILE, {})
    return render_template_string(HTML, syms=ALL_SYMS, auto=load_json(STATE_FILE,{"auto":False}).get("auto",False), hora=datetime.now(TZ_MX).strftime("%H:%M:%S"),
        positions=pos, tp=TP_PCT, trail=TRAIL_PCT, rsi_buy=RSI_BUY, pos_file=POS_FILE,
        prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})
@app.route('/toggle')
def tog():
    s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); return redirect('/')
@app.route('/chart/<sym>')
def ch(sym): d=chart_bytes(sym.upper()); return Response(d,mimetype='image/png') if d else ("Generando grafica, recarga 5s - si es fin de semana XAU/NVDA/TSLA no tienen datos nuevos",503)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''

@bot.message_handler(commands=['start','balance'])
def start(m):
    pos=load_json(POS_FILE,{}); auto=load_json(STATE_FILE,{"auto":False}).get("auto",False)
    total_profit=0; txt_pos=""
    pr,rs=get_all_data()
    for s,p in pos.items():
        prof=(pr.get(s,0)-p['entry'])/p['entry']*100 if pr.get(s,0)>0 else 0; total_profit+=prof
        txt_pos+=f"\n{s}: ${p['entry']:.2f} -> ${pr.get(s,0):.2f} ({prof:.2f}%) Bola ${p['bola']}"
    if not txt_pos: txt_pos="\nSin posiciones - esperando RSI<45"
    txt=f"✅ V45.6 FULL CON TODO\n{'🟢AUTO ON' if auto else '🔴AUTO OFF'} Cap ${CAPITAL} Bola {BOLA}\nRSI<{RSI_BUY} TP{TP_PCT}% Trail{TRAIL_PCT}%\nPosiciones: {len(pos)} Profit: {total_profit:.2f}%\n{txt_pos}\n{URL}"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if auto else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id, txt, reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    t=m.text.upper().strip()
    if "AUTO" in t:
        s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s)
        bot.send_message(m.chat.id,f"{'🟢AUTO ON - estrategia RSI<45 activa' if s['auto'] else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in ALL_SYMS:
        d=chart_bytes(t); pr,rs=get_all_data()
        cap=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} TP{TP_PCT}% Trail{TRAIL_PCT}% Cap${CAPITAL} Bola{BOLA}\nPos: {load_json(POS_FILE,{}).get(t,'Sin pos')}"
        bot.send_photo(m.chat.id,d,caption=cap) if d else bot.send_message(m.chat.id,cap+" (grafica en 5s)")

try:
    if URL: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V45.6 FULL OK")
except Exception as e: print(e)
app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
