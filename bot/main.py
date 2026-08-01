import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
print(f"Token encontrado: {'SI' if TOKEN else 'NO'}")

def get_price(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=10)
        return float(r.json()["price"])
    except Exception as e:
        print(f"Error precio {symbol}: {e}")
        return None

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price("BTC")
    await update.message.reply_text(f"BTC: ${p:,.2f}" if p else "Error BTC")

async def eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price("ETH")
    await update.message.reply_text(f"ETH: ${p:,.2f}" if p else "Error ETH")

async def xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price("XRP")
    await update.message.reply_text(f"XRP: ${p:.4f}" if p else "Error XRP")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt="BALANCE V22.2\n"
    total=0
    for s, cant in [("BTC",0.0012),("ETH",0.5),("XRP",555.55)]:
        p=get_price(s)
        if p:
            v=p*cant
            total+=v
            txt+=f"\n{s}: ${v:.2f}"
    txt+=f"\n\nTOTAL: ${total:.2f}"
    await update.message.reply_text(txt)

async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("V22.2 ACTIVO ✅ - Usa /btc /eth /xrp /balance")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot V22.2 OK - Live")
    def log_message(self, *a):
        pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Iniciando Bot V22.2...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("xrp", xrp))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("alertas", alertas))
    app.add_handler(CommandHandler("start", alertas))
    print("Bot V22.2 listo - polling")
    app.run_polling()
