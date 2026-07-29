import os
import telebot
import requests
import threading
from flask import Flask

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render Environment Variables")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "BOT EN LINEA - BTC Vicente Alert", 200

# --- FUNCION DE PRECIO QUE SI JALA EN RENDER ---
def get_btc_price():
    try:
        # Intento 1: Binance
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except Exception as e:
        print(f"Fallo Binance: {e}")

    try:
        # Intento 2: CoinGecko - este es el bueno para Render
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        r = requests.get(url, timeout=10)
        data = r.json()
        return float(data['bitcoin']['usd'])
    except Exception as e:
        print(f"Fallo CoinGecko: {e}")
        return None

# --- COMANDOS DEL BOT ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola Rub! Soy tu BTC Vicente Alert 🚀\n\nEscribe:\n*Precio* - para ver el BTC ahora\n*Hola* - para saludar")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    texto = message.text.lower().strip()
    
    if "precio" in texto or "btc" in texto:
        bot.send_chat_action(message.chat.id, 'typing')
        precio = get_btc_price()
        if precio is None:
            bot.reply_to(message, "Hola Rub! Estoy vivo, pero las APIs no me contestan. Intenta en 10 seg.")
        else:
            bot.reply_to(message, f"🔥 BTC AHORA: ${precio:,.2f} USD\n\n¿Quieres que te avise si baja?")
    elif "hola" in texto or "ola" in texto:
        precio = get_btc_price()
        if precio:
            bot.reply_to(message, f"Hola Rub! 🙋‍♂️ BTC está en ${precio:,.2f}")
        else:
            bot.reply_to(message, "¡Hola Rub! Estoy vivo ✅")
    else:
        bot.reply_to(message, f"Recibido: {message.text}\nEscribe *Precio* para ver el BTC")

# --- PARA QUE RENDER NO LO APAGUE ---
def run_bot():
    print("BOT INICIANDO...")
    bot.infinity_polling(none_stop=True, timeout=60)

# Inicia el bot en un hilo
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
