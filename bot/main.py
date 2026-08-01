import asyncio
import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
BUY_DROP = 0.02
SELL_GAIN = 0.022
CHECK_MIN = 300

precios_compra = {"BTC": 63000, "ETH": 3200, "XRP": 0.60}
cantidades = {"BTC": 0.0012, "ETH": 0.5, "XRP": 555.55}
chat_id_global = None

def get_price(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=10)
        return float(r.json()["price"])
    except:
        return None

async def btc(update, context):
    global chat_id_global
    chat_id_global = update.effective_chat.id
    p = get_price("BTC")
    await update.message.reply_text(f"BTC: ${p:,.2f}")

async def eth(update, context):
    global chat_id_global
    chat_id_global = update.effective_chat.id
    p = get_price("ETH")
    await update.message.reply_text(f"ETH: ${p:,.2f}")

async def xrp(update, context):
    global chat_id_global
    chat_id_global = update.effective_chat.id
    p = get_price("XRP")
    await update.message.reply_text(f"XRP: ${p:.4f}")

async def balance(update, context):
    global chat_id_global
    chat_id_global = update.effective_chat.id
    total=0
    txt="BALANCE V22.1\n"
    for s in ["BTC","ETH","XRP"]:
        p=get_price(s)
        if p:
            v=p*cantidades[s]
            total+=v
            txt+=f"\n{s}: ${v:.2f}"
    txt+=f"\n\nTOTAL: ${total:.2f}"
    await update.message.reply_text(txt)

async def alertas(update, context):
    global chat_id_global
    chat_id_global = update.effective_chat.id
    await update.message.reply_text("V22.1 ACTIVO - Reviso cada 5 min")

async def cerebro(app):
    global precios_compra
    while True:
        await asyncio.sleep(CHECK_MIN)
        if not chat_id_global:
            continue
        for sym in ["BTC","ETH","XRP"]:
            price=get_price(sym)
            if not price: continue
            compra=precios_compra[sym]
            if price <= compra * (1 - BUY_DROP):
                try:
                    await app.bot.send_message(chat_id=chat_id_global, text=f"COMPRA {sym} ${price:.4f}")
                    precios_compra[sym]=price
                except: pass
            elif price >= compra * (1 + SELL_GAIN):
                try:
                    await app.bot.send_message(chat_id=chat_id_global, text=f"VENTA {sym} ${price:.4f}")
                    precios_compra[sym]=price
                except: pass

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot V22.1 OK")
    def log_message(self, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

async def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("xrp", xrp))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("alertas", alertas))
    asyncio.create_task(cerebro(app))
    print("Bot V22.1 listo")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
