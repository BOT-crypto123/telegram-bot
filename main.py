import os, sys, requests, threading, time, random
from flask import Flask, request, jsonify
from datetime import datetime

os.environ['PYTHONUNBUFFERED']='1'
sys.stdout.reconfigure(line_buffering=True)
print("INICIANDO V115 FIX BINANCE", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "FEES_PCT": 0.10,
    "TP_PCT": 0.30,
    "AUTO": True,
    "BOLAS_MAX": 8,
    "COSTO_BOLA": 1031.63,
    "EXCHANGE": "BINANCE"
}

MONEDAS = {"BTC": True, "ETH": True, "XRP": True, "SOL": True, "DOGE": True, "ADA": True, "AVAX": True, "BNB": True}

bolas = [
    {"id":1,"moneda":"XRP","compra":2.85,"costo":1031.63,"actual":2.85,"neto":0,"usd":0},
    {"id":2,"moneda":"ETH","compra":2450.5,"costo":1031.63,"actual":2450.5,"neto":0,"usd":0},
]

historial = []
PRECIOS = {}

def get_precio_binance(moneda):
    try:
        symbol = moneda + "USDT"
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + symbol, timeout=5)
        data = r.json()
        price = float(data['price'])
        PRECIOS[moneda] = price
        return price
    except:
        return PRECIOS.get(moneda, 0)

def calc(e,a,c):
    if not e or a==0:
        return 0,0,0
    bruto = ((a-e)/e)*100
    neto = bruto - CONFIG["FEES_PCT"]
    usd = c * (neto/100)
    return bruto, neto, usd

def get_stats():
    flot=0
    vend=0
    for b in bolas:
        actual = get_precio_binance(b["moneda"])
        if actual!= 0:
            b["actual"] = actual
        _, neto, usd = calc(b["compra"], b["actual"], b["costo"])
        b["neto"]=neto
        b["usd"]=usd
        flot+=usd
        if neto>=CONFIG["TP_PCT"]:
            vend+=1
    bal = CONFIG["BASE"] + CONFIG["ACUMULADO"]
    total = bal + flot
    prog = (datetime.now().day / 30)*100
    return bal, flot, total, prog, vend

def comprar_bola(moneda):
    if len(bolas) >= CONFIG["BOLAS_MAX"]:
        return None
    for x in bolas:
        if x["moneda"]==moneda:
            return None
    p = get_precio_binance(moneda)
    if p==0:
        return None
    n = {"id":int(time.time()),"moneda":moneda,"compra":p,"costo":CONFIG["COSTO_BOLA"],"actual":p,"neto":0,"usd":0}
    bolas.append(n)
    return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if b["id"]==id_bola:
            CONFIG["ACUMULADO"]+=b["usd"]
            historial.insert(0,{"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"neto":round(b["neto"],2),"usd":round(b["usd"],2),"estado":"CERRADA"})
            bolas.remove(b)
            return b
    return None

def enviar(cid, txt, botones=True):
    try:
        data={"chat_id":cid,"text":txt}
        if botones:
            data["reply_markup"]={"keyboard":[["DASHBOARD","BALANCE"],["AUTO ON","AUTO OFF"],["TP 0.3","TP 0.6"],["COMPRAR","WEB"]],"resize_keyboard":True,"is_persistent":True}
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage", json=data, timeout=10)
    except Exception as e:
        print(str(e), flush=True)

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>V115 FIX</title>
<style>
body{background:#0a0e1a;color:#fff;font-family:Arial;padding:12px}
.card{background:#121a2b;border-radius:14px;padding:12px;margin:10px 0;border:1px solid #f3ba2f}
.btn{padding:10px 14px;border-radius:10px;border:none;margin:4px;font-weight:bold;cursor:pointer}
.on{background:#f3ba2f;color:#000}.off{background:#1e2a44;color:#888}.tp{background:#00ff88;color:#000;border:2px solid #00ff88}
.input-tp{background:#000;color:#00ff88;border:2px solid #f3ba2f;border-radius:10px;padding:10px;width:90px;font-size:18px;font-weight:bold;text-align:center}
.rojo{border-color:#ff3040}.verde{border-color:#00ff88}
.circle-wrap{position:relative;width:220px;height:220px;margin:15px auto}
.bg{fill:none;stroke:#1a2332;stroke-width:12}
.prog{fill:none;stroke:#f3ba2f;stroke-width:12;stroke-linecap:round
