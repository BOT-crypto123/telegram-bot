import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
FILE="bot_data.json"
FEE_ENTRADA=0.001
FEE_SALIDA=0.001
FEE_TOTAL=0.002
SLIPPAGE=0.0005
META_MES_USD=500.0
MODO_SIMULACION=True

data={
    "base_inicial": 0.0,
    "capital_actual": 450.0,
    "gan_acum_total": 0.0,
    "gan_mes": 0.0,
    "gan_hoy": 0.0,
    "pos": [{"sym":"ETH","monto":50.0,"entry":2428.64,"ahora":2428.64,"rsi_entry":27.0,"motivo":"RECUPERADO","fecha":"22/05 12:08"}],
    "historial": [],
    "capital_history": [{"t": int(time.time()*1000), "cap": 500.0}],
    "coins": ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas": 10,
    "tp_bruto": 0.3,
    "auto": True,
    "alert_users": [],
    "entradas": 1,
    "salidas": 0,
    "ganadas": 0,
    "perdidas": 0,
    "last_alert": {},
    "usd_mxn": 16.96,
    "rsi_compra": 35.0,
    "rsi_por_moneda": {},
    "sl_pct": -2.0,
    "rsi_venta": 70.0,
    "filtro_ema": "OFF"
}

def load():
    if os.path.exists(FILE):
        try:
            j=json.load(open(FILE))
            # Si hay backup con pos, respetalo
            if len(j.get("pos",[]))>0 or j.get("capital_actual",500)!=500:
                data.update(j)
        except:
            pass

def save():
    try:
        json.dump(data, open(FILE,'w'))
    except:
        pass

load()

def P(s):
    for url in [f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT",f"https://api.binance.com/api/v3/ticker/price?symbol={s}USDT"]:
        try:
            j=requests.get(url,timeout=4).json()
            if 'price' in j:
                return float(j['price'])
        except:
            continue
    return 0

def C(s):
  for url in [f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=100",f"https://api.binance.com/api/v3/klines?symbol={s}USDT&interval=1h&limit=100"]:
    try:
      r=requests.get(url,timeout=5).json()
      if isinstance(r, list) and len(r)>20:
        return [float(x[4]) for x in r]
    except:
        continue
  return
