import os, requests, threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")

PORTAFOLIO = {
    "BTC": {"cantidad": 0.01, "entrada": 65000},
    "ETH": {"cantidad": 0.1, "entrada": 3200},
    "SOL": {"cantidad": 2, "entrada": 140}
}

# Servidor falso para que Render no se queje
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot Rub 3 Cryptos Activo!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

def get_precios():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5)
        data = {item['symbol']: float(item['price']) for item in r.json()}
        return {
            "BTC": data.get("BTCUSDT", 68432),
            "ETH": data.get("ETHUSDT", 3450),
            "SOL": data.get("SOLUSDT", 165)
        }
    except:
        return {"BTC": 68432, "ETH": 3450, "SOL": 165}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot Rub 3 Cryptos Activo!\nEscribe: precio")

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    precios = get_precios()
    msg = "💰 PORTAFOLIO $1000\n\n"
    total = 0
    ganancia_total = 0
    for m, info in PORTAFOLIO.items():
        p = precios[m]
        valor = info["cantidad"] * p
        g = valor - (info["cantidad"] * info["entrada"])
        total += valor
        ganancia_total += g
        emoji = "🟢" if g >=0 else "🔴"
        msg += f"{emoji} {m}: ${p:,.2f}\n ${valor:.2f} ({g:+.2f})\n\n"
    msg += f"💵 Total: ${total:.2f}\n📈 Ganancia: ${ganancia_total:+.2f}"
    await update.message.reply_text(msg)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await precio(update, context)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("BOT 3 CRYPTOS INICIADO - Web server OK")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
