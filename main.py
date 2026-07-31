import os, time, requests, telebot, threading
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(TOKEN)

CAPITAL_INICIAL = 1000.0
BTC_COMPRADO = 0.0085

def get_btc_price():
    # Intenta todo lo posible
    try:
        j = requests.get("https://api.coindesk.com/v1/bpi/currentprice/USD.json", timeout=10).json()
        return float(j["bpi"]["USD"]["rate_float"])
    except: pass
    try:
        j = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10).json()
        return float(j["data"]["amount"])
    except: pass
    try:
        j = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
        return float(j["price"])
    except: pass
    # Si todo falla, no regreses None, regresa precio de respaldo para no trabarte
    return 115000.0

@bot.message_handler(commands=['start','balance','Balance','BALANCE'])
def handle(m):
    price = get_btc_price()
    valor = BTC_COMPRADO * price
    gan = valor - CAPITAL_INICIAL
    porc = (gan / CAPITAL_INICIAL)*100 if CAPITAL_INICIAL else 0
    bot.reply_to(m, f"📊 *BTC VICENTE ALERT PRO*\n\n💰 BTC: ${price:,.2f}\n💼 Tienes: {BTC_COMPRADO} BTC\n💵 Valor: ${valor:,.2f}\n📈 Ganancia: ${gan:,.2f} ({porc:.2f}%)", parse_mode="Markdown")

def reporte_10pm():
    while True:
        try:
            ahora = datetime.now(timezone.utc) + timedelta(hours=-6)
            if ahora.hour == 22 and ahora.minute == 0:
                p = get_btc_price()
                if CHAT_ID:
                    bot.send_message(CHAT_ID, f"🌙 REPORTE 10PM\nBTC: ${p:,.2f}")
                time.sleep(61)
        except: pass
        time.sleep(30)

threading.Thread(target=reporte_10pm, daemon=True).start()
print("INICIANDO BTC VICENTE ALERT PRO...")
bot.delete_webhook(drop_pending_updates=True)
bot.infinity_polling(skip_pending=True)
