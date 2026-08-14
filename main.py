# ==========================================
# LA MAQUINA DE HACER DINERO V48.5 - MODO 10K SEGURO
# 3 VATOS - JEFE CON MEMORIA
# ==========================================
import time, json, os
from datetime import datetime
import pytz

CONFIG = {
    "MAQUINA_1": 300,
    "MAQUINA_2": 300,
    "TRIPLE_BASE": 1200,
    "TRIPLE_R1": 1500,
    "TRIPLE_R2": 1800,
    "DOBLE": 900,
    "CAZADOR": 500,
    "TOPE_PERDIDA": -800,
    "META_GANANCIA": 600
}

MEMORIA_FILE = "memoria_jefe.json"

def cargar_memoria():
    try:
        with open(MEMORIA_FILE, "r") as f: return json.load(f)
    except: return {"ultimo": "GANO", "racha": 0, "lote": CONFIG["TRIPLE_BASE"]}

def guardar_memoria(resultado):
    mem = cargar_memoria()
    if resultado == "GANO":
        mem["racha"] = mem["racha"] + 1 if mem["ultimo"] == "GANO" else 1
        mem["lote"] = CONFIG["TRIPLE_BASE"] if mem["racha"]==0 else CONFIG["TRIPLE_R1"] if mem["racha"]==1 else CONFIG["TRIPLE_R2"]
    else:
        mem["racha"] = -1
        mem["lote"] = 600
    mem["ultimo"] = resultado
    with open(MEMORIA_FILE, "w") as f: json.dump(mem, f)

# --- TUS 8 FUNCIONES DEL BOT 2 VAN AQUÍ (NO LAS TOCO) ---
# filtro_ny(), filtro_noticias(), filtro_spread(), etc...

def triple_candado():
    # Aqui va tu logica triple/doble
    memoria = cargar_memoria()
    return "TRIPLE", memoria["lote"] # Ejemplo

def jefe_cazador():
    memoria = cargar_memoria()
    if memoria["racha"] == -1: return None # Si perdio, no caza hoy
    # logica cazador 75% fuerza
    return CONFIG["CAZADOR"]

def main():
    ganancia_hoy = 0
    print("🔥 LA MAQUINA DE HACER DINERO V48.5 INICIADA - MODO 10K 🔥")
    while True:
        if ganancia_hoy >= CONFIG["META_GANANCIA"]:
            print(f"💰 META DEL DIA CUMPLIDA: +${ganancia_hoy} - APAGANDO")
            time.sleep(3600*6) # Duerme 6 horas
            continue
        if ganancia_hoy <= CONFIG["TOPE_PERDIDA"]:
            print(f"🛑 TOPE PERDIDA: {ganancia_hoy} - APAGANDO")
            time.sleep(3600*12)
            continue
        
        # LOGICA DE 3 VATOS
        tipo, lote = triple_candado()
        if tipo != "NADA":
            # Abrir operacion
            pass
        else:
            lote_caz = jefe_cazador()
            if lote_caz: pass

        time.sleep(60)

if __name__ == "__main__":
    main()
