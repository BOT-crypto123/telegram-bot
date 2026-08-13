import os, time, io, requests, json
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
SYMBOLS = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
TZ_MX = pytz.timezone("America/Mexico_City")

# Guarda AUTO en archivo para que no se desfase
STATE_FILE="/tmp/state.json"
def load_state():
    try: return json.load(open(STATE_FILE))['auto']
    except: return False
def save_state(v):
    try: json.dump({"auto":v}, open(STATE_FILE,"w"))
    except: pass
AUTO_ON = load_state()

chart_cache={}
data_cache={"prices":{},"rsis":{},"time":0}

def get_price_cg(sym):
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={SYMBOLS[sym]}&vs_currencies=usd", timeout=8).json()
        return float(r[SYMBOLS[sym]]['usd'])
    except: return None

def get_kraken(sym):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}", timeout=8).json()
        k=list(r['result'].keys())[0]
        return float(r['result'][k]['c'][0])
    except: return None

def get_yahoo_price(ticker):
    try:
        import yfinance as yf
        # truco anti-bloqueo Render
        try:
            from curl_cffi import requests as creq
            session = creq.Session(impersonate="chrome")
            df=yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True, threads=False, session=session)
        except:
            df=yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True, threads=False)
        if len(df)>0: return float(df['Close'].iloc[-1]), df
    except: return None, None
    return None, None

def rsi_calc(s,p=14):
    try:
        d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean(); rs=g/l; return 100-(100/(1+rs))
    except: return pd.Series([50])

def get_all_data():
    if time.time()-data_cache["time"]<20 and data_cache["prices"]: return data_cache["prices"], data_cache["rsis"]
    prices, rsis={}, {}
    # crypto por Kraken + CG
    for k in ["BTC","ETH","SOL"]:
        pr = get_kraken(k)
        if pr is None: pr = get_price_cg(k)
        if pr is None: pr=0
        prices[k]=pr
        # RSI con historico CG
        try:
            rh=requests.get(f"https://api.coingecko.com/api/v3/coins/{SYMBOLS[k]}/market_chart?vs_currency=usd&days=5", timeout=10).json()
            df=pd.DataFrame(rh['prices'], columns=['t','Close']); df['Close']=df['Close'].astype(float)
            rsis[k]=float(rsi_calc(df['Close']).iloc[-1])
        except: rsis[k]=50.0
    # stocks / oro - intenta Yahoo con truco
    for k in ["XAUUSD","NVDA","TSLA"]:
        pr, df = get_yahoo_price(SYMBOLS[k])
        if pr is None: pr=0
        prices[k]=pr
        try: rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if df is not None and len(df)>14 else 50.0
        except: rsis[k]=50.0
    data_cache.update({"prices":prices,"rsis":rsis,"time":time.time()})
    return prices, rsis

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<60: return chart_cache[sym][1]
    try:
        if sym in ["BTC","ETH","SOL"]:
            rh=requests.get(f"https://api.coingecko.com/api/v3/coins/{SYMBOLS[sym]}/market_chart?vs_currency=usd&days=5", timeout=10).json()
            df=pd.DataFrame(rh['prices'], columns=['t','Close']); df['t']=pd.to_datetime(df['t'], unit='ms'); df=df.set_index('t')
            df=df.resample('15min').last().dropna()
        else:
            _, df = get_yahoo_price(SYMBOLS[sym])
            if df is None: return None
        if len(df)<20: return None
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1])
        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,5),gridspec_kw={'height_ratios':[3,1]},sharex=True)
        ax1.plot(df['Close'],linewidth=2,label='Precio'); ax1.plot(df['SMA20'],linewidth=1,alpha=.6,label='SMA20'); ax1.plot(df['SMA50'],linewidth=1,alpha=.6,label='SMA50')
        entradas=df[df['RSI']<45]; ax1.scatter(entradas.index, entradas['Close'], marker='^', color='green', s=50, label='Entrada')
        ax1.set_title(f"{sym} ${price:.2f} RSI {r:.1f} AUTO {'ON' if AUTO_ON else 'OFF'} Bola $500/750/1000 TP1.5% Trail3%"); ax1.legend(fontsize=8); ax1.grid(True,alpha=.3)
        ax2.plot(df['RSI'],label='RSI'); ax2.axhline(45,color='green',ls='--'); ax2.axhline(70,color='red',ls='--'); ax2.grid(True,alpha=.3)
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=130,bbox_inches='tight'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e:
        print(f"chart {sym} err {e}"); plt.close('all'); return None

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:560px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:560px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff}.price{font-size:20px;font-weight:900;color:#58a6ff}</style></head><body>
<div class="top"><div><b>MAQUINA V45.5</b><br><small>Cap $5000 Bola $500/750/1000 - RSI/TP/Trail intacto</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | Kraken+CG+Yahoo Fix | WEBHOOK</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}"><h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div></a>{% endfor %}
</div><small>Toca tarjeta = grafica viva con SMA y entradas</small></body></html>"""

@app.route('/')
def home():
    pr,rs=get_all_data()
    return render_template_string(HTML, syms=SYMBOLS.keys(), auto=AUTO_ON, hora=datetime.now(TZ_MX).strftime("%H:%M:%S"),
        prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})

@app.route('/toggle')
def tog():
    global AUTO_ON; AUTO_ON=not AUTO_ON; save_state(AUTO_ON); return redirect('/')
@app.route('/chart/<sym>')
def ch(sym):
    d=chart_bytes(sym.upper()); return Response(d,mimetype='image/png') if d else ("Generando grafica, recarga en 5s...",503)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''

@bot.message_handler(commands=['start','balance'])
def start(m):
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if AUTO_ON else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id,f"✅ V45.5 FIX GRAFICAS\n{'🟢AUTO ON' if AUTO_ON else '🔴AUTO OFF'} Cap $5000\n{URL}",reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    global AUTO_ON; t=m.text.upper().strip()
    if "AUTO" in t: AUTO_ON=not AUTO_ON; save_state(AUTO_ON); bot.send_message(m.chat.id,f"{'🟢AUTO ON' if AUTO_ON else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in SYMBOLS: d=chart_bytes(t); pr,rs=get_all_data(); cap=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f}"; bot.send_photo(m.chat.id,d,caption=cap) if d else bot.send_message(m.chat.id,cap+" (grafica cargando)")

try:
    if URL:
        bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V45.5 OK")
except Exception as e: print(e)
app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
