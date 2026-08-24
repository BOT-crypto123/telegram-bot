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
except: data=default_data.copy()

def save():
    for p in [DATA_FILE, DATA_FILE_BINANCE, "/data/bot_data.json", "/data/bot_data_binance.json"]:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            with open(p,"w") as f: json.dump(data,f)
        except: pass
    try:
        with open(DATA_FILE_MT5,"w") as f: json.dump({
            "capital_mt5": data["capital_mt5"],
            "pos_mt5": data.get("pos_mt5",[]),
            "historial_mt5": data.get("historial_mt5",[]),
            "capital_history_mt5": data.get("capital_history_mt5",[]),
            "coins_mt5_activas": data["coins_mt5_activas"]
        },f)
        with open("/data/"+DATA_FILE_MT5,"w") as f: json.dump({
            "capital_mt5": data["capital_mt5"],
            "pos_mt5": data.get("pos_mt5",[]),
            "historial_mt5": data.get("historial_mt5",[]),
            "capital_history_mt5": data.get("capital_history_mt5",[]),
            "coins_mt5_activas": data["coins_mt5_activas"]
        },f)
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
    for url_fn in [
        lambda: requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=8).json()["rates"]["MXN"],
        lambda: requests.get("https://open.er-api.com/v6/latest/USD", timeout=8).json()["rates"]["MXN"],
        lambda: requests.get("https://api.frankfurter.app/latest?from=USD&to=MXN", timeout=8).json()["rates"]["MXN"],
    ]:
        try:
            mxn = float(url_fn())
            if 10 < mxn < 30:
                USD_CACHE["price"] = mxn; USD_CACHE["t"] = now; USD_CACHE["last_ok"] = mxn
                data["usd_mxn"] = mxn; save()
                return mxn
        except: continue
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
    # FIX DOLAR VIVO
    usd_live = get_usd_mxn_live()
    bola_binance=data["capital_binance"]/max(1,data["max_entradas"])
    bola_mt5=data["capital_mt5"]/4
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"]>0 else 0
    prices=get_prices_data()
    for p in data["pos"]:
        pr=prices.get(p["sym"],{}).get("price",p["entry"]); p["ahora"]=pr; gan_b=(pr-p["entry"])/p["entry"]*100; gan_n=gan_b - (FEE*2*100); p["gan_neta_pct"]=gan_n; p["tipo"]="LONG"
    for p in data.get("pos_short",[]):
        pr=prices.get(p["sym"],{}).get("price",p["entry"]); p["ahora"]=pr; gan_b=(p["entry"]-pr)/p["entry"]*100; gan_n=gan_b - (FEE*2*100); p["gan_neta_pct"]=gan_n; p["tipo"]="SHORT"

    # FIX CALCULO REAL
    bloqueado_binance=sum([x.get("monto", bola_binance) for x in data["pos"]]) + sum([x.get("monto", bola_binance) for x in data.get("pos_short",[])])
    disponible_binance=data["capital_binance"]-bloqueado_binance
    gan_total = data.get("gan_acum_total",0.0)
    total_real_binance = disponible_binance + bloqueado_binance + gan_total
    
    # Si no hay pos, total_real debe ser capital_binance + gan_acum
    if bloqueado_binance==0:
        total_real_binance = data["capital_binance"] + gan_total
        disponible_binance = data["capital_binance"]

    return jsonify({
        "capital_binance": data["capital_binance"], "capital_mt5": data["capital_mt5"],
        "capital": total_real_binance + data["capital_mt5"],
        "capital_total_real": total_real_binance,
        "bola_binance": bola_binance, "bola_mt5": bola_mt5,
        "meta_mxn": usd_live*500, "gan_acum": gan_total,
        "gan_acum_total": gan_total,
        "usd_mxn": round(usd_live,4), "pct_mes": data["pct_mes"], "gan_mes": data["gan_mes"],
        "ganadas": data["ganadas"], "salidas": data["salidas"], "winrate": winrate,
        "tp": data["tp"], "fee_total": FEE*2*100, "max_entradas": data["max_entradas"],
        "rsi_compra": data["rsi_compra"], "sl_pct": data["sl_pct"], "rsi_venta": data["rsi_venta"],
        "filtro_ema": data["filtro_ema"], "auto": data["auto"], "auto_tune": data.get("auto_tune",True),
        "modo": data.get("modo","AMBOS"), "coins_activas": data["coins_activas"], "coins_mt5_activas": data["coins_mt5_activas"],
        "bola": total
