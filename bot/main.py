import os, asyncio, requests, json
from datetime import datetime
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
BALANCE_FILE = "/tmp/demo_balance.json"
INIT = 1000.0

def get_prices():
    # Intenta 1 sola llamada que trae las 3 - la más estable
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd", headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        j = r.json()
        return j['bitcoin']['usd'], j['ethereum']['usd'], j['ripple']['usd']
    except Exception as e:
        print(f"Fallo CoinGecko: {e}")
    try:
        # Respaldo Coinbase - uno por uno
        b = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10).json()['data']['amount'])
        e = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=10).json()['data']['amount'])
        x = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", timeout=10).json()['data']['amount'])
        return b,e,x
    except Exception as e:
        print(f"Fallo Coinbase: {e}")
    return None, None, None

def load_bal():
    try:
        with open(BALANCE_FILE,"r") as f: return json.load(f)
    except:
        return {"usd":INIT,"btc":0,"eth":0,"xrp":0}

def save_bal(d):
    with open(BALANCE_FILE,"w") as f: json.dump(d,f)

async def handle(update, context):
    txt = update.message.text.lower()
    btc, eth, xrp = get_prices()
    
    print(f"Precios obtenidos: BTC={btc} ETH={eth} XRP={xrp}")
    
    if not btc:
        await update.message.reply_text("Estoy vivo, pero CoinGecko me bloqueó 30 seg. Mándame Precio otra vez en 20 seg y ya jala.")
        return

    bal = load_bal()
    total = bal["usd"] + bal["btc"]*btc + bal["eth"]*eth + bal["xrp"]*xrp

    if "precio" in txt:
        await update.message.reply_text(f"🔥 REAL:\nBTC ${btc:,.0f}\nETH ${eth:,.0f}\nXRP ${xrp:.4f}\n\n💰 DEMO $1000:\nUSD ${bal['usd']:.2f}\nTotal ${total:.2f} Gan {total-INIT:+.2f}\n\nEscribe: comprar btc / balance")
    elif "comprar btc" in txt and bal["usd"]>=100:
        bal["usd"]-=100; bal["btc"]+=100/btc; save_bal(bal)
        await update.message.reply_text(f"✅ DEMO Compraste $100 BTC")
    elif "balance" in txt:
        await update.message.reply_text(f"📊 DEMO: Inicio ${INIT} -> Ahora ${total:.2f} Ganancia ${total-INIT:+.2f}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("BOT DEMO INICIADO")
    await app.run_polling()

if __name__=="__main__":
    asyncio.run(main())
