import os
import time
import threading
from flask import Flask

# --- SERVIDOR PARA RENDER (OBLIGATORIO) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "V105 REAL EFECTIVO CORRIENDO - Cazando en -0.4%"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- TU BOT ---
CONFIG = {
    "FEES_PCT": 0.35,
    "MIN_RETAIL_PCT": 0.5,
    "FONDO_ENTRADA_PCT": -0.4,
    # ... tu config
}

def revisar_salidas_seguro():
    for bola in bolas_activas[:]:
        precio_actual = get_precio_actual(bola["moneda"])
        precio_compra = bola["precio_compra"]
        
        # FIX ANTI DIVISION BY ZERO
        if not precio_actual or not precio_compra:
            continue
        if precio_actual == 0 or precio_compra == 0:
            continue
            
        profit_bruta_pct = ((precio_actual - precio_compra) / precio_compra) * 100
        # ... resto de tu lógica

# Inicia servidor en hilo separado
threading.Thread(target=run_server, daemon=True).start()

# Aqui tu loop principal
while True:
    # cazar_entrada()
    # revisar_salidas_seguro()
    time.sleep(3)
