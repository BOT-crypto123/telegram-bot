import os, time, threading
from flask import Flask
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def home():
    return f"V105.3 REAL CONTABLE OK - {datetime.now()}"
def run_server():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), debug=False)
threading.Thread(target=run_server, daemon=True).start()

# --- CONFIG V105.3 REAL ---
CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "BOLAS_MAX": 10,
    "COSTO_BOLA": 1031.63,
    "FEES_PCT": 0.35,
    "MIN_RETAIL_PCT": 0.3,
    "STOP_PCT": -7.0,
    "TRAIL_PCT": 0.2,
    "FONDO_PCT": -0.4,
    "REBOTE_PCT": 0.08,
    "MONEDAS_PERMITIDAS": ["BTC","ETH","SOL","DOGE","XRP","ADA","AVAX"], # SHIB ELIMINADO
}

bolas_activas = [
    {"moneda": "ETH", "precio_compra": 40049.34, "costo": 1031.63},
    {"moneda": "XRP", "precio_compra": 22.24, "costo": 1031.63}
]
historial_cerradas = []

def precio_valido(p):
    if not p: return False
    if p == 0: return False
    if p < 0.001: return False
    return True

def calcular_ganancia(precio_entrada, precio_actual, costo):
    if not precio_valido(precio_entrada) or not precio_valido(precio_actual):
        return 0, 0, 0
    if precio_entrada < 0.00001:
        return 0, 0, 0
    pct_bruto = ((precio_actual - precio_entrada) / precio_entrada) * 100
    pct_neto = pct_bruto - CONFIG["FEES_PCT"]
    usd = costo * (pct_neto / 100)
    return pct_bruto, pct_neto, usd

def get_precio_actual(moneda):
    # AQUI PONES TU API REAL DE COINBASE
    mock = {"BTC": 1273222.19, "ETH": 39926.52, "SOL": 1531.61, "DOGE": 1.42, "XRP": 22.13, "ADA": 3.54, "AVAX": 125.33}
    return mock.get(moneda, 0)

def revisar_y_mostrar():
    print("\n--- BOLAS ABIERTAS (FLOTANTE EN ROJO) ---")
    perdida_flotante_total = 0
    for bola in bolas_activas:
        actual = get_precio_actual(bola["moneda"])
        if not precio_valido(actual):
            continue
        bruto, neto, usd = calcular_ganancia(bola["precio_compra"], actual, bola["costo"])
        perdida_flotante_total += usd
        
        color = "🟢" if neto >= 0 else "🔴"
        estado = f"{bola['moneda']} E {bola['precio_compra']} -> {actual} ({neto:.2f}% neto) ${usd:.2f} {color} FLOTANTE"
        
        # SI CIERRA EN STOP -7%
        if neto <= CONFIG["STOP_PCT"]:
            print(f"🔴 STOP {estado} -> CERRANDO Y REGISTRANDO PERDIDA DEFINITIVA")
            historial_cerradas.append({"moneda": bola["moneda"], "neto": neto, "usd": usd, "status": "PER"})
            bolas_activas.remove(bola)
            CONFIG["ACUMULADO"] += usd
        else:
            print(estado)

    print(f"PERDIDA FLOTANTE TOTAL: ${perdida_flotante_total:.2f}")
    print("\n--- DESGLOSE REAL (SOLO CERRADAS) ---")
    for h in historial_cerradas:
        print(f"{h['moneda']} PER {h['neto']:.2f}% ${h['usd']:.2f} -> ACUMULADO: ${CONFIG['ACUMULADO']:.2f}")

print("🚀 V105.3 REAL CONTABLE - SHIB BORRADO - LISTO")
while True:
    try:
        revisar_y_mostrar()
        time.sleep(10)
    except ZeroDivisionError:
        print("ZeroDivision bloqueado, continuando...")
        time.sleep(3)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(3)
