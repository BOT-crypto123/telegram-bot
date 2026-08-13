import os, threading, time, io, traceback
from flask import Flask, Response, render_template_string
import telebot
from telebot import types
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
N1,N2,N3 = 500, 750, 1000
CAPITAL = 5000
TP_PCT = 1.5
TRAIL = 3.0
TZ_MX = pytz.timezone("America/Mexico_City")
SYMBOLS = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ANTI-CAIDA ---
chart_cache = {}
chart_lock = threading.Lock()
CACHE_SECONDS = 60

def rsi_calc(s, p=14):
    d = s.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    rs = g/l
    return 100-(100/(1+rs))

def puede_operar(sym):
    if sym in ["BTC","ETH","SOL"]:
        return True, "24/7 ABIERTO"
    h = datetime.now(TZ_MX).hour
    return (8 <= h < 15, "NY ABIERTO" if 8 <= h < 15 else "NY CERRADO")

def gen_chart_bytes(sym):
    with chart_lock:
        now = time.time()
        if sym in chart_cache and now - chart_cache[sym][0] < CACHE_SECONDS:
            return chart_cache[sym][1], chart_cache[sym][2]
        try:
            df = yf.download(SYMBOLS[sym], period="2d", interval="5m", progress=False, auto_adjust=True)
            if len(df)<40:
                df = yf.download(SYMBOLS[sym], period="5d", interval="15m", progress=False, auto_adjust=True)
            df['RSI']=rsi_calc(df['Close'])
            rsi=float(df['RSI'].iloc[-1])
            plt.figure(figsize=(10,4.5))
            plt.plot(df['Close'], linewidth=2.5)
            plt.title(f"{sym} | RSI {rsi:.2f} | TP {TP_PCT}% Trail {TRAIL}% | Bola ${N1}/${N2}/${N3}")
            plt.grid(True, alpha=0.3)
            buf=io.BytesIO()
            plt.savefig(buf, format='png', dpi=130, bbox_inches='tight')
            plt.close()
            buf.seek(0)
            data=buf.getvalue()
            chart_cache[sym]=(now,data,rsi)
            return data, rsi
        except Exception as e:
            print(f"Error chart {sym}: {e}")
            traceback.print_exc()
            plt.close('all')
            return None, 50.0

HTML_DASH = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0d1117;color:white;font-family:Arial;text-align:center;padding:15px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;max-width:500px;margin:auto}
.card{background:#161b22;border:1px solid #30363d;border-radius:15px;padding:20px;text-decoration:none;color:white}
.card h2{margin:5px}.green{color:#2ea043}.red{color:#f85149}
</style></head>
<body>
<h1>MAQUINA V44 FINAL</h1>
<p>Capital ${{cap}} | Bola ${{n1}}/${{n2}}/${{n3}} | TP {{tp}}% Trail {{trail}}%</p>
<p>{{hora}} | BTC/ETH/SOL 24/7</p>
<div class="grid">
{% for s in syms %}
<a class="card" href="/chart/{{s}}">
<h2>{{s}}</h2>
<p>{{status[s]}}</p>
<p>RSI {{rsis[s]}}</p>
</a>
{% endfor %}
</div>
<p style="margin-top:20px"><a href="/chart/BTC" style="color:#58a6ff">Ver BTC en vivo</a> | Profit hoy $0</p>
</body></html>
"""

@app.route('/')
def home():
    rsis={}
    status={}
    for s in SYMBOLS:
        puede, txt = puede_operar(s)
        status[s]=txt
        # usa cache si hay, si no 50
        if s in chart_cache:
            rsis[s]=f"{chart_cache[s][2]:.2f}"
        else:
            rsis[s]="--"
    return render_template_string(HTML_DASH, syms=SYMBOLS.keys(), cap=CAPITAL, n1=N1, n2=N2, n3=N3, tp=TP_PCT, trail=TRAIL, hora=datetime.now(TZ_MX).strftime("%H:%M:%S"), status=status, rsis=rsis)

@app.route('/chart/<sym>')
def chart_web(sym):
    sym=sym.upper()
    if sym not in SYMBOLS: return "No existe",404
    data,rsi=gen_chart_bytes(sym)
    if not data: return "Error temporal yfinance, reintenta",500
    return Response(data, mimetype='image/png')

# --- TELEGRAM ---
@bot.message_handler(commands=['start','balance','dashboard'])
def cmds(m):
    t=m.text.lower()
    if 'start' in t:
        kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3)
        kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA","DASHBOARD","/balance")
        bot.send_message(m.chat.id, f"MAQUINA V44 FINAL LISTA\nCapital ${CAPITAL} Bola ${N1}/${N2}/${N3}\nTP {TP_PCT}% Trail {TRAIL}%\nBTC/ETH/SOL 24/7\nDashboard: {os.environ.get('RENDER_EXTERNAL_URL','tu link de render')}", reply_markup=kb)
    else:
        bot.send_message(m.chat.id, f"Balance ${CAPITAL}\nBola {N1}/{N2}/{N3}\nTP {TP_PCT}% Trail {TRAIL}%\nPos 0/8\nProfit hoy $0")

@bot.message_handler(func=lambda m: m.text.upper() in SYMBOLS or m.text.upper()=="DASHBOARD")
def handle(m):
    sym=m.text.upper()
    if sym=="DASHBOARD":
        url=os.environ.get('RENDER_EXTERNAL_URL','https://tu-app.onrender.com')
        bot.send_message(m.chat.id, f"Dashboard web:\n{url}\nPucha cualquier moneda para ver grafica viva")
        return
    puede, horario = puede_operar(sym)
    data,rsi = gen_chart_bytes(sym)
    estado = "🟢 PUEDE ENTRAR" if rsi<45 else "🔴 ESPERANDO"
    if not puede: estado="🔴 CERRADO"
    cap=f"{sym} {estado}\nRSI {rsi:.2f} (<45)\nBOLA ${N1}/${N2}/${N3} TP {TP_PCT}% Trail {TRAIL}%\nHorario: {horario}\nCapital ${CAPITAL}"
    if data:
        bot.send_photo(m.chat.id, data, caption=cap)
    else:
        bot.send_message(m.chat.id, cap+"\nGrafica temporal no disponible")

def run_flask():
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()
try:
    bot.remove_webhook()
    time.sleep(3)
except: pass
print("V44 FINAL VIVA BTC 24/7 + DASHBOARD WEB")
while True:
    try:
        bot.infinity_polling(timeout=90, long_polling_timeout=90, skip_pending=True)
    except Exception as e:
        print(f"Restart bot {e}")
        time.sleep(5)
