import os, json, time, threading, requests, random
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"
DATA_FILE_BINANCE = "bot_data_binance.json"
DATA_FILE_MT5 = "bot_data_mt5.json"
FEE = 0.001
POSIBLES_RUTAS = ["/data/bot_data.json", "bot_data.json", "bot_data_binance.json", "/data/bot_data_binance.json"]

default_data = {
 "capital_actual": 500.0, "capital_inicial": 500.0,
 "capital_binance": 500.0, "capital_mt5": 500.0,
 "usd_mxn": 18.5,
 "gan_acum_total": 0.0, "gan_acum_mxn": 0.0, "gan_mes": 0.0, "pct_mes": 0.0,
 "ganadas": 0, "salidas": 0, "tp": 0.3, "sl_pct": -1.5, "rsi_compra": 35, "rsi_venta": 70,
 "filtro_ema": "OFF", "max_entradas": 8, "auto": True, "auto_tune": True,
 "modo": "AMBOS",
 "pos": [], "pos_short": [],
 "pos_binance": [], "pos_mt5": [],
 "historial": [], "historial_binance": [], "historial_mt5": [],
 "capital_history": [], "capital_history_binance": [], "capital_history_mt5": [],
 "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"ADA":True,"AVAX":True,"DOGE":True},
 "coins_mt5_activas": {"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True},
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
    if "capital_binance" not in data:
        data["capital_binance"] = data.get("capital_actual",500)
        data["capital_mt5"] = 500.0
    if "historial_binance" not in data: data["historial_binance"]=data.get("historial",[])
    if "historial_mt5" not in data: data["historial_mt5"]=[]
    if "capital_history_binance" not in data: data["capital_history_binance"]=data.get("capital_history",[])
except:
    data=default_data.copy()

def save():
    for p in [DATA_FILE, DATA_FILE_BINANCE, "/data/bot_data.json", "/data/bot_data_binance.json"]:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            with open(p,"w") as f: json.dump(data,f)
        except: pass
    try:
        with open(DATA_FILE_MT5,"w") as f:
            json.dump({"capital_mt5":data["capital_mt5"],"pos_mt5":data.get("pos_mt5",[]),"historial_mt5":data.get("historial_mt5",[]),"capital_history_mt5":data.get("capital_history_mt5",[]),"coins_mt5_activas":data["coins_mt5_activas"]},f)
        with open("/data/"+DATA_FILE_MT5,"w") as f:
            json.dump({"capital_mt5":data["capital_mt5"],"pos_mt5":data.get("pos_mt5",[]),"historial_mt5":data.get("historial_mt5",[]),"capital_history_mt5":data.get("capital_history_mt5",[]),"coins_mt5_activas":data["coins_mt5_activas"]},f)
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

USD_CACHE = {"price": 18.5, "t": 0, "last_ok": 18.5}
def get_usd_mxn_live(force=False):
    now = time.time()
    if not force and now - USD_CACHE["t"] < 60:
        return USD_CACHE["price"]
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8).json()
        mxn = float(r["rates"]["MXN"])
        if 10 < mxn < 30:
            USD_CACHE["price"]=mxn; USD_CACHE["t"]=now; USD_CACHE["last_ok"]=mxn
            data["usd_mxn"]=mxn; save()
            return mxn
    except: pass
    try:
        r2 = requests.get("https://api.frankfurter.app/latest?from=USD&to=MXN", timeout=8).json()
        mxn2 = float(r2["rates"]["MXN"])
        if 10 < mxn2 < 30:
            USD_CACHE["price"]=mxn2; USD_CACHE["t"]=now; USD_CACHE["last_ok"]=mxn2
            data["usd_mxn"]=mxn2; save()
            return mxn2
    except: pass
    try:
        r3 = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=8).json()
        mxn3 = float(r3["rates"]["MXN"])
        if 10 < mxn3 < 30:
            USD_CACHE["price"]=mxn3; USD_CACHE["t"]=now; USD_CACHE["last_ok"]=mxn3
            data["usd_mxn"]=mxn3; save()
            return mxn3
    except: pass
    return USD_CACHE.get("last_ok", data.get("usd_mxn", 18.5))

USD_CACHE["price"] = data.get("usd_mxn", 18.5)
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

