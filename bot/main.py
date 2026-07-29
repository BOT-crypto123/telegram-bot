from flask import Flask
import threading
import os, asyncio, aiohttp
from telegram import Bot
import numpy as np

# --- ESTO ES PARA QUE RENDER NO LO APAGUE ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot running OK"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
# --- FIN ---

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT"]

async def main():
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="✅ Bot XRP conectado en Render - Quedó verde!")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
