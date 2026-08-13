import os, threading
from flask import Flask
from datetime import datetime
import time

# V43 FINAL - NO SE TOCA ESTRATEGIA
BOT_NAME = "V43 FINAL - 5K BOLA"
N1, N2_BOLA, N3_BOLA = 500, 750, 1000
RSI_ENTRADA = 45

app = Flask(__name__)
@app.route('/')
def home(): return "V43 OK - LIVE"
def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_flask, daemon=True).start()

while True:
    print(f"[{datetime.now()}] {BOT_NAME} esperando... RSI < {RSI_ENTRADA} | Bola ${N1}/${N2_BOLA}/${N3_BOLA}", flush=True)
    time.sleep(60)
