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

data={
    "base_inicial":0.0,"capital_actual":500.0,"gan_acum_total":0.0,"gan_mes":0.0,"gan_hoy":0.0,
    "pos":[],"historial":[],"capital_history":[{"t":int(time.time()*1000),"cap":500.0}],
    "coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas":{"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas":10,"tp_bruto":0.3,"auto":True,"alert_users":[],
    "entradas":0,"salidas":0,"ganadas":0,"perdidas":0,"usd_mxn":16.96,
    "rsi_compra":35.0,"rsi_por_moneda":{},
    "sl_pct":-2.0,"rsi_venta":72.0,"filtro_ema":"ON"
}

def load():
    if os.path.exists(FILE):
        try: data.update(json.load(open(FILE)))
        except: pass
def save():
    try: json.dump(data, open(FILE,'w'))
    except: pass
load()

def P(s):
    for url in [f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT", f"https://api.binance.com/api/v3/ticker/price?symbol={s}USDT"]:
        try:
            j=requests.get(url,timeout=4).json()
            if 'price' in j: return float(j['price'])
        except: continue
    return 0

def C(s):
    for url in [f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=100", f"https://api.binance.com/api/v3/klines?symbol={s}USDT&interval=1h&limit=100"]:
        try:
            r=requests.get(url,timeout=5).json()
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
    if l==0: return 70.0
    if g==0: return 30.0
    rs=g/l
    return 100-(100/(1+rs))

def EMA(cl,p=20):
    if len(cl)<p: return cl[-1] if cl else 0
    k=2/(p+1); e=cl[0]
    for c in cl[1:]: e=c*k+e*(1-k)
    return e

def RSI_HIST(cl):
    if len(cl)<30: return 50.0,50.0
    return RSI(cl[:-1]), RSI(cl)

def SUGERIR_RSI(sym, closes):
    if len(closes)<30: return 35, "Sin datos"
    vols=sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(-30,0))/30*100
    rsi_now=RSI(closes)
    if vols>2.5: return 45, f"Volatil {vols:.2f}% ponle 45 RSI {rsi_now:.0f}"
    elif vols>1.5: return 40, f"Volatil {vols:.2f}% ponle 40 RSI {rsi_now:.0f}"
    else: return 33, f"Estable {vols:.2f}% ponle 32-35 RSI {rsi_now:.0f}"

def CEREBRO(sym, closes):
    if len(closes)<30: return "Sin datos"
    rsi=RSI(closes)
    vols=sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(-30,0))/30*100
    if vols>3.0: return f"APAGA {sym} vol {vols:.1f}% extrema"
    if rsi>68: return f"ESPERA {sym} RSI {rsi:.0f} alto"
    if rsi<35: return f"PRENDE {sym} RSI {rsi:.0f} ganga"
    return f"OK {sym} estable"

def ANALIZA(sym):
    closes=C(sym)
    if len(closes)<30:
        pr=P(sym)
        return False,50.0,pr,f"Sin datos ({len(closes)})",35,"","Sin datos"
    r_prev,r_now=RSI_HIST(closes)
    ema20=EMA(closes,20)
    price=closes[-1]
    limite=data.get("rsi_por_moneda",{}).get(sym,data.get("rsi_compra",35.0))
    if data.get("filtro_ema","ON")=="ON":
        ok=(r_now<limite) and (price>ema20*0.995) and (r_now>r_prev)
    else:
        ok=(r_now<limite) and (r_now>r_prev)
    mot=f"RSI {r_now:.1f} {'ok' if r_now<limite else 'no'}<{limite:.0f} Mom {r_prev:.0f}->{r_now:.0f}"
    sv,st=SUGERIR_RSI(sym,closes)
    cerebro=CEREBRO(sym,closes)
    return ok,r_now,ema20,mot,limite,st,cerebro

def get_usdmxn():
    try:
        r=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=4).json()
        return float(r["rates"]["MXN"])
    except:
        try: return float(requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=USDTMXN",timeout=3).json()['price'])
        except: return 17.0

def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"VER DASHBOARD","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.80 SIM REAL + AUTO BUY",200

@app.route('/api/prices')
def prices():
    out={}
    for sym in data["coins"]:
        ok,rsi,ema,mot,limite,sug,cerebro=ANALIZA(sym)
        closes=C(sym)
        price=closes[-1] if closes else P(sym)
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"action":"COMPRAR" if ok else "VENDER" if rsi>data["rsi_venta"] else "SOSTENER","ok":ok,"motivo":mot,"activa":data["coins_activas"].get(sym,True),"limite":limite,"sug":sug,"cerebro":cerebro}
    return jsonify(out)

