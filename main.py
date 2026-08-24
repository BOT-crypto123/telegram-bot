import os, json, time, threading, requests, random
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"
DATA_FILE_BINANCE = "bot_data_binance.json"
DATA_FILE_MT5 = "bot_data_mt5.json"
FEE = 0.001
POSIBLES_RUTAS = ["/data/bot_data.json", "bot_data.json", "bot_data_binance.json"]

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

data = default_data.copy()
try:
    for p in POSIBLES_RUTAS:
        if os.path.exists(p):
            with open(p) as f:
                loaded_json=json.load(f)
                data.update(loaded_json)
            break
    for k,v in default_data.items():
        if k not in data: data[k]=v
except:
    data=default_data.copy()

def save():
    for p in [DATA_FILE, DATA_FILE_BINANCE, "/data/bot_data.json"]:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            with open(p,"w") as f: json.dump(data,f)
        except: pass
    try:
        with open(DATA_FILE_MT5,"w") as f: json.dump(data,f)
        with open("/data/"+DATA_FILE_MT5,"w") as f: json.dump(data,f)
    except: pass

def tg(chat_id, text):
    if not BOT_TOKEN:
        return
    try:
        DASH_URL = "https://telegram-bot-cijp.onrender.com/dashboard"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "inline_keyboard": [[{"text":"🚀 VER DASHBOARD V5","url": DASH_URL}]]
            }
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("TG ERROR", e)

def keep_alive_render():
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL") or "https://telegram-bot-cijp.onrender.com/"
            requests.get(url, timeout=10)
        except: pass
        time.sleep(600)
threading.Thread(target=keep_alive_render, daemon=True).start()

USD_CACHE = {"price": data.get("usd_mxn",18.5), "t": 0, "last_ok": 18.5}
def get_usd_mxn_live(force=False):
    now=time.time()
    if not force and now-USD_CACHE["t"]<300: return USD_CACHE["price"]
    try:
        r=requests.get("https://open.er-api.com/v6/latest/USD",timeout=8).json()
        mxn=float(r["rates"]["MXN"])
        if 10<mxn<30:
            USD_CACHE["price"]=mxn; USD_CACHE["t"]=now; USD_CACHE["last_ok"]=mxn
            data["usd_mxn"]=mxn; save(); return mxn
    except: pass
    return USD_CACHE.get("last_ok",18.5)

SYMS=["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","ADA/USDT","AVAX/USDT","DOGE/USDT"]
def get_rsi(prices,p=14):
    if len(prices)<p+1: return 50
    gains=losses=0
    for i in range(1,p+1):
        d=prices[-i]-prices[-i-1]
        if d>=0: gains+=d
        else: losses+=-d
    if losses==0: return 100
    rs=gains/losses
    return 100-(100/(1+rs))

def get_prices_data():
    out={}
    for sym in SYMS:
        coin=sym.replace("/USDT",""); bin_sym=sym.replace("/","")
        try:
            r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={bin_sym}&interval=1h&limit=100",timeout=10).json()
            closes=[float(k[4]) for k in r]; price=closes[-1]; rsi=get_rsi(closes); ema=sum(closes[-20:])/20
            p_ema_ok=price>ema if data["filtro_ema"]=="ON" else True
            limite=data["rsi_por_moneda"].get(coin,data["rsi_compra"])
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
    except: out["XAUUSD"]={"price":2341.20+random.uniform(-3,3),"rsi":45,"ok":True,"sug":"COMPRA LONG","change":0.64}
    try:
        r=requests.get("https://api.gold-api.com/price/XAG",timeout=8).json()
        out["XAGUSD"]={"price":float(r.get("price",28.15)),"rsi":52,"ok":False,"sug":"Espera","change":-0.31}
    except: out["XAGUSD"]={"price":28.15+random.uniform(-0.3,0.3),"rsi":52,"ok":False,"sug":"Espera","change":-0.31}
    out["USOIL"]={"price":76.42+random.uniform(-0.5,0
