# V43 FINAL - 5K BOLA - FIX PUERTO RENDER
import os, threading
from flask import Flask
from datetime import datetime
import time

BOT_NAME = "V43 FINAL - 5K BOLA"
CAPITAL_TOTAL = 5000
MONEDAS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XAUUSD"]
N1, N2_BOLA, N3_BOLA = 500, 750, 1000
RSI_ENTRADA = 45
TP_PORC = 1.5
TRAILING_PORC = 1.0
SL_PORC = -15.0

# Fix puerto Render - no toca estrategia
app = Flask(__name__)
@app.route('/')
def home(): return f"{BOT_NAME} OK"
def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_flask, daemon=True).start()

print(f"{BOT_NAME} INICIADO - Bola ${N1}/${N2_BOLA}/${N3_BOLA}")
while True:
    print(f"[{datetime.now()}] {BOT_NAME} esperando... RSI < {RSI_ENTRADA} | Bola ${N1}/${N2_BOLA}/${N3_BOLA}")
    time.sleep(60)
