import os
import threading
from flask import Flask
import telebot
import requests
import time

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "BTC Vicente Alert - LIVE"

@bot.message_handler(commands=['start', 'precio', 'price'])
@bot.message_handler(func=lambda m: True)
def responder(m):
    texto = m.text.lower() if m.text else ""
    if "precio" in texto or "hola" in texto or "/start" in texto or "btc" in texto:
        try:
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
            precio = float(data['price'])
            bot.reply_to(m, f"🔥 BTC AHORA: ${precio:,.2f} USD\nVicente, tu bot ya jala al 100%")
        except Exception as e:
            print(f"Error precio: {e}")
            bot.reply_to(m, "Hola Rub! Estoy vivo, pero Binance no me contestó. Intenta de nuevo en 5 seg.")

def run_bot():
    time.sleep(3)
    try:
        bot.send_message(CHAT_ID, "✅ ¡BOT EN LINEA! Ya contesto Precio")
    except:
        pass
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
