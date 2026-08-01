import asyncio
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

# CONFIG V22
BUY_DROP = 0.02
SELL_GAIN = 0.022
CHECK_MIN = 300

precios_compra = {
"BTC": 63000,
"ETH": 3200,
"XRP": 0.60
}
cantidades = {
"BTC": 0.0012,
"ETH": 0.5,
"XRP": 555.55
}

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
    total = 0
    txt = "BALANCE V22\n"
    for s in ["BTC","ETH","XRP"]:
        p = get_price(s)
        if p:
            v = p * cantidades[s]
            total += v
            txt += f"\n{s}: ${p:.4f} = ${v:.2f}"
    txt += f"\n\nTOTAL: ${total:.2f}\nReviso cada 5 min."
    await update.message.reply_text(txt)

async def alertas(update, context):
    global chat_id_global
    chat_id_global = update.effective_chat.id
    await update.message.reply_text("V22 ACTIVO\nReviso cada 5 min.\n-2% COMPRA\n+2.2% VENTA")

async def cerebro(app):
    global precios_compra
    print("Cerebro V22 iniciado cada 5 min")
    while True:
        await asyncio.sleep(CHECK_MIN)
        if not chat_id_global:
            continue
        for sym in ["BTC","ETH","XRP"]:
            price = get_price(sym)
            if not price:
                continue
            compra = precios_compra[sym]
            if price <= compra * (1 - BUY_DROP):
                pct = (price-compra)/compra*100
                try:
                    await app.bot.send_message(chat_id=chat_id_global, text=f"COMPRA {sym}\nAhora: ${price:.4f}\nBajo {pct:.2f}%\nCompra: ${compra}")
                    precios_compra[sym] = price
                except:
                    pass
            elif price >= compra * (1 + SELL_GAIN):
                ganancia = (price-compra)/compra*100
                neta = ganancia - 0.20
                try:
                    await app.bot.send_message(chat_id=chat_id_global, text=f"VENTA {sym}\nAhora: ${price:.4f}\nSubio +{ganancia:.2f}%\nLimpio: +{neta:.2f}%\nCompra: ${compra}")
                    precios_compra[sym] = price
                except:
                    pass

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("xrp", xrp))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("alertas", alertas))
    app.job_queue = None
    asyncio.create_task(cerebro(app))
    print("Bot V22 listo")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
