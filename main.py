# V105 MAQUINA DE HACER DINERO - REAL EFECTIVO
# BASE $10,000 - 7 BOLAS - ENTRADA -0.4% - SALIDA 0.5% REAL
# Nogales, Veracruz - Agosto 2026

import time
import requests
from datetime import datetime

# ================= CONFIGURACION V105 =================
CONFIG = {
    "BASE": 10000.0,
    "BOLAS": 7,
    "FEES_PCT": 0.35,          # REAL: 0.20% taker + 0.15% spread/slippage
    "MIN_RETAIL_PCT": 0.5,     # Minimo 0.5% bruta para vender
    "TRAIL_PCT": 0.2,          # Trail para dejar correr hasta 1%+
    "STOP_PCT": -7.0,          # Stop loss por bola
    "FONDO_ENTRADA_PCT": -0.4, # CAZA EN -0.4% - NO CAMBIA
    "REBOTE_ENTRADA_PCT": 0.05,# Entra cuando rebota 0.05%
    "MONEDAS": ["SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB", "BONK"],
    "BOLA_NIEVE": True,        # ON
    "AUTO": True,
    "TELEGRAM_TOKEN": "TU_TOKEN_AQUI",
    "TELEGRAM_CHAT_ID": "TU_CHAT_ID"
}

# Estado global
ACUMULADO = 310.0  # Lo que ya llevas
BALANCE = CONFIG["BASE"] + ACUMULADO
COSTO_BOLA_BASE = CONFIG["BASE"] / CONFIG["BOLAS"]

bolas_activas = []  # [{'moneda': 'SOL', 'precio_compra': 180.5, 'costo': 1472.86, 'max_profit': 0}]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/sendMessage"
        requests.post(url, data={"chat_id": CONFIG["TELEGRAM_CHAT_ID"], "text": msg, "parse_mode": "Markdown"})
    except:
        pass
    print(msg)

def get_precio_actual(moneda):
    # AQUI VA TU CONEXION A COINBASE / BITSO API
    # Por ahora simulado - tu ya tienes esta funcion
    # return api.get_price(f"{moneda}-USD")
    return 0

def calcular_costo_bola_actual():
    if CONFIG["BOLA_NIEVE"] and ACUMULADO > 0:
        # Bola de nieve: reinvierte ganancias
        return (CONFIG["BASE"] + ACUMULADO) / CONFIG["BOLAS"]
    return COSTO_BOLA_BASE

def cazar_entrada():
    global bolas_activas, ACUMULADO, BALANCE
    if len(bolas_activas) >= CONFIG["BOLAS"]:
        return

    costo_actual = calcular_costo_bola_actual()
    
    for moneda in CONFIG["MONEDAS"]:
        # Lógica: detecta caida -0.4% y rebote 0.05%
        # Tu bot ya tiene el detector de fondo, aquí solo se respeta
        precio = get_precio_actual(moneda)
        caida = -0.45 # Ejemplo: viene de tu detector
        
        if caida <= CONFIG["FONDO_ENTRADA_PCT"]:
            # Rebote detectado
            rebote = 0.06
            if rebote >= CONFIG["REBOTE_ENTRADA_PCT"]:
                bola = {
                    "moneda": moneda,
                    "precio_compra": precio,
                    "costo": costo_actual,
                    "max_profit_pct": 0,
                    "entrada_time": datetime.now()
                }
                bolas_activas.append(bola)
                print(f"🎯 CAZADA {moneda} en ${precio} | Costo bola: ${costo_actual:.2f}")

