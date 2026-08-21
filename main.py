import os
import time
import threading
from flask import Flask
from datetime import datetime

# --- SERVIDOR RENDER - OBLIGATORIO PARA QUE NO TE MARQUE ERROR DE PORT ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"V105 REAL EFECTIVO - {datetime.now()} - Cazando en -0.4% - OK"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Hilo del servidor
threading.Thread(target=run_server, daemon=True).start()

# --- CONFIG V105 REAL ---
CONFIG = {
    "BASE": 10000.0,
    "BOLAS": 7,
    "FEES_PCT": 0.35,
    "MIN_RETAIL_PCT": 0.5,
    "TRAIL_PCT": 0.2,
    "STOP_PCT": -7.0,
    "FONDO_ENTRADA_PCT": -0.4,
    "REBOTE_ENTRADA_PCT": 0.05,
    "ACUMULADO": 310.0
}

# Estado
bolas_activas = []
BALANCE = CONFIG["BASE"] + CONFIG["ACUMULADO"]

def get_precio_actual(moneda):
    # MOCK SEGURO - AQUI PONES TU API REAL DE COINBASE
    # Por ahora regresa precio falso para que no truene
    precios_mock = {"SOL": 180.5, "DOGE": 0.15, "XRP": 0.6, "ADA": 0.45, "AVAX": 30.0, "SHIB": 0.00002, "BONK": 0.00003}
    return precios_mock.get(moneda, 100.0)  # Nunca regresa 0

def revisar_salidas_seguro():
    global bolas_activas
    if not bolas_activas:
        return

    for bola in bolas_activas[:]:
        try:
            precio_actual = get_precio_actual(bola.get("moneda", "SOL"))
            precio_compra = bola.get("precio_compra", 0)

            # BLINDAJE ANTI DIVISION BY ZERO
            if not precio_actual or not precio_compra:
                continue
            if precio_actual == 0 or precio_compra == 0:
                continue
            if precio_compra < 0.0000001:
                continue

            profit_bruta_pct = ((precio_actual - precio_compra) / precio_compra) * 100
            print(f"Chequeo {bola['moneda']}: {profit_bruta_pct:.2f}%")

        except ZeroDivisionError:
            print(f"Skip division by zero en {bola}")
            continue
        except Exception as e:
            print(f"Error en bola: {e}")
            continue

def cazar_simulado():
    # Solo para que Render vea actividad
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Cazando en {CONFIG['FONDO_ENTRADA_PCT']}% - Bolas: {len(bolas_activas)}/{CONFIG['BOLAS']} - Balance: ${BALANCE}")

# --- LOOP PRINCIPAL ---
print("🚀 V105 REAL EFECTIVO INICIADO")
while True:
    try:
        cazar_simulado()
        revisar_salidas_seguro()
        time.sleep(10)
    except ZeroDivisionError as e:
        print(f"ZeroDivision atrapado: {e} - continuando")
        time.sleep(5)
    except Exception as e:
        print(f"Error general: {e}")
        time.sleep(5)
