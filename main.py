import os, time, requests, telebot, threading
from datetime import datetime, timezone, timedelta
from flask import Flask

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(TOKEN, threaded=False)

CAPITAL_INICIAL = 1000.0
BTC_COMPRADO = 0.0085

def get_btc_price():
    urls = [
        "https://api.coindesk.com/v1/bpi/currentprice/USD.json",
        "https://api.coinbase.com/v2/prices/BTC-USD/spot",
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api.kraken.com/0/public/Ticker?pair=BTCUSD"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10).json()
            if "bpi" in str(r): return float(r["bpi"]["USD"]["rate_float"])
            if "data" in r: return float(r["data"]["amount"])
            if "price" in r: return float(r["price"])
            if "result" in r: return float(list(r["result"].values())[0]["c"][0])
        except:
            continue
    # Si TODO falla, regresa precio fijo para no romper el bot
    return 115000.0

@bot.message_handler(commands=['start','balance','Balance','BALANCE'])
def handle(m):
    price = get_btc_price()
    valor = BTC_COMPRADO * price
    gan = valor - CAPITAL_INICIAL
    porc = (gan / CAPITAL_INICIAL * 100) if CAPITAL_INICIAL else 0
    txt = f"""📊 *BTC VICENTE ALERT PRO*

💰 *Precio BTC:* ${price:,.2f}
💼 *Tienes:* {BTC_COMPRADO} BTC
💵 *Valor actual:* ${valor:,.2f}
📈 *Ganancia:* ${gan:,.2f} ({porc:+.2f}%)

✅ Bot vivo en Render"""
    bot.reply_to(m, txt, parse_mode="Markdown")

def reporte_10pm():
    while True:
        try:
            ahora = datetime.now(timezone.utc) + timedelta(hours=-6)
            if ahora.hour == 22 and ahora.minute == 0:
                p = get_btc_price()
                if CHAT_ID:
                    try: bot.send_message(CHAT_ID, f"🌙 *REPORTE 10PM*\nBTC: ${p:,.2f}\nValor: ${BTC_COMPRADO*p:,.2f}")
                    except: pass
                time.sleep(70)
        except: pass
        time.sleep(30)

threading.Thread(target=reporte_10pm, daemon=True).start()

# Servidor web fantasma para que Render no te duplique el bot y no de 409
app = Flask(__name__)
@app.route('/')
def home(): return "BTC Bot Vivo", 200
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

print("=== BTC VICENTE ALERT PRO INICIADO ===")
bot.delete_webhook(drop_pending_updates=True)
time.sleep(2)
bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
