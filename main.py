import os, time, threading, requests
from flask import Flask, request
from datetime import datetime

print("INICIANDO MAQUINA V105.7 DEFINITIVA...")

CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "BOLAS_MAX": 10,
    "COSTO_BOLA": 1031.63,
    "FEES_PCT": 0.35,
    "MIN_RETAIL_PCT": 0.3,
    "STOP_PCT": -7.0,
    "TRAIL_PCT": 0.2,
    "MONEDAS": ["BTC","ETH","SOL","DOGE","XRP","ADA","AVAX"],
}

bolas = [
    {"moneda": "XRP", "compra": 22.24, "costo": 1031.63},
    {"moneda": "ETH", "compra": 40049.34, "costo": 1031.63},
]

TOKEN = os.environ.get("TELEGRAM_TOKEN")
print(f"TOKEN existe? {'SI' if TOKEN else 'NO - PONLO EN RENDER ENVIRONMENT'}")

def valido(p): return p and p != 0 and p > 0.001
def calc(entra, actual, costo):
    if not valido(entra) or not valido(actual): return 0,0,0
    try:
        bruto = ((actual-entra)/entra)*100
        neto = bruto - CONFIG["FEES_PCT"]
        usd = costo*(neto/100)
        return bruto,neto,usd
    except: return 0,0,0

def precio(m):
    d={"BTC":1273222.19,"ETH":39926.52,"SOL":1531.61,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33}
    return d.get(m,0)

def responder_dashboard(cid):
    tot=0
    msg=f"💰 *MAQUINA V105.7*\nBAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f} ACUM +${CONFIG['ACUMULADO']}\n\n"
    for b in bolas:
        a=precio(b['moneda'])
        _,n,us=calc(b['compra'],a,b['costo'])
        tot+=us
        msg+=f"{'🟢' if n>=0 else '🔴'} {b['moneda']} E {b['compra']} -> {a} ({n:.2f}%) ${us:.2f} FLOTANTE\n"
    msg+=f"\n*TOTAL FLOTANTE: ${tot:.2f}*\nhttps://telegram-bot-ci
