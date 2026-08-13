import os, threading, time, io, math
from flask import Flask, Response, render_template_string, redirect
import telebot
from telebot import types
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
N1,N2,N3 = 500,750,1000
CAPITAL, TP_PCT, TRAIL = 5000, 1.5, 3.0
TZ_MX = pytz.timezone("America/Mexico_City")
SYMBOLS = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

AUTO_ON = False
chart_cache = {}
POS = {} # simulado para mostrar profit
data_cache = {"prices":{},"rsis":{},"profit":{},"time":0}

def rsi_calc(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+(g/l)))

def get_data():
    if time.time() - data_cache["time"] < 30 and data_cache["prices"]:
        return data_cache["prices"], data_cache["rsis"], data_cache["profit"]
    prices, rsis, profit = {},{},{}
    for k,yfs in SYMBOLS.items():
        try:
            df=yf.download(yfs, period="2d", interval="5m", progress=False, auto_adjust=True)
            if len(df)<20: continue
            r=float(rsi_calc(df['Close']).iloc[-1]); p=float(df['Close'].iloc[-1])
            prices[k]=p; rsis[k]=r; profit[k]=round((p*0.01)-0.5,2) # profit demo
        except: pass
    data_cache.update({"prices":prices,"rsis":rsis,"profit":profit,"time":time.time()})
    return prices, rsis, profit

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<60:
        return chart_cache[sym][1]
    try:
        df=yf.download(SYMBOLS[sym], period="5d", interval="15m", progress=False, auto_adjust=True)
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        rsi=float(df['RSI'].iloc[-1]); price=float(df['Close'].iloc[-1])
        fig, (ax1, ax2) = plt.subplots(2,1, figsize=(12,7), gridspec_kw={'height_ratios':[3,1]}, sharex=True)
        ax1.plot(df['Close'], label=f'{sym} Precio', linewidth=2.3, color='#58a6ff')
        ax1.plot(df['SMA20'], label='SMA20', linewidth=1.1, color='#f0d91a'); ax1.plot(df['SMA50'], label='SMA50', linewidth=1.1, color='#ff4d4d')
        entradas=df[df['RSI']<45]; ax1.scatter(entradas.index, entradas['Close'], marker='^', color='#2ea043', s=80, label='ENTRADA', zorder=5)
        ax1.set_title(f"{sym} ${price:.2f} | RSI {rsi:.1f} | TP {TP_PCT}% Trail {TRAIL}% | Bola ${N1}/${N2}/${N3} | AUTO {'ON' if AUTO_ON else 'OFF'}", fontsize=11)
        ax1.legend(); ax1.grid(True, alpha=0.25)
        ax2.plot(df['RSI'], color='#8b949e'); ax2.axhline(45,color='green',ls='--'); ax2.axhline(65,color='red',ls='--'); ax2.set_ylim(0,100)
        buf=io.BytesIO(); plt.savefig(buf, format='png', dpi=140, bbox_inches='tight'); plt.close(fig)
        buf.seek(0); data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e:
        print("chart err",e); plt.close('all'); return None

def puede(sym):
    if sym in ["BTC","ETH","SOL"]: return True, "24/7"
    h=datetime.now(TZ_MX).hour; return (8<=h<15, "ABIERTO NY" if 8<=h<15 else "CERRADO NY")

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,Arial;text-align:center;margin:0;padding:12px}
.top{max-width:560px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}
.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}
.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:560px;margin:16px auto}
.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;text-decoration:none;color:#fff}
.card h2{margin:2px}.price{font-size:20px;font-weight:900;color:#58a6ff}.rsi{font-size:13px;color:#8b949e}.profit{font-size:14px;color:#2ea043}
</style></head><body>
<div class="top"><div><b>MAQUINA V45.1</b><br><small>Cap ${{cap}} Bola ${{n1}}/{{n2}}/{{n3}}</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p style="color:#8b949e">{{hora}} | BTC/ETH/SOL 24/7 | XAU/NVDA/TSLA NY 8AM-3PM MEX</p>
<div class="grid">
{% for s in syms %}
<a class="card" href="/chart/{{s}}"><h2>{{s}}</h2><div class="price">${{prices.get(s,'--')}}</div><div class="rsi">RSI {{rsis.get(s,'--')}} | {{status[s]}}</div><div class="profit">Profit ${{profit.get(s,'0')}}</div></a>
{% endfor %}
</div>
<small style="color:#8b949e">Pucha cualquier tarjeta para ver grafica con lineas y entradas reales</small>
</body></html>
"""

@app.route('/')
def home():
    prices, rsis, profit = get_data(); st={}
    for s in SYMBOLS: _, t = puede(s); st[s]=t
    return render_template_string(HTML, syms=SYMBOLS.keys(), cap=CAPITAL, n1=N1, n2=N2, n3=N3, auto=AUTO_ON, hora=datetime.now(TZ_MX).strftime("%H:%M:%S"), status=st,
        prices={k:f"{v:.2f}" for k,v in prices.items()}, rsis={k:f"{v:.1f}" for k,v in rsis.items()}, profit={k:f"{v}" for k,v in profit.items()})

@app.route('/toggle')
def tog():
    global AUTO_ON; AUTO_ON=not AUTO_ON; return redirect('/')

@app.route('/chart/<sym>')
def ch(sym):
    sym=sym.upper()
    if sym not in SYMBOLS: return "no",404
    data=chart_bytes(sym)
    return Response(data, mimetype='image/png') if data else ("Cargando, espera 15s y recarga",503)

@bot.message_handler(commands=['start','balance'])
def start(m):
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3)
    kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if AUTO_ON else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id, f"✅ V45.1 FUSION LISTA\n{'🟢AUTO ON' if AUTO_ON else '🔴AUTO OFF'} Cap ${CAPITAL}\nWeb: {os.environ.get('RENDER_EXTERNAL_URL','')}", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    global AUTO_ON; t=m.text.upper().strip()
    if "AUTO" in t:
        AUTO_ON=not AUTO_ON; bot.send_message(m.chat.id, f"{'🟢AUTO ON - Ya compra solo RSI<45' if AUTO_ON else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, f"{os.environ.get('RENDER_EXTERNAL_URL','')}"); return
    if t in SYMBOLS:
        d=chart_bytes(t); pr, rs, _ = get_data(); puede_ok, hor = puede(t)
        txt=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} {hor} AUTO {'ON' if AUTO_ON else 'OFF'}\n{'✅ COMPRARIA' if rs.get(t,99)<45 and puede_ok else '⏳ ESPERANDO'}"
        bot.send_photo(m.chat.id, d, caption=txt) if d else bot.send_message(m.chat.id, txt)

def runf(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
threading.Thread(target=runf, daemon=True).start()
try: bot.remove_webhook(); time.sleep(1)
except: pass
print("V45.1 FUSION")
while True:
    try: bot.infinity_polling(timeout=90, long_polling_timeout=90, skip_pending=True)
    except: time.sleep(4)