def revisar_salidas():
    global bolas_activas, ACUMULADO, BALANCE
    
    for bola in bolas_activas[:]:
        precio_actual = get_precio_actual(bola["moneda"])
        precio_compra = bola["precio_compra"]
        
        profit_bruta_pct = ((precio_actual - precio_compra) / precio_compra) * 100
        
        # Actualiza max profit para trail
        if profit_bruta_pct > bola["max_profit_pct"]:
            bola["max_profit_pct"] = profit_bruta_pct
        
        # Logica de venta V105 REAL
        # 1. Debe superar 0.5% bruta minimo
        # 2. Si esta en trail, solo vende si cae 0.2% desde el maximo
        
        if profit_bruta_pct >= CONFIG["MIN_RETAIL_PCT"]:
            # Checa trail
            caida_desde_max = bola["max_profit_pct"] - profit_bruta_pct
            
            debe_vender = False
            if bola["max_profit_pct"] <= 0.7:
                # Si apenas llego a 0.5%, vende directo
                debe_vender = True
            else:
                # Si ya se fue a 0.8%+, deja trail de 0.2%
                if caida_desde_max >= CONFIG["TRAIL_PCT"]:
                    debe_vender = True
            
            if debe_vender:
                bruta_usd = bola["costo"] * (profit_bruta_pct / 100)
                comision_usd = bola["costo"] * (CONFIG["FEES_PCT"] / 100)
                neto_usd = bruta_usd - comision_usd
                neto_pct = profit_bruta_pct - CONFIG["FEES_PCT"]
                
                # Solo vende si neto REAL > 0.10%
                if neto_pct >= 0.10:
                    ACUMULADO += neto_usd
                    BALANCE = CONFIG["BASE"] + ACUMULADO
                    
                    # Mensaje V105 REAL
                    msg = f"✅ GANADA LIMPIA REAL {bola['moneda']} +${neto_usd:.2f} Neto ({profit_bruta_pct:.2f}% bruta - {CONFIG['FEES_PCT']}% fees = +{neto_pct:.2f}% neto) | BALANCE ${BALANCE:.2f}"
                    send_telegram(msg)
                    
                    bolas_activas.remove(bola)
        
        # Stop loss -7%
        if profit_bruta_pct <= CONFIG["STOP_PCT"]:
            perdida = bola["costo"] * (profit_bruta_pct / 100)
            ACUMULADO += perdida
            BALANCE = CONFIG["BASE"] + ACUMULADO
            send_telegram(f"🛑 STOP {bola['moneda']} {profit_bruta_pct:.2f}% | BALANCE ${BALANCE:.2f}")
            bolas_activas.remove(bola)

def mostrar_circulo():
    # Aqui va tu UI del circulo limpio
    dia = datetime.now().day
    progreso = (dia / 31) * 100
    costo_bola = calcular_costo_bola_actual()
    
    print(f"""
    ========= V105 REAL EFECTIVO =========
    [  CIRCULO LIMPIO  ]
    BASE ${CONFIG['BASE']:.0f}
    ACUMULADO +${ACUMULADO:.2f}
    {progreso:.0f}% MES - Día {dia}/31
    
    --- DESGLOSE FUERA DEL CIRCULO ---
    Bruta: +$315.00 (ejemplo)
    Comisiones: -${(BALANCE*0.0035):.2f} (0.35% REAL)
    Neto REAL: +${ACUMULADO:.2f}
    BALANCE: ${BALANCE:.2f}
    Costo/bola: ${costo_bola:.2f}
    
    CONFIG: MAX {CONFIG['BOLAS']} | MINORISTA {CONFIG['MIN_RETAIL_PCT']}% REAL | STOP {CONFIG['STOP_PCT']}% | TRAIL {CONFIG['TRAIL_PCT']}%
    ENTRADA: {CONFIG['FONDO_ENTRADA_PCT']}% fondo + {CONFIG['REBOTE_ENTRADA_PCT']}% rebote
    BOLA NIEVE: {'EN' if CONFIG['BOLA_NIEVE'] else 'OFF'} | AUTO: {'ON' if CONFIG['AUTO'] else 'OFF'}
    BOLAS ACTIVAS: {len(bolas_activas)}/{CONFIG['BOLAS']} CAZANDO

    """)

# ================= LOOP PRINCIPAL =================
if __name__ == "__main__":
    send_telegram(f"🚀 V105 REAL EFECTIVO INICIADO - CAZANDO EN {CONFIG['FONDO_ENTRADA_PCT']}% | MIN {CONFIG['MIN_RETAIL_PCT']}% REAL | BALANCE ${BALANCE:.2f}")
    
    while True:
        try:
            cazar_entrada()
            revisar_salidas()
            mostrar_circulo()
            time.sleep(3) # Revisa cada 3 seg
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
