import os, sys, requests, threading, time
from flask import Flask, request
from datetime import datetime

os.environ['PYTHONUNBUFFERED']='1'
sys.stdout.reconfigure(line_buffering=True)

print("INICIANDO V108 FINAL TODO COMPLETO", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

# ====== TU CONFIG REAL ======
CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "BOLAS_MAX": 10,
    "COSTO_BOLA": 1031.63,
    "FEES_PCT": 0.50,  # TU COMISION REAL 0.5% TOTAL
    "TP_PCT": 0.50,    # Solo vende si neto >= 0.5%
    "SL_PCT": -3.0,
    "AUTO": False
}

# TUS BOLAS - EDITA AQUI TUS COMPRAS REALES
bolas = [
    {"moneda":"XRP","compra":22.24,"costo":1031.63,"cantidad":46.38,"fecha":"2025-01-10"},
    {"moneda":"ETH","compra":40049.34,"costo":1031.63,"cantidad":0.0257,"fecha":"2025-01-11"},
]

# PRECIOS - AQUI VA TU API REAL DE BITSO
# Si quieres precios reales, cambia esta funcion por tu llamada a Bitso
PRECIOS_CACHE = {"BTC":1273222,"ETH":39926,"SOL":1531,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33,"BNB":9870,"LTC":1450}

def get_precio_bitso(moneda):
    try:
        # Descomenta esto cuando quieras precios reales de Bitso
        # r = requests.get(f"https://api.bitso.com/v3/ticker?book={moneda.lower()}_mxn", timeout=5).json()
        # return float(r['payload']['last'])
        return PRECIOS_CACHE.get(moneda, 0)
    except:
        return PRECIOS_CACHE.get(moneda, 0)

def calc_ganancia(entrada, actual, costo):
    if not entrada or not actual or entrada < 0.001:
        return 0, 0, 0
    bruto = ((actual - entrada) / entrada) * 100
    neto = bruto - CONFIG["FEES_PCT"]  # AQUI TU 0.5% REAL
    usd = costo * (neto / 100)
    return bruto, neto, usd

def dashboard_text():
    total_flotante = 0
    ganadoras = 0
    msg = f"🤖 MAQUINA V108 FINAL\n"
    msg += f"💰 BAL: ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f}\n"
    msg += f"📈 ACUM: +${CONFIG['ACUMULADO']:.2f} BASE: ${CONFIG['BASE']:.2f}\n"
    msg += f"🎯 AUTO: {'🟢 ON' if CONFIG['AUTO'] else '🔴 OFF'} | FEES: {CONFIG['FEES_PCT']}%\n"
    msg += f"⚙️ TP: >={CONFIG['TP_PCT']}% NETO | SL: {CONFIG['SL_PCT']}%\n"
    msg += f"━━━━━━━━━━━━━━\n\n"
    
    for i, b in enumerate(bolas, 1):
        actual = get_precio_bitso(b['moneda'])
        bruto, neto, usd = calc_ganancia(b['compra'], actual, b['costo'])
        total_flotante += usd
        if neto >= CONFIG["TP_PCT"]:
            ganadoras += 1
        
        if neto >= CONFIG["TP_PCT"]:
            estado = "🟢 VENDIBLE"
        elif neto >= 0:
            estado = "🟡 EN VERDE pero no llega a 0.5% neto"
        else:
            estado = "🔴 ROJO"
            
        msg += f"{estado} BOLA {i} {b['moneda']}\n"
        msg += f"   Compra: {b['compra']} -> Ahora: {actual}\n"
        msg += f"   Bruto: {bruto:.2f}% | NETO REAL: {neto:.2f}%\n"
        msg += f"   Ganancia: ${usd:.2f} (costo ${b['costo']})\n\n"
    
    msg += f"━━━━━━━━━━━━━━\n"
    msg += f"💵 FLOTANTE TOTAL: ${total_flotante:.2f}\n"
    msg += f"✅ VENDIBLES (>=
