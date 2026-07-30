import os, threading, requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)
@app.route('/')
def home():
    return "BOT XRP DEMO REAL - VIVO"

TOKEN = os.environ.get("BOT_TOKEN")
INVERSION = 1000
MONEDAS = ["BTC", "ETH", "XRP"]

portfolio = {}
entrada = {}

def get_precio(s):
    try:
        m = {"BTC":"bitcoin","ETH":"ethereum","XRP":"ripple"}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={m[s]}&vs_currencies=usd"
        r = requests.get(url, timeout=10).json()
        return float(r[m[s]]['usd'])
    except:
        return {"BTC":68000,"ETH":3400,"XRP":0.60}[s]

def init():
    if portfolio: return
    for mon in MONEDAS:
        p = get_precio(mon)
        portfolio[mon] = (INVERSION/3) / p
        entrada[mon] = p

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init()
    await update.message.reply_text("✅ Bot BTC+ETH+XRP Demo REAL activo\nEscribe 'precio'")

async def precio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init()
    txt = "📊 *DEMO $1000 - GANANCIA REAL (BTC ETH XRP)*\n\n"
    total = 0
    for mon in MONEDAS:
        ahora = get_precio(mon)
        cant = portfolio[mon]
        valor = cant * ahora
        total += valor
        gan = valor - (INVERSION/3)
        emoji = "🟢" if gan>=0 else "🔴"
        txt += f"{emoji} *{mon}:* ${ahora:,.4f}\n {cant:.4f} = ${valor:.2f} ({gan:+.2f})\n\n"
    gt = total - INVERSION
    pc = (gt/INVERSION)*100
    txt += f"💰 *Total: ${total:.2f}*\n📈 *Ganancia REAL: ${gt:+.2f} ({pc:+.2f}%)*\n\nDemo - no cobrable pero precio real"
    await update.message.reply_text(txt, parse_mode='Markdown')

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__ == "__main__":
    init()
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("precio", precio_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, precio_cmd))
    print("BOT XRP INICIADO - precios reales CoinGecko")
    application.run_polling()