@app.route('/api/state')
def state():
    usdmxn=get_usdmxn()
    data["usd_mxn"]=usdmxn
    bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
    for p in data["pos"]:
        price=P(p["sym"])
        p["ahora"]=price
        gan_bruta_pct=((price-p["entry"])/p["entry"]*100) if p["entry"] else 0
        gan_bruta_mxn=p["monto"]*gan_bruta_pct/100
        com=p["monto"]*FEE_ENTRADA+(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
        p["gan_bruta_pct"]=gan_bruta_pct
        p["gan_neta_pct"]=gan_bruta_pct-FEE_TOTAL*100
        p["gan_bruta_mxn"]=gan_bruta_mxn
        p["gan_neta_mxn"]=gan_bruta_mxn-com
        p["rsi_now"]=RSI(C(p["sym"])) if C(p["sym"]) else 50
        p["debe_vender"]=gan_bruta_pct>=data["tp_bruto"] or p["rsi_now"]>=data["rsi_venta"] or gan_bruta_pct<=data["sl_pct"]
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
    pct_mes=min(100,(data["gan_mes"]/META_MES_USD*100)) if META_MES_USD else 0
    return jsonify({"capital":data["capital_actual"],"gan_acum":data["gan_acum_total"],"gan_mes":data["gan_mes"],"bola":bola,"bola_mxn":bola*usdmxn,"pos":data["pos"],"max_entradas":data["max_entradas"],"tp":data["tp_bruto"],"sl_pct":data["sl_pct"],"rsi_venta":data["rsi_venta"],"filtro_ema":data["filtro_ema"],"auto":data["auto"],"coins_activas":data["coins_activas"],"entradas":data["entradas"],"salidas":data["salidas"],"ganadas":data["ganadas"],"perdidas":data["perdidas"],"winrate":winrate,"fee_total":FEE_TOTAL*100,"usd_mxn":usdmxn,"meta_mxn":META_MES_USD*usdmxn,"pct_mes":pct_mes,"gan_mes_mxn":data["gan_mes"]*usdmxn,"gan_acum_mxn":data["gan_acum_total"]*usdmxn,"historial":data["historial"][-50:],"capital_history":data["capital_history"][-100:],"rsi_compra":data.get("rsi_compra",35),"rsi_por_moneda":data.get("rsi_por_moneda",{})})

@app.route('/api/config', methods=['POST'])
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
    save()
    return jsonify({"ok":True})

@app.route('/api/buy/<sym>', methods=['POST'])
def buy_api(sym):
    sym=sym.upper()
    if len(data["pos"])>=data["max_entradas"] or any(p['sym']==sym for p in data["pos"]): return jsonify({"ok":False})
    bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
    if bola<5: return jsonify({"ok":False})
    price=P(sym)
    if price==0: return jsonify({"ok":False})
    ok,rsi,ema,mot,lim,sug,cerebro=ANALIZA(sym)
    entry_real=price*(1+SLIPPAGE)
    data["pos"].append({"sym":sym,"monto":bola,"entry":entry_real,"ahora":price,"rsi_entry":rsi,"motivo":mot,"fecha":datetime.now().strftime("%d/%m %H:%M")})
    data["capital_actual"]-=bola
    data["entradas"]+=1
    save()
    return jsonify({"ok":True})

@app.route('/api/sell/<sym>', methods=['POST'])
def sell_api(sym):
    sym=sym.upper()
    for p in data["pos"][:]:
        if p["sym"]==sym:
            price=P(sym)
            gan_bruta_pct=(price-p["entry"])/p["entry"]*100
            gan_bruta_mxn=p["monto"]*gan_bruta_pct/100
            com_e=p["monto"]*FEE_ENTRADA
            com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
            gan_neta_mxn=gan_bruta_mxn-com_e-com_s
            gan_neta_pct=gan_bruta_pct-FEE_TOTAL*100
            data["capital_actual"]+=p["monto"]+gan_neta_mxn
            data["gan_acum_total"]+=gan_neta_mxn
            data["gan_mes"]+=gan_neta_mxn
            data["gan_hoy"]+=gan_neta_mxn
            data["salidas"]+=1
            if gan_neta_mxn>0: data["ganadas"]+=1
            else: data["perdidas"]+=1
            data["historial"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"sym":sym,"entry":p["entry"],"exit":price,"monto":p["monto"],"gan_neta_pct":gan_neta_pct,"gan_neta_mxn":gan_neta_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
            data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]})
            data["pos"].remove(p)
            save()
            return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    data["auto"]=not data["auto"]
    save()
    return jsonify({"auto":data["auto"]})

@app.route('/dashboard')
def dash():
    html = '''
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:8px}.header{border:2px solid #ffcc00;border-radius:22px;padding:16px;background:#111;text-align:center}.circs{display:flex;justify-content:center;gap:20px;flex-wrap:wrap;margin-top:14px}.circ-box{position:relative;width:175px;height:175px}.circ-bg{fill:none;stroke:#222;stroke-width:11}.circ-progress{fill:none;stroke:#ffcc00;stroke-width:11;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}.circ-progress.green{stroke:#00ff88}.circ-inner{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;width:130px}.small{font-size:11px;color:#888}.big-mxn{font-size:
