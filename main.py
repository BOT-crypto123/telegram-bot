import os, json, time, threading, requests
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
app=Flask(__name__)
DATA_FILE="bot_data.json";FEE=0.001
POSIBLES_RUTAS=["/data/bot_data.json","bot_data.json","bot_data_binance.json"]
default_data={"capital_binance":500.0,"capital_mt5":500.0,"usd_mxn":18.5,"gan_acum_total":0.0,"ganadas":0,"salidas":0,"tp":0.3,"sl_pct":-1.5,"rsi_compra":35,"rsi_venta":70,"filtro_ema":"OFF","max_entradas":8,"auto":True,"auto_tune":True,"modo":"AMBOS","pos":[],"pos_short":[],"historial":[],"coins_activas":{"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"ADA":True,"AVAX":True,"DOGE":True},"coins_mt5_activas":{"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True},"rsi_por_moneda":{},"alert_users":[]}
try:
 for p in POSIBLES_RUTAS:
  if os.path.exists(p):
   with open(p) as f: data=json.load(f);break
 else: raise FileNotFoundError
 for k,v in default_data.items():
  if k not in data: data[k]=v
except: data=default_data.copy()
def save():
 for p in [DATA_FILE,"/data/bot_data.json"]:
  try: Path(p).parent.mkdir(parents=True,exist_ok=True);json.dump(data,open(p,"w"))
  except: pass
USD_CACHE={"price":18.5,"t":0,"last_ok":18.5}
def get_usd_mxn_live(force=False):
 now=time.time()
 if not force and now-USD_CACHE["t"]<60: return USD_CACHE["price"]
 for fn in [lambda: requests.get("https://open.er-api.com/v6/latest/USD",timeout=8).json()["rates"]["MXN"],lambda: requests.get("https://api.frankfurter.app/latest?from=USD&to=MXN",timeout=8).json()["rates"]["MXN"]]:
  try:
   mxn=float(fn())
   if 10<mxn<30: USD_CACHE["price"]=mxn;USD_CACHE["t"]=now;USD_CACHE["last_ok"]=mxn;data["usd_mxn"]=mxn;save();return mxn
  except: continue
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
 rs=gains/losses;return 100-(100/(1+rs))
def get_prices_data():
 out={}
 for sym in SYMS:
  coin=sym.replace("/USDT","");bin_sym=sym.replace("/","")
  try:
   r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={bin_sym}&interval=1h&limit=100",timeout=10).json()
   closes=[float(k[4]) for k in r];price=closes[-1];rsi=get_rsi(closes);ema=sum(closes[-20:])/20
   p_ema_ok=price>ema if data["filtro_ema"]=="ON" else True;limite=data["rsi_por_moneda"].get(coin,data["rsi_compra"])
   ok_long=rsi<=limite and p_ema_ok;ok_short=rsi>=data["rsi_venta"] and (price<ema)
   out[coin]={"price":price,"rsi":round(rsi,1),"limite":limite,"p_ema_ok":p_ema_ok,"ok":ok_long,"ok_short":ok_short,"sug":"COMPRA LONG" if ok_long else "VENTA SHORT" if ok_short else "Espera","motivo":f"RSI {rsi:.1f}","ema":ema}
  except Exception as e: out[coin]={"price":0,"rsi":50,"limite":35,"p_ema_ok":False,"ok":False,"ok_short":False,"sug":"Error","motivo":str(e)[:90],"ema":0}
 return out
def get_prices_mt5(): return {"XAUUSD":{"price":2341.2,"rsi":45,"ok":True,"sug":"COMPRA LONG","change":0.64},"XAGUSD":{"price":28.15,"rsi":52,"ok":False,"sug":"Espera","change":-0.31},"USOIL":{"price":76.42,"rsi":48,"ok":True,"sug":"COMPRA LONG","change":1.08},"SPX500":{"price":5432.1,"rsi":55,"ok":False,"sug":"Espera","change":0.42}}
def auto_tune_logic(prices):
 if not data.get("auto_tune",True): return
 debajo=sum(1 for v in prices.values() if v["price"]>0 and v["price"]<v["ema"])
 if debajo>=6: data["filtro_ema"]="OFF";data["sl_pct"]=-2.5;data["tp"]=0.3
 elif debajo<=2: data["filtro_ema"]="ON";data["sl_pct"]=-1.0;data["tp"]=0.5
 else: data["filtro_ema"]="OFF";data["sl_pct"]=-1.5;data["tp"]=0.3
 save()
@app.route("/")
def home(): return "BOT LIVE V5 FULL CEL - OK",200
@app.route("/dashboard")
def dashboard():
 if os.path.exists("dashboard.html"): return send_from_directory(".","dashboard.html")
 return "No dashboard.html",404
@app.route("/api/prices")
def api_prices(): return jsonify(get_prices_data())
@app.route("/api/prices_mt5")
def api_prices_mt5(): return jsonify(get_prices_mt5())
@app.route("/api/state")
def api_state():
 usd_live=get_usd_mxn_live();max_ent=data.get("max_entradas",8);bola_base=data.get("capital_binance",500.0)/max(1,max_ent);prices=get_prices_data()
 for p in data.get("pos",[]): pr=prices.get(p["sym"],{}).get("price",p["entry"]);p["ahora"]=pr;p["gan_neta_pct"]=(pr-p["entry"])/p["entry"]*100-(FEE*2*100);p["tipo"]="LONG"
 for p in data.get("pos_short",[]): pr=prices.get(p["sym"],{}).get("price",p["entry"]);p["ahora"]=pr;p["gan_neta_pct"]=(p["entry"]-pr)/p["entry"]*100-(FEE*2*100);p["tipo"]="SHORT"
 bloqueado=sum([x.get("monto",bola_base) for x in data.get("pos",[])])+sum([x.get("monto",bola_base) for x in data.get("pos_short",[])])
 gan_total=data.get("gan_acum_total",0.0);capital_bin=data.get("capital_binance",500.0)
 if bloqueado==0: disponible=capital_bin;total_real=capital_bin+gan_total
 else: disponible=capital_bin-bloqueado;total_real=disponible+bloqueado+gan_total
 bola_real=total_real/max(1,max_ent);winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"]>0 else 0
 return jsonify({"capital_binance":capital_bin,"capital_mt5":data.get("capital_mt5",500.0),"capital":total_real+data.get("capital_mt5",500.0),"capital_total_real":total_real,"total_real_usd":total_real,"bola":bola_real,"bola_binance":bola_base,"bola_mxn":bola_real*usd_live,"gan_acum":gan_total,"usd_mxn":round(usd_live,4),"ganadas":data.get("ganadas",0),"salidas":data.get("salidas",0),"winrate":winrate,"max_entradas":max_ent,"auto":data.get("auto",True),"coins_activas":data.get("coins_activas",{}),"disponible_usd":disponible,"bloqueado_usd":bloqueado,"pos":data.get("pos",[])+data.get("pos_short",[]),"historial
