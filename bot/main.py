import os, asyncio, requests, json
from datetime import datetime
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BALANCE_FILE = "/tmp/balance_demo.json"
INITIAL = 1000.0

def get_price(symbol):
    # Intenta 4 APIs, una debe jalar
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot", timeout=8)
        return float(r.json()['data']['amount'])
    except: pass
    try:
        r = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={symbol}USD", timeout=8)
        key = list(r.json()['result'].keys())[0]
        return float(r.json()['result'][key]['c'][0])
    except: pass
    try:
        ids = {"BTC":"bitcoin","ETH":"ethereum","XRP":"ripple"}
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={ids[symbol]}&vs_currencies=usd", timeout=8)
        return float(r.json()[ids[symbol]]['usd'])
    except: pass
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=5)
        return float(r.json()['price'])
    except: pass
    return None

def load_bal():
    try:
        with open(BALANCE_FILE, "r") as f: return json.load(f)
    except:
        return {"usd":INITIAL,"btc":0,"eth":0,"xrp":0,"hist":[]}

def save_bal(d):
    with open(BALANCE_FILE,"w") as f: json.dump(d,f)

async def handle(update, context):
    text = update.message.text.lower()
    btc = get_price("BTC")
    eth = get_price("ETH")
    xrp = get_price("XRP")
    
    if not btc:
        await update.message.reply_text("Hola Rub! Estoy vivo, pero las APIs no me contestan. Intenta en 10 seg.")
        return

    bal = load_bal()
    total = bal["usd"] + bal["btc"]*btc + bal["eth"]*eth + bal["xrp"]*(xrp or 0)
    
    if "precio" in text:
        await update.message.reply_text(f"🔥 PRECIOS REALES:\nBTC: ${btc:,.0f}\nETH: ${eth:,.0f}\nXRP: ${xrp:.4f}\n\n💰 TU DEMO $1000:\nUSD: ${bal['usd']:.2f}\nTotal: ${total:.2f} (Gan: ${total-INITIAL:+.2f})\n\nPon: comprar btc / balance")
    elif "comprar btc" in text:
        if bal["usd"]>=100:
            bal["usd"]-=100; bal["btc"]+=100/btc; bal["hist"].append(f"Compra BTC {100/btc:.6f}"); save_bal(bal)
            await update.message.reply_text(f"✅ DEMO: Compraste $100 de BTC = {100/btc:.6f}")
        else: await update.message.reply_text("No te alcanza")
    elif "balance" in text or "ganancia" in text:
        await update.message.reply_text(f"📊 DEMO: Iniciaste ${INITIAL}\nAhora ${total:.2f}\nGanancia ${total-INITIAL:+.2f}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    await app.run_polling()

if __name__=="__main__": asyncio.run(main())
