import os, threading, requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)
@app.route('/')
def home():
    return "BOT DEMO REAL - BTC ETH XRP VIVO"

TOKEN = os.environ.get("BOT_TOKEN")
INVERSION = 1000
MONEDAS = ["BTC", "ETH", "XRP"]
DINERO_CADA = INVERSION / 3

portfolio = {}
entrada = {}

def get_precio(simbolo):
    try:
        m = {"BTC":"bitcoin","ETH":"ethereum","XRP":"ripple"}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={m[simbolo]}&vs_currencies=usd"
        r = requests.get(url, timeout=10).json()
        return float(r[m[simbolo]]['usd'])
    except:
        return {"BTC":68432,"ETH":3450,"XRP":0.60}[simbolo]

def init():
    global portfolio, entrada
    if portfolio: return
    for mon in MONEDAS:
        p = get_precio(mon)
        portfolio[mon] = DINERO_CADA / p
        entrada[mon] = p

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init()
    await update.message.reply_text("✅ Bot BTC+ETH+XRP Demo Real Activo\nEscribe 'precio'")

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init()
    txt = "📊 *DEMO $1000 - GANANCIA REAL (BTC ETH XRP)*\n\n"
    total = 0
    for mon in MONEDAS:
        ahora = get_precio(mon)
        cant = portfolio[mon]
        valor = cant * ahora
        total += valor
        gan = valor - DINERO_CADA
        emoji = "🟢" if gan>=0 else "🔴"
        txt += f"{emoji} *{mon}:* ${ahora:,.4f}\n Tienes {cant:.4f} = ${valor:.2f} ({gan:+.2f})\n\n"
    gt = total - INVERSION
    pc = (gt/INVERSION)*100
    txt += f"💰 *Total: ${total:.2f}*\n📈 *Ganancia REAL: ${gt:+.2f} ({pc:+.2f}%)*"
    await update.message.reply_text(txt, parse_mode='Markdown')

def run_bot():
    init()
    app_tg = Application.builder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, precio))
    print("BOT BTC ETH XRP INICIADO")
    app_tg.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
