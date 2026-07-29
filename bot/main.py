import os, asyncio, requests, json
from datetime import datetime
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ===== MODO DEMO - DINERO FALSO =====
BALANCE_FILE = "balance_demo.json"
INITIAL_BALANCE = 1000.0

def load_balance():
    try:
        with open(BALANCE_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "usd": INITIAL_BALANCE,
            "btc": 0, "eth": 0, "xrp": 0,
            "historial": [],
            "inicio": str(datetime.now())
        }

def save_balance(data):
    with open(BALANCE_FILE, "w") as f:
        json.dump(data, f)

def get_price(symbol):
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot", timeout=8)
        return float(r.json()['data']['amount'])
    except:
        return None

def comprar(symbol, usd_amount, price):
    bal = load_balance()
    if bal["usd"] < usd_amount:
        return f"❌ No alcanza, solo tienes ${bal['usd']:.2f}"
    cantidad = usd_amount / price
    bal["usd"] -= usd_amount
    bal[symbol.lower()] += cantidad
    bal["historial"].append(f"{datetime.now().strftime('%d/%m %H:%M')} COMPRA {symbol} {cantidad:.6f} a ${price:.2f}")
    save_balance(bal)
    return f"✅ DEMO COMPRA: ${usd_amount} de {symbol} = {cantidad:.6f} a ${price:.2f}"

def vender(symbol, cantidad, price):
    bal = load_balance()
    if bal[symbol.lower()] < cantidad:
        return f"❌ No tienes suficiente {symbol}"
    bal[symbol.lower()] -= cantidad
    bal["usd"] += cantidad * price
    bal["historial"].append(f"{datetime.now().strftime('%d/%m %H:%M')} VENTA {symbol} {cantidad:.6f} a ${price:.2f}")
    save_balance(bal)
    return f"✅ DEMO VENTA: {cantidad:.6f} {symbol} por ${cantidad*price:.2f}"

async def handle_message(update, context):
    text = update.message.text.lower()
    bal = load_balance()
    
    btc = get_price("BTC") or 0
    eth = get_price("ETH") or 0
    xrp = get_price("XRP") or 0
    
    if "precio" in text:
        valor_total = bal["usd"] + bal["btc"]*btc + bal["eth"]*eth + bal["xrp"]*xrp
        ganancia = valor_total - INITIAL_BALANCE
        await update.message.reply_text(
            f"🔥 PRECIOS:\nBTC: ${btc:,.0f}\nETH: ${eth:,.0f}\nXRP: ${xrp:.4f}\n\n"
            f"💰 TU DEMO:\nUSD: ${bal['usd']:.2f}\nBTC: {bal['btc']:.6f}\nETH: {bal['eth']:.6f}\nXRP: {bal['xrp']:.2f}\n"
            f"TOTAL: ${valor_total:.2f} ({ganancia:+.2f})"
        )
    elif "comprar btc" in text:
        await update.message.reply_text(comprar("BTC", 100, btc))
    elif "comprar eth" in text:
        await update.message.reply_text(comprar("ETH", 100, eth))
    elif "comprar xrp" in text:
        await update.message.reply_text(comprar("XRP", 100, xrp))
    elif "balance" in text or "ganancia" in text:
        valor_total = bal["usd"] + bal["btc"]*btc + bal["eth"]*eth + bal["xrp"]*xrp
        await update.message.reply_text(f"📊 BALANCE DEMO\nIniciaste: ${INITIAL_BALANCE}\nAhora: ${valor_total:.2f}\nGanancia: ${valor_total-INITIAL_BALANCE:+.2f}\n\nHistorial:\n" + "\n".join(bal["historial"][-5:]))

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
