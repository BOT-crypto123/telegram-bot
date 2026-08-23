import os, json, time, threading, requests
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"
FEE = 0.001
POSIBLES_RUTAS = ["/data/bot_data.json", "bot_data.json"]

default_data = {
 "capital_actual": 500.0, "capital_inicial": 500.0, "usd_mxn": 18.5,
 "gan_acum_total": 0.0, "gan_acum_mxn": 0.0, "gan_mes": 0.0, "pct_mes": 0.0,
 "ganadas": 0, "salidas": 0, "tp": 0.3, "sl_pct": -1.5, "rsi_compra": 35, "rsi_venta": 70,
 "filtro_ema": "OFF", "max_entradas": 8, "auto": True, "auto_tune": True,
 "modo": "AMBOS",
 "pos": [], "pos_short": [], "historial": [], "capital_history": [],
 "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"ADA":True,"AVAX":True,"DOGE":True},
 "rsi_por_moneda": {}, "alert_users": []
}
try:
    loaded=False
    for p in POSIBLES_RUTAS:
        if os.path.exists(p):
            with open(p) as f: data=json.load(f)
            loaded=True; break
    if not loaded: raise FileNotFoundError
    for k,v in default_data.items():
        if k not in data: data[k]=v
except: data=default_data.copy()

def save():
    for p in POSIBLES_RUTAS:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            with open(p,"w") as f: json.dump(data,f)
        except: pass
    try:
        with open(DATA_FILE,"w") as f: json.dump(data,f)
    except: pass

def tg(chat_id, text):
    if not BOT_TOKEN: return
    try:
        base = os.getenv("RENDER_EXTERNAL_URL","https://telegram-bot-cijp.onrender.com")
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "reply_markup": {"inline_keyboard": [[{"text":"VER DASHBOARD","url":f"{base}/dashboard"}]]}}, timeout=10)
    except: pass

def keep_alive_render():
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL") or "https://telegram-bot-cijp.onrender.com/"
            requests.get(url, timeout=10)
        except: pass
        time.sleep(600)
threading.Thread(target=keep_alive_render, daemon=True).start()

def get_usd_mxn_live():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10).json()
        mxn = float(r["rates"]["MXN"])
        if 10 < mxn < 30: return mxn
    except: pass
    return data.get("usd_mxn", 18.5)

SYMS = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","ADA/USDT","AVAX/USDT","DOGE/USDT"]

def get_rsi(prices, p=14):
    if len(prices)<p+1: return 50
    gains=losses=0
    for i in range(1,p+1):
        d=prices[-i]-prices[-i-1]
        if d>=0: gains+=d
        else: losses+=-d
    if losses==0: return 100
    rs=gains/losses
    return 100 - (100/(1+rs))

def get_prices_data():
    out={}
    for sym in SYMS:
        coin=sym.replace("/USDT",""); bin_sym=sym.replace("/","")
        try:
            r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={bin_sym}&interval=1h&limit=100", timeout=10).json()
            closes=[float(k[4]) for k in r]; price=closes[-1]; rsi=get_rsi(closes); ema=sum(closes[-20:])/20
            p_ema_ok=price>ema if data["filtro_ema"]=="ON" else True
            limite=data["rsi_por_moneda"].get(coin, data["rsi_compra"])
            ok_long=rsi<=limite and p_ema_ok; ok_short=rsi>=data["rsi_venta"] and (price<ema)
            out[coin]={"price":price,"rsi":round(rsi,1),"limite":limite,"p_ema_ok":p_ema_ok,"ok":ok_long,"ok_short":ok_short,"sug":"COMPRA LONG" if ok_long else "VENTA SHORT" if ok_short else "Espera","motivo":f"RSI {rsi:.1f}","ema":ema}
        except Exception as e:
            out[coin]={"price":0,"rsi":50,"limite":35,"p_ema_ok":False,"ok":False,"ok_short":False,"sug":"Error","motivo":str(e)[:90],"ema":0}
    return out

def auto_tune_logic(prices):
    if not data.get("auto_tune", True): return
    debajo=sum(1 for v in prices.values() if v["price"]>0 and v["price"] < v["ema"])
    if debajo>=6: data["filtro_ema"]="OFF"; data["sl_pct"]=-2.5; data["tp"]=0.3; data["rsi_venta"]=70; data["rsi_compra"]=40
    elif debajo<=2: data["filtro_ema"]="ON"; data["sl_pct"]=-1.0; data["tp"]=0.5; data["rsi_venta"]=75; data["rsi_compra"]=30
    else: data["filtro_ema"]="OFF"; data["sl_pct"]=-1.5; data["tp"]=0.3; data["rsi_venta"]=70; data["rsi_compra"]=35
    save()

