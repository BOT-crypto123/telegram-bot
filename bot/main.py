import os
import threading
from flask import Flask
import telebot
import time
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "BOT LIVE"

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text.lower()
    if "precio" in text or "/precio" in text or "/start" in text or "hola" in text:
        try:
            # Precio de BTC
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()
            precio = r['price']
            bot.reply_to(message, f"BTC ahora: ${precio} 🔥")
        except:
            bot.reply_to(message, "Hola Rub! Bot listo")

def run_bot():
    # Avisa que prendió
    try:
        bot.send_message(CHAT_ID, "✅ ¡BOT EN LINEA! Render ya detectó el puerto y está LIVE")
    except:
        pass
    bot.infinity_polling()

if __name__ == "__main__":
    # Hilo 1: Bot
    threading.Thread(target=run_bot).start()
    # Hilo 2: Flask para Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
