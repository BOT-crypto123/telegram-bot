import os
import time
import json
import threading
import pytz
from datetime import datetime
from flask import Flask

# ========== FIX PARA RENDER (WEB SERVICE) ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 LA MAQUINA DE HACER DINERO V48.5 MODO 10K ACTIVA 💰 - LIVE"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_server, daemon=True).start()
# ====================================================

# ========== CONFIG MAQUINA 10K ==========
CONFIG = {
    "MAQUINA_1": 300,
    "MAQUINA_2": 300,
    "TRIPLE_BASE": 1200,
    "TRIPLE_R1": 1500,
    "TRIPLE_R2": 1800,
    "DOBLE": 900,
    "CAZADOR": 500,
    "TOPE_PERDIDA": -800,
    "META_GANANCIA": 600,
    "TZ": "America/Mexico_City"
}

MEMORIA_FILE = "memoria_jefe.json"
TOKEN = os.environ.get("BOT_TOKEN", "TU_TOKEN_AQUI")
# =========================================

def cargar_memoria():
    try:
        if os.path.exists(MEMORIA_FILE):
            with open(MEMORIA_FILE, "r") as f:
                return json.load(f)
    except: pass
    return {"ultimo": "GANO", "racha": 0, "lote": CONFIG["TRIPLE_BASE"], "ganancia_hoy": 0, "fecha": ""}

def guardar_memoria(resultado, ganancia):
    mem = cargar_memoria()
    hoy = datetime.now(pytz.timezone(CONFIG["TZ"])).strftime("%Y-%m-%d")
    
    if mem.get("fecha") != hoy:
        mem["ganancia_hoy"] = 0
        mem["fecha"] = hoy

    mem["ganancia_hoy"] += ganancia

    if resultado == "GANO":
        mem["racha"] = mem["racha"] + 1 if mem["ultimo"] == "GANO" else 1
        if mem["racha"] == 0: mem["lote"] = CONFIG["TRIPLE_BASE"]
        elif mem["racha"] == 1: mem["lote"] = CONFIG["TRIPLE_R1"]
        else: mem["lote"] = CONFIG["TRIPLE_R2"]
    else:
        mem["racha"] = -1
        mem["lote"] = 600

    mem["ultimo"] = resultado
    with open(MEMORIA_FILE, "w") as f:
        json.dump(mem, f)
    return mem

# --- AQUI VAN TUS FILTROS DEL BOT 2 ---
def filtro_ny():
    # tu logica NY
    return True

def filtro_noticias():
    return True

def filtro_spread():
    return True

def triple_candado():
    mem = cargar_memoria()
    # TU LOGICA REAL DE TRIPLE AQUI
    # Por ahora retorna TRIPLE si pasa filtros
    if filtro_ny() and filtro_noticias():
        return "TRIPLE", mem["lote"]
    return "NADA", 0

def jefe_cazador():
    mem = cargar_memoria()
    if mem["racha"] == -1:
        print("🧠 JEFE EN DESCANSO - Perdio ayer, no caza hoy")
        return None
    return CONFIG["CAZADOR"]

def main_bot():
    print("🔥 LA MAQUINA DE HACER DINERO V48.5 INICIADA - MODO 10K 🔥")
    print(f"✅ Flask corriendo en puerto {os.environ.get('PORT', 10000)}")
    
    while True:
        try:
            mem = cargar_memoria()
            ganancia_hoy = mem.get("ganancia_hoy", 0)
            hoy = datetime.now(pytz.timezone(CONFIG["TZ"])).strftime("%Y-%m-%d")
            
            if mem.get("fecha") != hoy:
                ganancia_hoy = 0

            if ganancia_hoy >= CONFIG["META_GANANCIA"]:
                print(f"💰 META CUMPLIDA: +${ganancia_hoy} - Durmiendo 6h")
                time.sleep(3600 * 6)
                continue

            if ganancia_hoy <= CONFIG["TOPE_PERDIDA"]:
                print(f"🛑 TOPE PERDIDA: ${ganancia_hoy} - Durmiendo 12h")
                time.sleep(3600 * 12)
                continue

            tipo, lote = triple_candado()
            
            if tipo != "NADA":
                print(f"🎯 SEÑAL {tipo} LOTE {lote} - {datetime.now()}")
                # AQUI TU LOGICA PARA ABRIR OPERACION
            else:
                lote_caz = jefe_cazador()
                if lote_caz:
                    print(f"🦁 JEFE CAZADOR ACTIVO LOTE {lote_caz}")

            time.sleep(60)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Esperar 3 seg a que Flask prenda el puerto
    time.sleep(3)
    main_bot()