@app.route("/", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def webhook():
    if request.method=="GET": return "BOT LIVE - /dashboard OK",200
    d=request.get_json(force=True,silent=True) or {}
    if "message" in d and "chat" in d["message"]:
        chat=d["message"]["chat"]["id"]
        if chat not in data["alert_users"]: data["alert_users"].append(chat); save()
        base=os.getenv("RENDER_EXTERNAL_URL","https://telegram-bot-cijp.onrender.com")
        tg(chat, f"500 USD = ${data['usd_mxn']*500:.0f} MXN\nAcum: ${data['gan_acum_total']:.2f} USD\n{base}/dashboard")
    return jsonify(ok=True)

@app.route("/dashboard")
def dashboard():
    if os.path.exists("dashboard.html"): return send_from_directory(".","dashboard.html")
    return "No existe dashboard.html",404

@app.route("/chart/<sym>")
def chart_page(sym):
    sym=sym.upper()
    return f'''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>{sym}</title></head><body><div id="tv" style="height:92vh"></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{sym}USDT","interval":"60","timezone":"America/Mexico_City","theme":"dark","style":"1","locale":"es","container_id":"tv"}});</script></body></html>'''

@app.route("/api/prices")
def api_prices(): return jsonify(get_prices_data())

@app.route("/api/state")
def api_state():
    bola=data["capital_actual"]/data["max_entradas"]
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"]>0 else 0
    prices=get_prices_data()
    for p in data["pos"]:
        pr=prices.get(p["sym"],{}).get("price",p["entry"]); p["ahora"]=pr; gan_b=(pr-p["entry"])/p["entry"]*100; gan_n=gan_b - (FEE*2*100); p["gan_neta_pct"]=gan_n; p["tipo"]="LONG"
    for p in data.get("pos_short",[]):
        pr=prices.get(p["sym"],{}).get("price",p["entry"]); p["ahora"]=pr; gan_b=(p["entry"]-pr)/p["entry"]*100; gan_n=gan_b - (FEE*2*100); p["gan_neta_pct"]=gan_n; p["tipo"]="SHORT"
    bloqueado=sum([x.get("monto", bola) for x in data["pos"]]) + sum([x.get("monto", bola) for x in data.get("pos_short",[])])
    disponible=data["capital_actual"]-bloqueado; disponible_mxn=disponible*data["usd_mxn"]
    return jsonify({
        "meta_mxn": data["usd_mxn"]*500, "gan_acum": data["gan_acum_total"], "gan_acum_mxn": data["gan_acum_mxn"],
        "usd_mxn": round(data["usd_mxn"],3), "pct_mes": data["pct_mes"], "gan_mes": data["gan_mes"],
        "ganadas": data["ganadas"], "salidas": data["salidas"], "winrate": winrate,
        "tp": data["tp"], "fee_total": FEE*2*100, "max_entradas": data["max_entradas"],
        "rsi_compra": data["rsi_compra"], "sl_pct": data["sl_pct"], "rsi_venta": data["rsi_venta"],
        "filtro_ema": data["filtro_ema"], "auto": data["auto"], "auto_tune": data.get("auto_tune",True),
        "modo": data.get("modo","AMBOS"), "coins_activas": data["coins_activas"],
        "bola": bola, "bola_mxn": bola*data["usd_mxn"],
        "capital": data["capital_actual"],
        "disponible_usd": disponible, "disponible_mxn": disponible_mxn, "bloqueado_usd": bloqueado,
        "pos": data["pos"]+data.get("pos_short",[]), "pos_long": data["pos"], "pos_short": data.get("pos_short",[]),
        "historial": data["historial"][-50:], "capital_history": data["capital_history"][-100:]
    })

@app.route("/api/config", methods=["POST"])
def api_config():
    j=request.json
    if "toggle_coin" in j: data["coins_activas"][j["toggle_coin"]]=not data["coins_activas"].get(j["toggle_coin"],True)
    if "max" in j: data["max_entradas"]=int(j["max"])
    if "modo" in j: data["modo"]=j["modo"]
    if "auto_tune" in j: data["auto_tune"]=(j["auto_tune"]=="ON" or j["auto_tune"]==True)
    if not data.get("auto_tune",True):
        if "rsi_compra" in j: data["rsi_compra"]=float(j["rsi_compra"])
        if "tp" in j: data["tp"]=float(j["tp"])
        if "sl_pct" in j: data["sl_pct"]=float(j["sl_pct"])
        if "rsi_venta" in j: data["rsi_venta"]=float(j["rsi_venta"])
        if "filtro_ema" in j: data["filtro_ema"]=j["filtro_ema"]
    if "rsi_coin" in j: data["rsi_por_moneda"][j["rsi_coin"]["sym"]]=float(j["rsi_coin"]["val"])
    if "rsi_coin_reset" in j: data["rsi_por_moneda"].pop(j["rsi_coin_reset"],None)
    save();return jsonify(ok=True)

@app.route("/api/sell/<sym>", methods=["POST"])
def sell_sym(sym):
    prices=get_prices_data()
    for p in list(data["pos"]):
        if p["sym"]==sym:
            pr=prices.get(sym,{}).get("price",p["entry"]); gan_b=(pr-p["entry"])/p["entry"]*100; gan_n=gan_b - FEE*2*100; gan_mxn=p["monto"]*gan_n/100*data["usd_mxn"]
            data["capital_actual"]+=p["monto"]*gan_n/100; data["gan_acum_total"]+=p["monto"]*gan_n/100; data["gan_acum_mxn"]+=gan_mxn; data["salidas"]+=1
            if gan_n>0: data["ganadas"]+=1
            data["historial"].append({"fecha":time.strftime("%m-%d %H:%M"),"sym":sym+" LONG","monto":p["monto"],"entry":p["entry"],"exit":pr,"gan_neta_pct":gan_n,"gan_neta_mxn":gan_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
            data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]})
            data["pos"].remove(p); save(); return jsonify(ok=True)
    return jsonify(ok=True)