def get_prices_mt5():
    out={}
    try:
        r=requests.get("https://api.gold-api.com/price/XAU",timeout=8).json()
        out["XAUUSD"]={"price":float(r.get("price",2341.20)),"rsi":45,"ok":True,"sug":"COMPRA LONG","change":0.64}
    except:
        out["XAUUSD"]={"price":2341.20+random.uniform(-3,3),"rsi":45,"ok":True,"sug":"COMPRA LONG","change":0.64}
    try:
        r=requests.get("https://api.gold-api.com/price/XAG",timeout=8).json()
        out["XAGUSD"]={"price":float(r.get("price",28.15)),"rsi":52,"ok":False,"sug":"Espera","change":-0.31}
    except:
        out["XAGUSD"]={"price":28.15+random.uniform(-0.3,0.3),"rsi":52,"ok":False,"sug":"Espera","change":-0.31}
    out["USOIL"]={"price":76.42+random.uniform(-0.5,0.5),"rsi":48,"ok":True,"sug":"COMPRA LONG","change":1.08}
    out["SPX500"]={"price":5432.10+random.uniform(-5,5),"rsi":55,"ok":False,"sug":"Espera","change":0.42}
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
    if request.method=="GET": return "BOT LIVE V5 DUAL SEPARADO - /dashboard OK",200
    d=request.get_json(force=True,silent=True) or {}
    if "message" in d and "chat" in d["message"]:
        chat=d["message"]["chat"]["id"]
        if chat not in data["alert_users"]: data["alert_users"].append(chat); save()
        base=os.getenv("RENDER_EXTERNAL_URL","https://telegram-bot-cijp.onrender.com")
        tg(chat, f"DUAL V5 SEPARADO\nBinance: ${data['capital_binance']:.2f} + MT5: ${data['capital_mt5']:.2f} = ${data['capital_binance']+data['capital_mt5']:.2f}\n{base}/dashboard")
    return jsonify(ok=True)

@app.route("/dashboard")
def dashboard():
    if os.path.exists("dashboard.html"): return send_from_directory(".","dashboard.html")
    return "No existe dashboard.html",404

@app.route("/api/prices")
def api_prices(): return jsonify(get_prices_data())

@app.route("/api/prices_mt5")
def api_prices_mt5(): return jsonify(get_prices_mt5())

@app.route("/api/state")
def api_state():
    usd_live = get_usd_mxn_live()
    max_ent = data.get("max_entradas",8)
    bola_base = data.get("capital_binance",500.0)/max(1,max_ent)
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"]>0 else 0
    prices=get_prices_data()
    for p in data.get("pos",[]):
        pr=prices.get(p["sym"],{}).get("price",p["entry"])
        p["ahora"]=pr
        gan_b=(pr-p["entry"])/p["entry"]*100
        p["gan_neta_pct"]=gan_b - (FEE*2*100)
        p["tipo"]="LONG"
    for p in data.get("pos_short",[]):
        pr=prices.get(p["sym"],{}).get("price",p["entry"])
        p["ahora"]=pr
        gan_b=(p["entry"]-pr)/p["entry"]*100
        p["gan_neta_pct"]=gan_b - (FEE*2*100)
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
    return jsonify({
        "capital_binance": capital_bin,
        "capital_mt5": data.get("capital_mt5",500.0),
        "capital": total_real + data.get("capital_mt5",500.0),
        "capital_total_real": total_real,
        "total_real_usd": total_real,
        "bola": bola_real,
        "bola_binance": bola_base,
        "bola_mt5": data.get("capital_mt5",500.0)/4,
        "bola_mxn": bola_real*usd_live,
        "meta_mxn": usd_live*500,
        "gan_acum": gan_total,
        "gan_acum_total": gan_total,
        "usd_mxn": round(usd_live,4),
        "pct_mes": data.get("pct_mes",0),
        "gan_mes": data.get("gan_mes",0),
        "ganadas": data.get("ganadas",0),
        "salidas": data.get("salidas",0),
        "winrate": winrate,
        "tp": data.get("tp",0.3),
        "fee_total": FEE*2*100,
        "max_entradas": max_ent,
        "rsi_compra": data.get("rsi_compra",35),
        "sl_pct": data.get("sl_pct",-1.5),
        "rsi_venta": data.get("rsi_venta",70),
        "filtro_ema": data.get("filtro_ema","OFF"),
        "auto": data.get("auto",True),
        "auto_tune": data.get("auto_tune",True),
        "modo": data.get("modo","AMBOS"),
        "coins_activas": data.get("coins_activas",{}),
        "coins_mt5_activas": data.get("coins_mt5_activas",{}),
        "disponible_usd": disponible,
        "bloqueado_usd": bloqueado,
        "pos": data.get("pos",[])+data.get("pos_short",[]),
        "pos_long": data.get("pos",[]),
        "pos_short": data.get("pos_short",[]),
        "pos_binance": data.get("pos",[]),
        "pos_mt5": data.get("pos_mt5",[]),
        "historial": data.get("historial",[])[-50:],
        "capital_history": data.get("capital_history",[])[-100:]
    })

@app.route("/api/config", methods=["POST"])
def api_config():
    j=request.json
    if "toggle_coin" in j: data["coins_activas"][j["toggle_coin"]]=not data["coins_activas"].get(j["toggle_coin"],True)
    if "toggle_coin_mt5" in j: data["coins_mt5_activas"][j["toggle_coin_mt5"]]=not data["coins_mt5_activas"].get(j["toggle_coin_mt5"],True)
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
            data["capital_binance"]+=p["monto"]*gan_n/100; data["capital_actual"]=data["capital_binance"]
            data["gan_acum_total"]+=p["monto"]*gan_n/100; data["salidas"]+=1
            if gan_n>0: data["ganadas"]+=1
            h={"fecha":time.strftime("%m-%d %H:%M"),"sym":sym+" LONG","monto":p["monto"],"entry":p["entry"],"exit":pr,"gan_neta_pct":gan_n,"gan_neta_mxn":gan_mxn,"capital_despues":data["capital_binance"],"bola_despues":data["capital_binance"]/data["max_entradas"]}
            data["historial"].append(h); data["historial_binance"].append(h)
            data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_binance"]})
            data["capital_history_binance"].append({"t":int(time.time()*1000),"cap":data["capital_binance"]})
            data["pos"].remove(p); save(); return jsonify(ok=True)
    return jsonify(ok=True)

