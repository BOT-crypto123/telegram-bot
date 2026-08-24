import os, json, time, threading, requests, random
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"
FEE = 0.001
POSIBLES_RUTAS = ["/data/bot_data.json", "bot_data.json", "bot_data_binance.json"]

default_data = {
 "capital_actual": 500.0, "capital_inicial": 500.0,
 "capital_binance": 500.0, "capital_mt5": 500.0,
 "usd_mxn": 18.5,
 "gan_acum_total": 0.0, "gan_mes": 0.0, "pct_mes": 0.0,
 "ganadas": 0, "salidas": 0, "tp": 0.3, "sl_pct": -1.5,
 "rsi_compra": 35, "rsi_venta": 70, "filtro_ema": "OFF",
 "max_entradas": 8, "auto": True, "auto_tune": True,
 "modo": "AMBOS", "pos": [], "pos_short": [],
 "historial": [], "coins"
 @app.route("/api/state")
def api_state():
    usd_live = get_usd_mxn_live()
    max_ent = data.get("max_entradas",8)
    bola_base = data.get("capital_binance",500.0)/max(1,max_ent)
    prices = get_prices_data()
    for p in data.get("pos",[]):
        pr=prices.get(p["sym"],{}).get("price",p["entry"])
        p["ahora"]=pr
        p["gan_neta_pct"]=(pr-p["entry"])/p["entry"]*100 - (FEE*2*100)
        p["tipo"]="LONG"
    for p in data.get("pos_short",[]):
        pr=prices.get(p["sym"],{}).get("price",p["entry"])
        p["ahora"]=pr
        p["gan_neta_pct"]=(p["entry"]-pr)/p["entry"]*100 - (FEE*2*100)
        p["tipo"]="SHORT"
    bloqueado=sum([x.get("monto", bola_base) for x in data.get("pos",[])]) + sum([x.get("monto", bola_base) for x in data.get("pos_short",[])])
    gan_total=data.get("gan_acum_total",0.0)
    capital_bin=data.get("capital_binance",500.0)
    if bloqueado==0:
        disponible=capital_bin
        total_real=capital_bin + gan_total
    else:
        disponible=capital_bin - bloqueado
        total_real=disponible + bloqueado + gan_total
    bola_real=total_real/max(1,max_ent)
    winrate=(data.get("ganadas",0)/data.get("salidas",1)*100) if data.get("salidas",0)>0 else 0
    return jsonify({
        "capital_binance": capital_bin,
        "capital": total_real,
        "total_real_usd": total_real,
        "bola": bola_real,
        "bola_binance": bola_base,
        "bola_mxn": bola_real*usd_live,
        "gan_acum": gan_total,
        "usd_mxn": round(usd_live,4),
        "disponible_usd": disponible,
        "bloqueado_usd": bloqueado,
        "pos": data.get("pos",[])+data.get("pos_short",[]),
        "pos_long": data.get("pos",[]),
        "pos_short": data.get("pos_short",[]),
        "historial": data.get("historial",[])[-50:],
        "max_entradas": max_ent,
        "auto": data.get("auto",True),
        "coins_activas": data.get("coins_activas",{})
    })

@app.route("/api/config", methods=["POST"])
def api_config():
    j=request.json
    if "toggle_coin" in j:
        data["coins_activas"][j["toggle_coin"]]=not data["coins_activas"].get(j["toggle_coin"],True)
    if "max" in j:
        data["max_entradas"]=int(j["max"])
    save()
    return jsonify(ok=True)

@app.route("/api/toggle", methods=["POST"])
def toggle():
    data["auto"]=not data["auto"]
    save()
    return jsonify(ok=True)

def auto_loop():
    last_tune=0
    last_usd=0
    while True:
        try:
            if time.time()-last_usd>60:
                get_usd_mxn_live(force=True)
                last_usd=time.time()
            if data["auto"]:
                prices=get_prices_data()
                if time.time()-last_tune>900:
                    auto_tune_logic(prices)
                    last_tune=time.time()
                total_max=data["max_entradas"]
                max_long=(total_max+1)//2
                if len(data["pos"]) < max_long:
                    for sym,info in prices.items():
                        if info["price"]>0 and info["ok"] and data["coins_activas"].get(sym,True) and not any(x["sym"]==sym for x in data["pos"]):
                            monto=data["capital_binance"]/total_max
                            data["pos"].append({"sym":sym,"entry":info["price"],"monto":monto})
                            save()
                            break
        except Exception as e:
            print("AUTO ERROR",e)
        time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
