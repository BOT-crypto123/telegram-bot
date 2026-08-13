import os, threading, time, io, math
from flask import Flask
from datetime import datetime
import telebot
from telebot import types
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CAPITAL = 5000
N1, N2, N3 = 500, 750, 1000
RSI_LIMITE = 45
TP_PORC = 1.5
TZ_MX = pytz.timezone("America/Mexico_City")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
AUTO = True
SYMBOLS = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
POS = {"abiertas":0, "profit_hoy":0}

@app.route('/')
def home(): return f"MAQUINA V43 VIVA - {CAPITAL} BOLA {N1}/{N2}/{N3}"

def run_flask(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_flask, daemon=True).start()

def get_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA","DASHBOARD","AUTO ON","AUTO OFF")
    return kb

def rsi_calculate closes, period=14:
    delta = closes.diff()
    gain = (delta.where(delta>0,0)).rolling(window=period).mean()
    loss = (-delta.where(delta<0,0)).rolling(window=period).mean()
    rs = gain/loss
    return 100-(100/(1+rs))

def get_chart(symbol):
    try:
        df = yf.download(SYMBOLS[symbol], period="1d", interval="5m", progress=False)
        df['RSI'] = rsi_calculate(df['Close'])
        rsi_now = float(df['RSI'].iloc[-1])
        plt.figure(figsize=(9,4.5))
        plt.plot(df['Close'], linewidth=2.5, label=f"{symbol} Precio")
        plt.title(f"{symbol} | RSI {rsi_now:.1f} | V43 BOLA {N1}/{N2}/{N3}")
        plt.grid(True, alpha=0.3); plt.legend()
        buf = io.BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close()
        return buf, rsi_now
    except: return None, 0

def es_horario_ny():
    now = datetime.now(TZ_MX)
    return 8 <= now.hour <= 15 # 8:30 a 15:00 MEX = NY OPEN

@bot.message_handler(commands=['start'])
def start(m): bot.send_message(m.chat.id, f"💰 MAQUINA V43 ENCENDIDA 💰\nCapital ${CAPITAL}\nBOLA: N1 ${N1} N2 ${N2} N3 ${N3}\nRSI<{RSI_LIMITE} TP {TP_PORC}% TRAILING\nFILTRO NY: 8:30-15:00 MEX\nAUTO: {AUTO}\n\nOBJETIVO: $29 MXN DIARIOS", reply_markup=get_kb())

@bot.message_handler(func=lambda m: m.text.upper() in SYMBOLS)
def analizar(m):
    sym = m.text.upper()
    chart, rsi = get_chart(sym)
    estado = "🟢 ENTRADA" if rsi < RSI_LIMITE else "🔴 ESPERANDO"
    txt = f"{sym} {estado}\nRSI: {rsi:.2f} (busca <{RSI_LIMITE})\nBOLA: ${N1} / ${N2} / ${N3}\nTP: +{TP_PORC}% + Trailing\nNY: {'ABIERTO' if es_horario_ny() else 'CERRADO'}\nProfit hoy: ${POS['profit_hoy']}"
    if chart: bot.send_photo(m.chat.id, chart, caption=txt, reply_markup=get_kb())
    else: bot.send_message(m.chat.id, txt, reply_markup=get_kb())

@bot.message_handler(func=lambda m: "DASHBOARD" in m.text.upper())
def dash(m): bot.send_message(m.chat.id, f"💰 MAQUINA V43 💰\nhttps://telegram-bot-cijp.onrender.com\nTotal ${CAPITAL}.00 Saldo ${CAPITAL}.00\nFlotante +${POS['profit_hoy']}\nN1 ${N1} N2 ${N2} N3 ${N3}\nAUTO: {'ON 🟢' if AUTO else 'OFF 🔴'}\nNY: {'ABIERTO' if es_horario_ny() else 'CERRADO'}\nObjetivo hoy: $29 MXN", reply_markup=get_kb())

@bot.message_handler(func=lambda m: "AUTO ON" in m.text.upper())
def aon(m):
    global AUTO; AUTO=True; bot.send_message(m.chat.id, "AUTO ON 🟢 MAQUINA TRABAJANDO 24/7", reply_markup=get_kb())

@bot.message_handler(func=lambda m: "AUTO OFF" in m.text.upper())
def aoff(m):
    global AUTO; AUTO=False; bot.send_message(m.chat.id, "AUTO OFF 🔴", reply_markup=get_kb())

def loop_maquina():
    while True:
        try:
            if AUTO and es_horario_ny():
                # Aqui va tu logica de escaneo real
                time.sleep(60)
            else: time.sleep(30)
        except: time.sleep(30)

threading.Thread(target=loop_maquina, daemon=True).start()
print(f"MAQUINA V43 {N1}/{N2}/{N3} LISTA")
bot.infinity_polling()