@app.route("/api/toggle", methods=["POST"])
def toggle(): data["auto"]=not data["auto"]; save(); return jsonify(ok=True)

@app.route("/api/backup")
def api_backup():
    tipo=request.args.get("tipo","all")
    if tipo=="binance": return jsonify({"tipo":"binance","capital_binance":data["capital_binance"],"pos_binance":data["pos"],"historial_binance":data.get("historial_binance",data["historial"]),"capital_history_binance":data.get("capital_history_binance",data["capital_history"]),"coins_activas":data["coins_activas"],"usd_mxn":data["usd_mxn"]})
    if tipo=="mt5": return jsonify({"tipo":"mt5","capital_mt5":data["capital_mt5"],"pos_mt5":data.get("pos_mt5",[]),"historial_mt5":data.get("historial_mt5",[]),"capital_history_mt5":data.get("capital_history_mt5",[]),"coins_mt5_activas":data["coins_mt5_activas"],"usd_mxn":data["usd_mxn"]})
    return jsonify(data)

@app.route("/api/backup/binance")
def api_backup_binance():
    return jsonify({"tipo":"binance","capital_binance":data["capital_binance"],"pos_binance":data["pos"],"historial_binance":data.get("historial_binance",data["historial"]),"capital_history_binance":data.get("capital_history_binance",data["capital_history"]),"coins_activas":data["coins_activas"],"usd_mxn":data["usd_mxn"],"timestamp":int(time.time())})

@app.route("/api/backup/mt5")
def api_backup_mt5():
    return jsonify({"tipo":"mt5","capital_mt5":data["capital_mt5"],"pos_mt5":data.get("pos_mt5",[]),"historial_mt5":data.get("historial_mt5",[]),"capital_history_mt5":data.get("capital_history_mt5",[]),"coins_mt5_activas":data["coins_mt5_activas"],"usd_mxn":data["usd_mxn"],"timestamp":int(time.time())})

@app.route("/api/restore", methods=["POST"])
def api_restore():
    try:
        nuevo=request.get_json(force=True)
        tipo=nuevo.get("tipo","all")
        if tipo=="binance":
            if "capital_binance" in nuevo: data["capital_binance"]=nuevo["capital_binance"]
            if "pos_binance" in nuevo: data["pos"]=nuevo["pos_binance"]
            if "historial_binance" in nuevo: data["historial_binance"]=nuevo["historial_binance"]; data["historial"]=nuevo["historial_binance"]
            if "capital_history_binance" in nuevo: data["capital_history_binance"]=nuevo["capital_history_binance"]
            save(); return jsonify(ok=True, msg="BINANCE restaurado")
        if tipo=="mt5":
            if "capital_mt5" in nuevo: data["capital_mt5"]=nuevo["capital_mt5"]
            if "pos_mt5" in nuevo: data["pos_mt5"]=nuevo["pos_mt5"]
            if "historial_mt5" in nuevo: data["historial_mt5"]=nuevo["historial_mt5"]
            if "capital_history_mt5" in nuevo: data["capital_history_mt5"]=nuevo["capital_history_mt5"]
            save(); return jsonify(ok=True, msg="MT5 restaurado")
         global data
        data=nuevo
        for k,v in default_data.items():
            if k not in data: data[k]=v
        save(); return jsonify(ok=True, msg="TODO restaurado")
    except Exception as e: return jsonify(ok=False, error=str(e))

def auto_loop():
    last_tune=0; last_usd=0
    while True:
        try:
            if time.time()-last_usd>60:
                try: get_usd_mxn_live(force=True)
                except: pass
                last_usd=time.time()
            if data["auto"]:
                prices=get_prices_data()
                if time.time()-last_tune>900:
                    try: auto_tune_logic(prices)
                    except: pass
                    last_tune=time.time()
                total_max=data["max_entradas"]; max_long=(total_max+1)//2
                if data.get("modo","AMBOS") in ["LONG","AMBOS"]:
                    if len(data["pos"]) < max_long:
                        for sym,info in prices.items():
                            if info["price"]>0 and info["ok"] and data["coins_activas"].get(sym,True) and not any(x["sym"]==sym for x in data["pos"]):
                                monto=data["capital_binance"]/total_max; data["pos"].append({"sym":sym,"entry":info["price"],"monto":monto}); save(); break
        except Exception as e: print("AUTO ERROR",e)
        time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
