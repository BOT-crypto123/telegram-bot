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
except:
    data=default_data.copy()

def save():
    for p in [DATA_FILE, DATA_FILE_BINANCE, "/data/bot_data.json", "/data/bot_data_binance.json"]:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            with open(p,"w") as f: json.dump(data,f)
        except: pass

USD_CACHE = {"price": 18.5, "t": 0, "last_ok": 18.5}
def get
