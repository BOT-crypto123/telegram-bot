from flask import Flask
import os
import threading
import telebot # o la libreria que uses

print("INICIANDO BOT...", flush=True)

# --- TU BOT DE TELEGRAM AQUÍ ---
TOKEN = os.environ.get("BOT_TOKEN") # ponlo en Environment en Render!
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "¡Bot vivo en Render!")

def run_bot():
    print("Bot de Telegram corriendo...", flush=True)
    bot.infinity_polling()

# Inicia el bot en un hilo separado
threading.Thread(target=run_bot, daemon=True).start()

# --- SERVIDOR FLASK PARA RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot OK - Live"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Corriendo en puerto {port}", flush=True)
    app.run(host="0.0.0.0", port=port)
