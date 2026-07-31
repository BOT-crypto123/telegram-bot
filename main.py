import os
import time
import requests
import telebot
from datetime import datetime, timezone, timedelta
import threading

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

# --- SIMULADOR (pon aquí tu compra real) ---
CAPITAL_INICIAL = 1000.0  # USD que metiste
BTC_COMPRADO = 0.0085      # cuánto BTC compraste

def get_btc_price():
    # 1. Binance
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5).json()
        return float(r["price"])
    except:
        pass
    # 2. Coinbase
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except:
        pass
    # 3. Coingecko
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5).json()
        return float(r["bitcoin"]["usd"])
    except:
        return None

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "¡Bot vivo en Render! 🚀\nUsa /balance para tu reporte.")

@bot.message_handler(commands=['balance', 'Balance', 'BALANCE'])
def balance(m):
    price = get_btc_price()
    if not price:
        bot.reply_to(m, "Error precio, intenta en 10 segundos. Las APIs están lentas.")
        return

    valor_actual = BTC_COMPRADO * price
    ganancia = valor_actual - CAPITAL_INICIAL
    porcentaje = (ganancia / CAPITAL_INICIAL) * 100

    msg = f"""📊 *BTC VICENTE ALERT PRO*

💰 Precio BTC: ${price:,.2f} USD
💼 Tienes: {BTC_COMPRADO} BTC
💵 Valor actual: ${valor_actual:,.2f} USD
📈 Ganancia: ${ganancia:,.2f} USD ({porcentaje:.2f}%)

Capital inicial: ${CAPITAL_INICIAL}
"""
    bot.reply_to(m, msg, parse_mode="Markdown")

def reporte_10pm():
    while True:
        try:
            # Hora México
            ahora_mx = datetime.now(timezone.utc) + timedelta(hours=-6)
            if ahora_mx.hour == 22 and ahora_mx.minute == 0:
                price = get_btc_price()
                if price and CHAT_ID:
                    valor_actual = BTC_COMPRADO * price
                    ganancia = valor_actual - CAPITAL_INICIAL
                    texto = f"🌙 *REPORTE 10PM*\nBTC: ${price:,.2f}\nValor: ${valor_actual:,.2f}\nGanancia: ${ganancia:,.2f}"
                    bot.send_message(CHAT_ID, texto, parse_mode="Markdown")
                    time.sleep(61) # para no repetir
        except Exception as e:
            print(f"Error reporte: {e}")
        time.sleep(30)

print("INICIANDO BTC VICENTE ALERT PRO + REPORTE 10PM...")
# Inicia reporte en segundo plano
threading.Thread(target=reporte_10pm, daemon=True).start()

# Esto evita el error 409
bot.delete_webhook(drop_pending_updates=True)
bot.infinity_polling(skip_pending=True)
