import os, time, io, requests, threading
from flask import Flask, Response, render_template_string, redirect, request
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
URL = os.environ.get("RENDER_EXTERNAL_URL","").strip().rstrip("/")
SYMBOLS = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
AUTO_ON = False
chart_cache = {}
data_cache = {"prices":{},"rsis":{},"time":0}
TZ_MX = pytz.timezone("America/Mexico_City")

def get_price_kraken(sym):
    try:
        pair={"BTC":"BTCUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[sym]
        r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}", timeout=6).json()
        key=list(r['result'].keys())[0]
        return float(r['result'][key]['c'][0])
    except: return None

def get_price_coingecko(sym):
    try:
        id_map={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}[sym]
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={id_map}&vs_currencies=usd", timeout=6).json()
        return float(r[id_map]['usd'])
    except: return None

def get_klines_coingecko(sym):
    try:
        id_map={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}[sym]
        r=requests.get(f"https://api.coingecko.com/api/v3/coins/{id_map}/market_chart?vs_currency=usd&days=2", timeout=8).json()
        prices=r['prices'] # [[ts, price]]
        df=pd.DataFrame(prices, columns=['t','Close']); df['t']=pd.to_datetime(df['t'], unit='ms'); df=df.set_index('t')
        df=df.resample('15min').last().dropna(); return df
    except: return None

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean(); return 100-(100/(1+(g/l)))

def get_data():
    if time.time()-data_cache["time"]<15 and data_cache["prices"]: return data_cache["prices"], data_cache["rsis"]
    prices, rsis={},{}
    for k in SYMBOLS:
        pr=None
        if k in ["BTC","ETH","SOL"]:
            pr = get_price_kraken(k)
            if pr is None: pr = get_price_coingecko(k)
        if pr is None:
            try:
                df=yf.download(SYMBOLS[k], period="1d", interval="5m", progress=False, auto_adjust=True, threads=False)
                if len(df)>5: pr=float(df['Close'].iloc[-1])
            except: pass
        if pr is None: pr=0
        # RSI
        try:
            df_r = get_klines_coingecko(k) if k in ["BTC","ETH","SOL"] else None
            if df_r is None or len(df_r)<20:
                df_r=yf.download(SYMBOLS[k], period="5d", interval="15m", progress=False, auto_adjust=True, threads=False)
            r_val=float(rsi(df_r['Close']).iloc[-1]) if df_r is not None and len(df_r)>14 else 50.0
        except: r_val=50.0
        prices[k]=pr; rsis[k]=r_val
    data_cache.update({"prices":prices,"rsis":rsis,"time":time.time()}); return prices, rsis

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<60: return chart_cache[sym][1]
    try:
        df=get_klines_coingecko(sym) if sym in ["BTC","ETH","SOL"] else None
        if df is None: df=yf.download(SYMBOLS[sym], period="5d", interval="15m", progress=False, auto_adjust=True, threads=False)
        if df is None or len(df)<20: return None
        df['RSI']=rsi(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        price=float(df['Close'].iloc[-1]); rsi_v=float(df['RSI'].iloc[-1])
        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,5),gridspec_kw={'height_ratios':[3,1]},sharex=True)
        ax1.plot(df['Close'],linewidth=2,label='Precio'); ax1.plot(df['SMA20'],linewidth=1,alpha=.7); ax1.plot(df['SMA50'],linewidth=1,alpha=.7)
        ax1.scatter(df[df['RSI']<45].index, df[df['RSI']<45]['Close'], marker='^', color='green', s=60, label='ENTRADA')
        ax1.set_title(f"{sym} ${price:.2f} RSI {rsi_v:.1f} AUTO {'ON' if AUTO_ON else 'OFF'}"); ax1.legend(); ax1.grid(True,alpha=.3)
        ax2.plot(df['RSI']); ax2.axhline(45,color='green',ls='--')
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=120,bbox_inches='tight'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e: print(e); plt.close('all'); return None

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:10px}.top{max-width:560px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:560px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:14px;text-decoration:none;color:#fff}.price{font-size:22px;font-weight:900;color:#58a6ff}</style></head><body>
<div class="top"><div><b>MAQUINA V45.4 FINAL</b><br><small>Cap $5000 Bola $500/750/1000 - Kraken+CG</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | Datos por Kraken/CoinGecko | WEBHOOK</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}"><h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div></a>{% endfor %}
</div></body></html>"""

@app.route('/')
def home():
    pr,rs=get_data()
    return render_template_string(HTML, syms=SYMBOLS.keys(), auto=AUTO_ON, hora=datetime.now(TZ_MX).strftime("%H:%M:%S"),
        prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})

@app.route('/toggle')
def tog(): global AUTO_ON; AUTO_ON=not AUTO_ON; return redirect('/')
@app.route('/chart/<sym>')
def ch(sym): d=chart_bytes(sym.upper()); return Response(d,mimetype='image/png') if d else ("Generando...",503)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''

@bot.message_handler(commands=['start','balance'])
def start(m):
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if AUTO_ON else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id,f"✅ V45.4 KRAKEN FIX\n{'🟢AUTO ON' if AUTO_ON else '🔴AUTO OFF'}\n{URL}",reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    global AUTO_ON; t=m.text.upper().strip()
    if "AUTO" in t: AUTO_ON=not AUTO_ON; bot.send_message(m.chat.id,f"{'🟢AUTO ON' if AUTO_ON else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in SYMBOLS: d=chart_bytes(t); pr,rs=get_data(); bot.send_photo(m.chat.id,d,caption=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f}") if d else bot.send_message(m.chat.id,f"{t} ${pr.get(t,0):.2f}")

# set webhook
try:
    if URL:
        bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V45.4 OK")
except Exception as e: print(e)

app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
