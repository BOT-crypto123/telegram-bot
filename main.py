import os, json, time, threading, requests, random
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"
FEE = 0.001
POSIBLES_RUTAS = ["/data/bot_data.json", "bot_data.json", "bot_data_binance.json"]

default_data = {
 "capital_actual": 500.0,
 "capital_inicial": 500.0,
 "capital_binance": 500.0,
 "capital_mt5": 500.0,
 "usd_mxn": 18.5,
 "gan_acum_total": 0.0,
 "gan_acum_mxn": 0.0,
 "gan_mes": 0.0,
 "pct_mes": 0.0,
 "ganadas": 0,
 "salidas": 0,
 "tp": 0.3,
 "sl_pct": -1.5,
 "rsi_compra": 35,
 "rsi_venta": 70,
 "filtro_ema": "OFF",
 "max_entradas": 8,
 "auto": True,
 "auto_tune": True,
 "modo": "AMBOS",
 "pos": [],
 "pos_short": [],
 "pos_mt5": [],
 "historial": [],
 "historial_binance": [],
 "historial_mt5": [],
 "capital_history": [],
 "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"ADA":True,"AVAX":True,"DOGE":True},
 "coins_mt5_activas": {"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True},
 "rsi_por_moneda": {},
 "alert_users": []
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
        if k not in data:
            data[k]=v
except:
    data=default_data.copy()

def save():
    try:
        Path(DATA_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE,"w") as f:
            json.dump(data,f)
        with open("/data/bot_data.json","w") as f:
            json.dump(data,f)
    except:
        pass

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
            u = os.environ.get("RENDER_EXTERNAL_URL") or "https://telegram-bot-cijp.onrender.com/"
            requests.get(u, timeout=10)
        except:
            pass
        time.sleep(600)
threading.Thread(target=keep_alive_render, daemon=True).start()

USD_CACHE = {"price": data.get("usd_mxn",18.5), "t": 0, "
