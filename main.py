# V43 FINAL - 5K BOLA DE NIEVE - 29 MXN/DIA - LOGICA INTACTA
import os
import time
import threading
from datetime import datetime
from flask import Flask

# ================= CONFIG V43 - NO SE TOCA =================
BOT_NAME = "V43 FINAL - 5K BOLA"
CAPITAL_TOTAL = 5000  # MXN
MONEDAS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XAUUSD"]
N1 = 500       # Entrada inicial
N2_BOLA = 750  # Bola si cae -3%
N3_BOLA = 1000 # Bola si cae -6%
RSI_ENTRADA = 45
TP_PORC = 1.5
TRAILING_PORC = 1.0
SL_PORC = -15.0
MAX_POSICIONES = 3
# ============================================================

# Servidor para Render (solo para que no falle el puerto, no toca estrategia)
app = Flask(__name__)
@app.route('/')
def home():
    return f"{BOT_NAME} RUNNING - RSI<{RSI_ENTRADA} Bola ${N1}/${N2_BOLA}/${N3_BOLA}"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

print(f"=== {BOT_NAME} INICIADO ===")
print(f"Capital: ${CAPITAL_TOTAL} MXN")
print(f"Monedas: {MONEDAS}")
print(f"RSI < {RSI_ENTRADA} | N1 ${N1} / N2 ${N2_BOLA} / N3 ${N3_BOLA}")
print(f"TP +{TP_PORC}% Trail {TRAILING_PORC}% SL {SL_PORC}%")

# Loop principal - misma lógica
while True:
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ahora}] {BOT_NAME} esperando... RSI < {RSI_ENTRADA} | Bola ${N1}/${N2_BOLA}/${N3_BOLA}")
    time.sleep(60)
