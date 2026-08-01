import os, time, json, threading
from flask import Flask
from telegram import Bot
import yfinance as yf

# --- Pag web para que Render no lo apague (GRATIS) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot Cripto V10 Activo - 100% Gratis"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
# --- Fin truco gratis ---

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
# ... deja el resto de tu codigo igual abajo ...
