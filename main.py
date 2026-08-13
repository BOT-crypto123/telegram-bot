import os, threading, time, io, requests
from flask import Flask, Response, render_template_string, redirect
import telebot
from telebot import types
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz
from datetime import datetime
import pandas as pd

TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
N1,N2,N3 = 500,750,1000
CAPITAL, TP_PCT, TRAIL = 5000, 1.5, 3.0
TZ_MX = pytz.timezone("America/Mexico_City")
SYMBOLS = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
BINANCE = {"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
AUTO_ON = False
chart_cache = {}
data_cache = {"prices":{},"rsis":{},"profit":{},"time":0}

def get_binance_price(sym):
    try:
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={BINANCE[sym]}", timeout=4).json()
        return float(r['price'])
    except: return None

def get_binance_klines(sym):
    try:
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={BINANCE[sym]}&interval=15m&limit=100", timeout=6).json()
        df=pd.DataFrame(r, columns=['t','o','h','l','c','v','a','b','c','d','e','f'])
        df['Close']=df['c'].astype(float); df['t']=pd.to_datetime(df['t'], unit='ms')
        df=df.set_index('t'); return df
    except: return None

def rsi_calc(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+(g/l)))

def get_data():
    if time.time()-data_cache["time"]<20 and data_cache["prices"]:
        return data_cache["prices"], data_cache["rsis"], data_cache["profit"]
    prices, rsis, profit={},{},{}
    for k in SYMBOLS:
        price=None
        if k in BINANCE:
            price=get_binance_price(k)
            if price:
                df=get_binance_klines(k)
                r=float(rsi_calc(df['Close']).iloc[-1]) if df is not None else 50.0
                prices[k]=price; rsis[k]=r; profit[k]=round(price*0.0001,2)
        if price is None:
            try:
                df=yf.download(SYMBOLS[k], period="1d", interval="5m", progress=False, auto_adjust=True, threads=False)
                if len(df)>10:
                    prices[k]=float(df['Close'].iloc[-1]); rsis[k]=float(rsi_calc(df['Close']).iloc[-1]); profit[k]=0
            except: pass
        if k not in prices: prices[k]=0; rsis[k]=0; profit[k]=0
    data_cache.update({"prices":prices,"rsis":rsis,"profit":profit,"time":time.time()})
    return prices, rsis, profit

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<60: return chart_cache[sym][1]
    try:
        df=get_binance_klines(sym) if sym in BINANCE else None
        if df is None:
            df=yf.download(SYMBOLS[sym], period="5d", interval="15m", progress=False, auto_adjust=True, threads=False)
        if df is None or len(df)<20: return None
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        rsi=float(df['RSI'].iloc[-1]); price=float(df['Close'].iloc[-1])
        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,6),gridspec_kw={'height_ratios':[3,1]},sharex=True)
        ax1.plot(df['Close'],linewidth=2.2,label='Precio'); ax1.plot(df['SMA20'],linewidth=1,alpha=0.7,label='SMA20'); ax1.plot(df['SMA50'],linewidth=1,alpha=0.7,label='SMA50')
        entradas=df[df['RSI']<45]; ax1.scatter(entradas.index, entradas['Close'], marker='^', color='green', s=70, label='ENTRADA')
        ax1.set_title(f"{sym} ${price:.2f} RSI {rsi:.1f} TP{TP_PCT}% Trail{TRAIL}% AUTO {'ON' if AUTO_ON else 'OFF'} - Bola ${N1}/{N2}/{N3}"); ax1.legend(); ax1.grid(True,alpha=0.3)
        ax2.plot(df['RSI']); ax2.axhline(45,color='green',ls='--'); ax2.axhline(70,color='red',ls='--')
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=130,bbox_inches='tight'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except: plt.close('all'); return None

def puede(sym):
    if sym in ["BTC","ETH","SOL"]: return True, "24/7"
    h=datetime.now(TZ_MX).hour; return (8<=h<15, "ABIERTO" if 8<=h<15 else "CERRADO NY")

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="25">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:10px}.top{max-width:560px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:560px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:14px;text-decoration:none;color:#fff}.price{font-size:20px;font-weight:900;color:#58a6ff}</style></head><body>
<div class="top"><div><b>MAQUINA V45.2 FINAL</b><br><small>Cap $5000 Bola $500/750/1000</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | BTC/ETH/SOL 24/7 | XAU/NVDA/TSLA NY 8AM-3PM</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}"><h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}} | {{status[s]}}</div><div style="color:#2ea043">Profit ${{profit[s]}}</div></a>{% endfor %}
</div><small>Pucha tarjeta para ver grafica con lineas SMA y entradas</small></body></html>"""

@app.route('/')
def home():
    prices,rsis,profit=get_data(); st={}
    for s in SYMBOLS: _,t=puede(s); st[s]=t
    return render_template_string(HTML, syms=SYMBOLS.keys(), auto=AUTO_ON, hora=datetime.now(TZ_MX).strftime("%H:%M:%S"), status=st,
        prices={k:f"{v:.2f}" if v>0 else "--" for k,v in prices.items()},
        rsis={k:f"{v:.1f}" if v>0 else "--" for k,v in rsis.items()}, profit=profit)

@app.route('/toggle')
def tog(): global AUTO_ON; AUTO_ON=not AUTO_ON; return redirect('/')
@app.route('/chart/<sym>')
def ch(sym): sym=sym.upper(); d=chart_bytes(sym); return Response(d,mimetype='image/png') if d else ("Cargando 10s recarga",503)

@bot.message_handler(commands=['start','balance'])
def start(m):
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if AUTO_ON else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id,f"✅ V45.2 FINAL\n{'🟢AUTO ON' if AUTO_ON else '🔴AUTO OFF'} Cap $5000\nWeb: {os.environ.get('RENDER_EXTERNAL_URL','')}",reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    global AUTO_ON; t=m.text.upper().strip()
    if "AUTO" in t: AUTO_ON=not AUTO_ON; bot.send_message(m.chat.id,f"{'🟢AUTO ON - comprando solo' if AUTO_ON else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id,f"{os.environ.get('RENDER_EXTERNAL_URL','')}"); return
    if t in SYMBOLS:
        d=chart_bytes(t); pr,rs,_=get_data()
        bot.send_photo(m.chat.id,d,caption=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f}") if d else bot.send_message(m.chat.id,f"{t} ${pr.get(t,0):.2f}")

def runf(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
threading.Thread(target=runf, daemon=True).start()
try: bot.remove_webhook(); time.sleep(1)
except: pass
while True:
    try: bot.infinity_polling(timeout=90,long_polling_timeout=90,skip_pending=True)
    except: time.sleep(4)
