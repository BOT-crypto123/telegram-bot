import os, json, time, threading, requests
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__)
DATA_FILE="bot_data.json"
FEE=0.001
default_data={"capital_binance":500.0,"capital_mt5":500.0,"usd_mxn":18.5,"gan_acum_total":0.0,"ganadas":0,"salidas":0,"max_entradas":8,"auto":True,"pos":[],"pos_short":[],"historial":[],"coins_activas":{"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"ADA":True,"AVAX":True,"DOGE":True},"alert_users":[]}

try:
    data=json.load(open("/data/bot_data.json")) if os.path.exists("/data/bot_data.json") else json.load(open("bot_data.json"))
    for k,v in default_data.items():
        if k not in data: data[k]=v
except: data=default_data.copy()

def save():
    try:
        with open(DATA_FILE,"w") as f: json.dump(data,f)
        with open("/data/bot_data.json","w") as f: json.dump(data,f)
    except: pass

def get_usd_mxn_live():
    try:
        r=requests.get("https://open.er-api.com/v6/latest/USD",timeout=5).json()
        return float(r["rates"]["MXN"])
    except: return data.get("usd_mxn",18.5)

def get_prices_data():
    out={}
    for sym in ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","ADA/USDT","AVAX/USDT","DOGE/USDT"]:
        coin=sym.replace("/USDT","")
        try:
            r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={sym.replace('/','')}&interval=1h&limit=50",timeout=5).json()
            closes=[float(k[4]) for k in r]
            out[coin]={"price":closes[-1],"rsi":35,"ema":closes[-1],"ok":True,"ok_short":False}
        except: out[coin]={"price":0,"rsi":50,"ema":0,"ok":False,"ok_short":False}
    return out

@app.route("/")
def home(): return "BOT LIVE - /dashboard OK",200

@app.route("/dashboard")
def dashboard():
    if os.path.exists("dashboard.html"): return send_from_directory(".","dashboard.html")
    return "dashboard no existe",404

@app.route("/api/prices")
def api_prices(): return jsonify(get_prices_data())

@app.route("/api/state")
def api_state():
    usd=get_usd_mxn_live()
    bola_base=data["capital_binance"]/data["max_entradas"]
    prices=get_prices_data()
    for p in data["pos"]:
        pr=prices.get(p["sym"],{}).get("price",p["entry"])
        p["ahora"]=pr
        p["gan_neta_pct"]=(pr-p["entry"])/p["entry"]*100
    bloqueado=sum([x.get("monto",bola_base) for x in data["pos"]])
    gan=data.get("gan_acum_total",0.0)
    cap_bin=data["capital_binance"]
    disponible=cap_bin-bloqueado if bloqueado>0 else cap_bin
    total_real=disponible+bloqueado+gan if bloqueado>0 else cap_bin+gan
    bola_real=total_real/data["max_entradas"]
    return jsonify({"capital_binance":cap_bin,"capital":total_real,"total_real_usd":total_real,"bola":bola_real,"bola_mxn":bola_real*usd,"usd_mxn":usd,"gan_acum":gan,"disponible_usd":disponible,"bloqueado_usd":bloqueado,"pos":data["pos"],"historial":data["historial"][-20:]})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