@app.route("/api/toggle", methods=["POST"])
def toggle(): data["auto"]=not data["auto"]; save(); return jsonify(ok=True)

@app.route("/api/backup")
def api_backup(): return jsonify(data)

@app.route("/api/restore", methods=["POST"])
def api_restore():
    try:
        nuevo=request.get_json(force=True); global data; data=nuevo; save(); return jsonify(ok=True)
    except Exception as e: return jsonify(ok=False, error=str(e))

@app.route("/recuperar")
def recuperar():
    data["capital_actual"]=500.23559026914177
    data["gan_acum_total"]=0.2355902691417667
    data["gan_acum_mxn"]=3.995610964443636
    data["ganadas"]=2; data["salidas"]=2
    data["historial"]=[
        {"fecha":"08-23 04:11","sym":"ADA LONG","monto":62.5,"entry":0.2183,"exit":0.2192,"gan_neta_pct":0.21,"gan_neta_mxn":2.25,"capital_despues":500.13267292716444,"bola_despues":62.51},
        {"fecha":"08-23 04:11","sym":"AVAX LONG","monto":62.5,"entry":7.404,"exit":7.431,"gan_neta_pct":0.10,"gan_neta_mxn":1.74,"capital_despues":500.23559026914177,"bola_despues":62.52}
    ]
    data["capital_history"]=[{"t": int(time.time()*1000)-10000, "cap": 500.13},{"t": int(time.time()*1000), "cap": 500.23}]
    save()
    return "RECUPERADO $500.23 - Ve a /dashboard"

def auto_loop():
    last_tune=0; last_usd=0
    while True:
        try:
            if time.time()-last_usd>900:
                try: data["usd_mxn"]=get_usd_mxn_live(); save()
                except: pass
                last_usd=time.time()
            if data["auto"]:
                prices=get_prices_data()
                if time.time()-last_tune>900:
                    try: auto_tune_logic(prices)
                    except: pass
                    last_tune=time.time()
                total_max=data["max_entradas"]; max_long=(total_max+1)//2; max_short=total_max//2
                if data.get("modo","AMBOS") in ["LONG","AMBOS"]:
                    if len(data["pos"]) < max_long:
                        for sym,info in prices.items():
                            if info["price"]>0 and info["ok"] and data["coins_activas"].get(sym,True) and not any(x["sym"]==sym for x in data["pos"]):
                                if len(data["pos"])>=max_long: break
                                monto=data["capital_actual"]/total_max; data["pos"].append({"sym":sym,"entry":info["price"],"monto":monto}); save(); break
                if data.get("modo","AMBOS") in ["SHORT","AMBOS"]:
                    if len(data.get("pos_short",[])) < max_short:
                        for sym,info in prices.items():
                            if info["price"]>0 and info.get("ok_short") and data["coins_activas"].get(sym,True) and not any(x["sym"]==sym for x in data.get("pos_short",[])):
                                if len(data["pos_short"])>=max_short: break
                                monto=data["capital_actual"]/total_max; data.setdefault("pos_short",[]).append({"sym":sym,"entry":info["price"],"monto":monto}); save(); break
        except Exception as e: print("AUTO ERROR",e)
        time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
