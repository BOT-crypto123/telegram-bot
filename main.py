import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
FILE="bot_data.json"
FEE=0.002; SLIPPAGE=0.0005; META=500.0
data={"capital_actual":500.0,"gan_acum_total":0.0,"gan_mes":0.0,"pos":[],"historial":[],"capital_history":[{"t":int(time.time()*1000),"cap":500.0}],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"coins_activas":{"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},"max_entradas":3,"tp_bruto":0.3,"auto":True,"alert_users":[],"entradas":0,"salidas":0,"ganadas":0,"perdidas":0,"usd_mxn":17.0,"rsi_compra":32.0,"rsi_por_moneda":{},"sl_pct":-1.0,"rsi_venta":68.0,"filtro_ema":"ON"}
def load():
 try:
  if os.path.exists(FILE):
   j=json.load(open(FILE)); data.update(j)
   if data["capital_actual"]<10: data["capital_actual"]=500.0
 except: pass
def save():
 try: json.dump(data,open(FILE,'w'))
 except: pass
load()
def P(s):
 for u in [f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT",f"https://api.binance.com/api/v3/ticker/price?symbol={s}USDT"]:
  try:
   j=requests.get(u,timeout=4).json()
   if 'price' in j: return float(j['price'])
  except: continue
 return 0
def C(s):
 for u in [f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=100",f"https://api.binance.com/api/v3/klines?symbol={s}USDT&interval=1h&limit=100"]:
  try:
   r=requests.get(u,timeout=5).json()
   if isinstance(r,list) and len(r)>20: return [float(x[4]) for x in r]
  except: continue
 return []
def RSI(cl,p=14):
 if len(cl)<p+1: return 50.0
 g=l=0
 for i in range(1,p+1):
  d=cl[-i]-cl[-i-1]
  if d>0: g+=d
  else: l+=-d
 if l==0: return 70
 if g==0: return 30
 rs=g/l if l!=0 else 0
 return 100-(100/(1+rs))
def EMA(cl,p=20):
 if len(cl)<p: return cl[-1] if cl else 0
 k=2/(p+1); e=cl[0]
 for c in cl[1:]: e=c*k+e*(1-k)
 return e
def ANALIZA(sym):
 closes=C(sym)
 if len(closes)<30:
  return False,50.0,P(sym),f"Sin datos ({len(closes)})",data.get("rsi_por_moneda",{}).get(sym,data["rsi_compra"]),"",False
 r_now=RSI(closes); r_prev=RSI(closes[:-1]); price=closes[-1]; ema20=EMA(closes,20)
 limite=data.get("rsi_por_moneda",{}).get(sym,data["rsi_compra"])
 p_ok=price>ema20*0.995
 vol=sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(-30,0))/30*100 if len(closes)>=30 else 0
 sug=f"{'🔥 Volátil' if vol>1.5 else '🧊 Estable'} {vol:.2f}% -> ponle {45 if vol>2.5 else 40 if vol>1.5 else '32-35'}. Ahora RSI {r_now:.0f}"
 if data["filtro_ema"]=="ON": ok=(r_now<limite) and p_ok and (r_now>r_prev or r_now<35)
 else: ok=(r_now<limite) and (r_now>r_prev or r_now<35)
 mot=f"RSI {r_now:.1f} {'✅' if r_now<limite else '❌'}<{limite:.0f}, P>EMA {'✅' if p_ok else '❌'}, Mom {r_prev:.0f}->{r_now:.0f} {'✅' if r_now>r_prev else '❌'}"
 return ok,r_now,ema20,mot,limite,sug,p_ok
def get_usdmxn():
 try: return float(requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=4).json()["rates"]["MXN"])
 except:
  try: return float(requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=USDTMXN",timeout=3).json()['price'])
  except: return 17.0
@app.route('/api/prices')
def prices():
 out={}
 for sym in data["coins"]:
  ok,rsi,ema,mot,lim,sug,p_ok=ANALIZA(sym)
  cl=C(sym); pr=cl[-1] if cl else P(sym)
  out[sym]={"price":pr,"rsi":round(rsi,1),"ok":ok,"motivo":mot,"limite":lim,"sug":sug,"p_ema_ok":p_ok}
 return jsonify(out)
@app.route('/api/state')
def state():
 usdmxn=get_usdmxn(); data["usd_mxn"]=usdmxn
 bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
 for p in data["pos"]:
  price=P(p["sym"]); p["ahora"]=price
  gan=(price-p["entry"])/p["entry"]*100 if p["entry"] else 0
  p["gan_neta_pct"]=gan-FEE*100; p["gan_neta_mxn"]=p["monto"]*gan/100-p["monto"]*FEE
  p["debe_vender"]=gan>=data["tp_bruto"] or gan<=data["sl_pct"] or RSI(C(p["sym"]))>=data["rsi_venta"]
 winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
 pct=min(100,data["gan_mes"]/META*100) if META else 0
 return jsonify({"capital":data["capital_actual"],"gan_acum":data["gan_acum_total"],"gan_mes":data["gan_mes"],"bola":bola,"bola_mxn":bola*usdmxn,"pos":data["pos"],"max_entradas":data["max_entradas"],"tp":data["tp_bruto"],"auto":data["auto"],"coins_activas":data["coins_activas"],"salidas":data["salidas"],"ganadas":data["ganadas"],"winrate":winrate,"fee_total":FEE*100,"usd_mxn":usdmxn,"meta_mxn":META*usdmxn,"pct_mes":pct,"gan_mes_mxn":data["gan_mes"]*usdmxn,"gan_acum_mxn":data["gan_acum_total"]*usdmxn,"historial":data["historial"][-50:],"capital_history":data["capital_history"][-100:],"rsi_compra":data["rsi_compra"],"sl_pct":data["sl_pct"],"rsi_venta":data["rsi_venta"],"filtro_ema":data["filtro_ema"]})
@app.route('/api/config',methods=['POST'])
def config():
 j=request.json or {}
 if "tp" in j: data["tp_bruto"]=float(j["tp"])
 if "max" in j: data["max_entradas"]=int(j["max"])
 if "sl_pct" in j: data["sl_pct"]=float(j["sl_pct"])
 if "rsi_venta" in j: data["rsi_venta"]=float(j["rsi_venta"])
 if "filtro_ema" in j: data["filtro_ema"]=j["filtro_ema"]
 if "toggle_coin" in j: data["coins_activas"][j["toggle_coin"]]=not data["coins_activas"].get(j["toggle_coin"],True)
 if "rsi_compra" in j: data["rsi_compra"]=float(j["rsi_compra"])
 if "rsi_coin" in j: data["rsi_por_moneda"][j["rsi_coin"]["sym"]]=float(j["rsi_coin"]["val"])
 if "rsi_coin_reset" in j:
  if j["rsi_coin_reset"] in data["rsi_por_moneda"]: del data["rsi_por_moneda"][j["rsi_coin_reset"]]
 save(); return jsonify({"ok":True})
@app.route('/api/buy/<sym>',methods=['POST'])
def buy_api(sym):
 sym=sym.upper(); bola=data["capital_actual"]/data["max_entradas"]
 data["pos"].append({"sym":sym,"monto":bola,"entry":P(sym)*(1+SLIPPAGE),"ahora":P(sym),"fecha":datetime.now().strftime("%d/%m %H:%M")})
 data["capital_actual"]-=bola; data["entradas"]+=1; save(); return jsonify({"ok":True})
@app.route('/api/sell/<sym>',methods=['POST'])
def sell_api(sym):
 sym=sym.upper()
 for p in data["pos"][:]:
  if p["sym"]==sym:
   price=P(sym); gan=(price-p["entry"])/p["entry"]*100; gan_mxn=p["monto"]*gan/100-p["monto"]*FEE
   data["capital_actual"]+=p["monto"]+gan_mxn; data["gan_acum_total"]+=gan_mxn; data["gan_mes"]+=gan_mxn; data["salidas"]+=1; data["ganadas"]+=1 if gan_mxn>0 else 0
   data["historial"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"sym":sym,"entry":p["entry"],"exit":price,"monto":p["monto"],"gan_neta_pct":gan-FEE*100,"gan_neta_mxn":gan_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
   data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]})
   data["pos"].remove(p); save(); return jsonify({"ok":True})
 return jsonify({"ok":False})
@app.route('/api/toggle',methods=['POST'])
def toggle(): data["auto"]=not data["auto"]; save(); return jsonify({"auto":data["auto"]})
@app.route('/dashboard')
def dash():
 if os.path.exists('dashboard.html'): return open('dashboard.html','r',encoding='utf-8').read()
 return "Falta dashboard.html",404
@app.route('/',methods=['GET','POST'])
def root(): return "OK V3",200
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
