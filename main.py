import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V134 FIX SYNTAX", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {
    "BASE_USD": 500.0,
    "BASE_MXN": 9750.0,
    "ACUMULADO_MXN": 310.0,
    "ACUMULADO_USD": 15.90,
    "FEE_ENTRY_PCT": 0.10,
    "FEE_EXIT_PCT": 0.10,
    "TP_PCT": 0.30,
    "AUTO": True,
    "BOLAS_MAX": 6,
    "RATE_MXN": 19.50
}
MONEDAS = {"ADA":True,"AVAX":True,"BNB":True,"BTC":False,"DOGE":True,"ETH":True,"SOL":True,"XRP":True}
bolas = []
historial = []
PRECIOS = {}

def send_tg(text):
    global CHAT_ID
    if not TOKEN or not CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":text}, timeout=5)
    except:
        pass

def get_rate_mxn():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN", timeout=4)
        p = float(r.json()['price'])
        if 10 < p < 30:
            CONFIG["RATE_MXN"]=p
            CONFIG["BASE_MXN"]=CONFIG["BASE_USD"]*p
            return p
    except:
        pass
    return CONFIG["RATE_MXN"]

def get_precio(moneda):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={moneda}USDT", timeout=4)
        p = float(r.json()['price'])
        PRECIOS[moneda]=p
        return p
    except:
        return PRECIOS.get(moneda, 0)

def get_total_mxn():
    return CONFIG["BASE_MXN"] + CONFIG["ACUMULADO_MXN"]

def get_costo_mxn():
    return get_total_mxn() / CONFIG["BOLAS_MAX"]

def get_costo_usd():
    return get_costo_mxn() / CONFIG["RATE_MXN"]

def calc_desglose(entrada, salida, costo_usd, rate):
    if not entrada or salida==0:
        return {}
    pct_bruto = ((salida - entrada) / entrada) * 100
    bruta_usd = costo_usd * (pct_bruto/100)
    com_entry_usd = costo_usd * (CONFIG["FEE_ENTRY_PCT"]/100)
    com_exit_usd = (costo_usd + bruta_usd) * (CONFIG["FEE_EXIT_PCT"]/100)
    com_total_usd = com_entry_usd + com_exit_usd
    neta_usd = bruta_usd - com_total_usd
    pct_neto = (neta_usd / costo_usd) * 100
    return {
        "pct_bruto": pct_bruto,
        "pct_neto": pct_neto,
        "bruta_usd": bruta_usd,
        "bruta_mxn": bruta_usd * rate,
        "com_entry_usd": com_entry_usd,
        "com_entry_mxn": com_entry_usd * rate,
        "com_exit_usd": com_exit_usd,
        "com_exit_mxn": com_exit_usd * rate,
        "com_total_usd": com_total_usd,
        "com_total_mxn": com_total_usd * rate,
        "neta_usd": neta_usd,
        "neta_mxn": neta_usd * rate
    }

def get_stats():
    rate = get_rate_mxn()
    CONFIG["ACUMULADO_MXN"] = CONFIG["ACUMULADO_USD"] * rate
    CONFIG["BASE_MXN"] = CONFIG["BASE_USD"] * rate
    flot_usd=0
    flot_mxn=0
    vend=0
    for b in bolas:
        p=get_precio(b["moneda"])
        if p>0:
            b["actual"]=p
        d = calc_desglose(b["compra"], b["actual"], b["costo_usd"], rate)
        b.update(d)
        b["usd"]=d.get("neta_usd",0)
        b["mxn"]=d.get("neta_mxn",0)
        b["neto"]=d.get("pct_neto",0)
        flot_usd+=b["usd"]
        flot_mxn+=b["mxn"]
        if b["neto"]>=CONFIG["TP_PCT"]:
            vend+=1
    total_mxn=get_total_mxn()
    total_usd=total_mxn/rate
    prog=(datetime.now().day/30)*100
    return total_usd,total_mxn,flot_usd,flot_mxn,prog,vend,rate,get_costo_usd(),get_costo_mxn()

def comprar_bola(moneda):
    if len(bolas)>=CONFIG["BOLAS_MAX"]:
        return None
    for x in bolas:
        if x["moneda"]==moneda:
            return None
    p=get_precio(moneda)
    if p==0:
        return None
    n={"id":int(time.time()*1000),"moneda":moneda,"compra":p,"costo_usd":get_costo_usd(),"costo_mxn":get_costo_mxn(),"actual":p}
    bolas.append(n)
    return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if b["id"]==id_bola:
            CONFIG["ACUMULADO_USD"]+=b["neta_usd"]
            CONFIG["ACUMULADO_MXN"]+=b["neta_mxn"]
            h={"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"costo_mxn":round(b["costo_mxn"],2),"costo_usd":round(b["costo_usd"],2),"com_entry_mxn":round(b["com_entry_mxn"],2),"com_entry_usd":round(b["com_entry_usd"],4),"com_exit_mxn":round(b["com_exit_mxn"],2),"com_exit_usd":round(b["com_exit_usd"],4),"com_total_mxn":round(b["com_total_mxn"],2),"com_total_usd":round(b["com_total_usd"],4),"bruta_mxn":round(b["bruta_mxn"],2),"bruta_usd":round(b["bruta_usd"],4),"neta_mxn":round(b["neta_mxn"],2),"neta_usd":round(b["neta_usd"],4),"pct_bruto":round(b["pct_bruto"],3),"pct_neto":round(b["pct_neto"],3)}
            historial.insert(0,h)
            bolas.remove(b)
            if b["neta_usd"]>0:
                send_tg(f"CIERRE GANADOR\n{b['moneda']} NETO {b['pct_neto']:.2f}% (BRUTO {b['pct_bruto']:.2f}%)\nNETA: ${b['neta_mxn']:.2f} MXN (${b['neta_usd']:.2f} USD)\nBRUTA: ${b['bruta_mxn']:.2f} MXN\nCOMIS: ${b['com_total_mxn']:.2f} MXN")
            return b
    return None

def tabla_por_moneda():
    stats=defaultdict(lambda: {"entradas":0,"ganadas":0,"total_usd":0.0,"total_mxn":0.0,"com_mxn":0.0,"bruta_mxn":0.0})
    for h in historial:
        m=h["moneda"]
        stats[m]["entradas"]+=1
        if h["neta_mxn"]>0:
            stats[m]["ganadas"]+=1
        stats[m]["total_usd"]+=h["neta_usd"]
        stats[m]["total_mxn"]+=h["neta_mxn"]
        stats[m]["com_mxn"]+=h["com_total_mxn"]
        stats[m]["bruta_mxn"]+=h["bruta_mxn"]
    for b in bolas:
        stats[b["moneda"]]["entradas"]+=1
    return stats

def loop_auto():
    while True:
        try:
            if CONFIG["AUTO"]:
                get_stats()
                for b in bolas[:]:
                    if b.get("pct_neto",0)>=CONFIG["TP_PCT"]:
                        vender_bola(b["id"])
                if len(bolas)<CONFIG["BOLAS_MAX"]:
                    disponibles=[]
                    for m, on in MONEDAS.items():
                        if not on:
                            continue
                        ocupado=False
                        for x in bolas:
                            if x["moneda"]==m:
                                ocupado=True
                                break
                        if not ocupado:
                            disponibles.append(m)
                    if len(disponibles)>0:
                        elegir=random.choice(disponibles)
                        comprar_bola(elegir)
        except Exception as e:
            print(traceback.format_exc(), flush=True)
        time.sleep(12)

threading.Thread(target=loop_auto, daemon=True).start()
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>MAQUINA DE HACER DIN
