import os
import threading
import logging
import yfinance as yf
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN")

# ===== WEB SERVER PARA QUE NO SE APAGUE - GRATIS =====
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot Cripto V10 ACTIVO - 100% Gratis"
@app.route('/health')
def health():
    return "OK"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()
# ===== FIN TRUCO =====

CRYPTO_MAP = {"btc": "BTC-USD","eth": "ETH-USD","sol": "SOL-USD","xrp": "XRP-USD"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡VICENTE! Bot V10 ACTIVO 100% GRATIS\n\nComandos:\n/estado - Ver precios\n/btc - Bitcoin\n/sol - Solana\n/eth - Ethereum")

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📊 ESTADO ACTUAL\n\n"
    for name, ticker in CRYPTO_MAP.items():
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            price = data['Close'].iloc[-1]
            msg += f"{name.upper()}: ${price:.2f}\n"
    await update.message.reply_text(msg)

async def precio_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.replace('/', '').lower()
    ticker = CRYPTO_MAP.get(cmd, f"{cmd.upper()}-USD")
    data = yf.Ticker(ticker).history(period="1d")
    if data.empty:
        await update.message.reply_text(f"No encontre {cmd.upper()}")
        return
    price = data['Close'].iloc[-1]
    await update.message.reply_text(f"{cmd.upper()}: ${price:.2f}")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("estado", estado))
    application.add_handler(CommandHandler("btc", precio_crypto))
    application.add_handler(CommandHandler("sol", precio_crypto))
    application.add_handler(CommandHandler("eth", precio_crypto))
    application.add_handler(CommandHandler("xrp", precio_crypto))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
