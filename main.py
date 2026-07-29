import os, asyncio, requests, json
from datetime import datetime
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
BALANCE_FILE = "/tmp/demo_balance.json"
INIT = 1000.0

def get_prices():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd", timeout=10)
        j = r.json()
        return j['bitcoin']['usd'], j['ethereum']['usd'], j['ripple']['usd']
    except:
        return 68000, 3500, 0.6

def get_bal():
    try:
        if os.path.exists(BALANCE_FILE):
            with open(BALANCE_FILE) as f: return json.load(f)
    except: pass
    return {"usd": INIT, "btc": 0, "eth": 0, "xrp": 0}

def save_bal(b):
    try:
        with open(BALANCE_FILE, 'w') as f: json.dump(b, f)
    except: pass

async def handle(update, context):
    text = (update.message.text or "").lower().strip()
    bal = get_bal()
    btc_p, eth_p, xrp_p = get_prices()
    total = bal["usd"] + bal["btc"]*btc_p + bal["eth"]*eth_p + bal["xrp"]*xrp_p
    
    if "precio" in text or "price" in text:
        await update.message.reply_text(f"📊 PRECIOS DEMO:\nBTC: ${btc_p}\nETH: ${eth_p}\nXRP: ${xrp_p}\n\n💰 Tu balance demo: ${total:.2f} / ${INIT}")
        return
    if "balance" in text or "saldo" in text:
        await update.message.reply_text(f"💰 BALANCE DEMO\nUSD: ${bal['usd']:.2f}\nBTC: {bal['btc']}\nETH: {bal['eth']}\nXRP: {bal['xrp']}\nTotal: ${total:.2f}")
        return
    if text.startswith("comprar"):
        await update.message.reply_text(f"✅ Compra DEMO simulada. Balance: ${total:.2f}")
        return
    if text.startswith("vender"):
        await update.message.reply_text(f"✅ Venta DEMO simulada. Balance: ${total:.2f}")
        return

    await update.message.reply_text("🤖 Bot DEMO $1000 listo!\nEscribe:\n- precio\n- balance\n- comprar btc 100\n- vender btc 100")

if __name__ == "__main__":
    print("BOT DEMO INICIADO - $1000")
    print(f"Token existe: {bool(TOKEN)}")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
