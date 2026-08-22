import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
FILE="bot_data.json"
BACKUP_FILE="/tmp/backup_bot_data.json"
FEE_ENTRADA=0.001; FEE_SALIDA=0.001; FEE_TOTAL=0.002
SLIPPAGE=0.0005
META_MES_USD=500.0

# --- TU ENTRADA VIEJA RECUPERADA ---
data={
    "base_inicial": 0.0,"capital_actual": 450.0,"gan_acum_total": 0.0,"gan_mes": 0.0,"gan_hoy": 0.0,
    "pos": [{"sym":"ETH","monto":50.0,"entry":2428.64,"ahora":2426.98,"rsi_entry":27.0,"motivo":"RECUPERADO","fecha":"22/05 12:08"}],
    "historial": [],"capital_history": [{"t": int(time.time()*1000), "cap": 500.0}],
    "coins": ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas": 10,"tp_bruto": 0.3,"auto": True,"alert_users": [],
    "entradas": 1, "salidas": 0, "ganadas": 0, "perdidas": 0,"last_alert": {}, "usd_mxn": 16.96,
    "rsi_compra": 35.0,"rsi_por_moneda": {},
    "sl_pct": -2.0,"rsi_venta": 70.0,"filtro_ema": "OFF"
}

def load():
    global data
    for f in [FILE, BACKUP_FILE, "backup_"+FILE]:
        if os.path.exists(f):
            try:
                j = json.load(open(f))
                if j.get("capital_actual",0) > 0 or len(j.get("pos",[]))>0:
                    # Si el backup tiene mas trades que el actual, respetalo
                    if len(j.get("pos",[])) >= len(data["pos"]) or j.get("capital_actual",500)!= 500:
                        data.update(j)
                    print(f"✅ RECUPERADO de {f} -> ${data['capital_actual']} {len(data['pos'])} pos")
                    return
            except: continue
    print("⚠️ Iniciando con tu ETH recuperado")
    save()

def save():
    try:
        json.dump(data, open(FILE,'w'))
        json.dump(data, open(BACKUP_FILE,'w'))
        json.dump(data, open("backup_"+FILE,'w'))
    except: pass

load()

def P(s):
    for url in [f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT",f"https://api.binance.com/api/v3/ticker/price?symbol={s}USDT"]:
        try:
            j=requests.get(url,timeout=4).json()
            if 'price' in j: return float(j['price'])
        except: continue
    return 0
def C(s):
  for url in [f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=100",f"https://api.binance.com/api/v3/klines?symbol={s}USDT&interval=1h&limit=100"]:
    try:
      r = requests.get(url, timeout=5).json()
      if isinstance(r, list) and len(r)>20: return [float(x[4]) for x in r]
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
    return 100-(100/(1+g/l))
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
    vols = sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(-30,0))/30*100
    rsi_now = RSI(closes)
    if vols > 2.5: return 45, f"🔥 Muy volátil {vols:.2f}% -> ponle 45. Ahora RSI {rsi_now:.0f}"
    elif vols > 1.5: return 40, f"⚡ Volátil {vols:.2f}% -> ponle 40. Ahora RSI {rsi_now:.0f}"
    else: return 33, f"🧊 Estable {vols:.2f}% -> ponle 32-35. Ahora RSI {rsi_now:.0f}"

def ANALIZA(sym):
    closes=C(sym)
    if len(closes)<30:
        pr=P(sym); return False, 50.0, pr, f"Sin datos ({len(closes)})", 35, "", False
    r_prev, r_now = RSI_HIST(closes)
    ema20 = EMA(closes,20); price=closes[-1]
    limite = data.get("rsi_por_moneda",{}).get(sym, data.get("rsi_compra",35.0))
    p_ema_ok = price > ema20*0.995
    # SIN MOM - compra en barato directo
    if data.get("filtro_ema","ON") == "ON": ok = (r_now < limite) and p_ema_ok
    else: ok = (r_now < limite)
    mot = f"RSI {r_now:.1f} {'✅' if r_now<limite else '❌'}<{limite:.0f}, P>EMA {'✅' if p_ema_ok else '❌'} {'' if data.get('filtro_ema')=='ON' else '(OFF)'}"
    sug_val, sug_txt = SUGERIR_RSI(sym, closes)
    return ok, r_now, ema20, mot, limite, sug_txt, p_ema_ok

def get_usdmxn():
    try: return float(requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=4).json()["rates"]["MXN"])
    except:
        try: return float(requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=USDTMXN",timeout=3).json()['price'])
        except: return 17.0
def tg(uid, txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN",""); base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 VER DASHBOARD","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.90 ANTI-BORRADO + ETH RECUPERADO",200

@app.route('/api/prices')
def prices():
    out={}
    for sym in data["coins"]:
        ok,rsi,ema,mot,limite,sug,p_ema_ok = ANALIZA(sym)
        closes=C(sym); price=closes[-1] if closes else P(sym)
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"action":"COMPRAR" if ok else "VENDER" if rsi>data.get("rsi_venta",72) else "SOSTENER","ok":ok,"motivo":mot,"activa":data["coins_activas"].get(sym,True),"limite":limite,"sug":sug, "p_ema_ok": p_ema_ok}
    return jsonify(out)

@app.route('/api/state')
def state():
    usdmxn=get_usdmxn(); data["usd_mxn"]=usdmxn
    bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
    for p in data["pos"]:
        price=P(p["sym"]); p["ahora"]=price
        gan_bruta_pct=((price-p["entry"])/p["entry"]*100) if p["entry"] else 0
        gan_bruta_mxn=p["monto"]*gan_bruta_pct/100
        com=p["monto"]*FEE_ENTRADA+(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
        p["gan_bruta_pct"]=gan_bruta_pct; p["gan_neta_pct"]=gan_bruta_pct-FEE_TOTAL*100
        p["gan_bruta_mxn"]=gan_bruta_mxn; p["gan_neta_mxn"]=gan_bruta_mxn-com
        p["comision_total_mxn"]=com; p["rsi_now"]=RSI(C(p["sym"])) if C(p["sym"]) else 50
        p["debe_vender"]=gan_bruta_pct>=data["tp_bruto"] or p["rsi_now"]>=data.get("rsi_venta",72) or gan_bruta_pct<=data.get("sl_pct",-2.0)
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
    pct_mes=min(100,(data["gan_mes"]/META_MES_USD*100)) if META_MES_USD else 0
    return jsonify({"base":data["base_inicial"],"capital":data["capital_actual"],"gan_acum":data["gan_acum_total"],"gan_mes":data["gan_mes"],"gan_hoy":data["gan_hoy"],"bola":bola,"bola_mxn":bola*usdmxn,"pos":data["pos"],"max_entradas":data["max_entradas"],"tp":data["tp_bruto"],"auto":data["auto"],"coins_activas":data["coins_activas"],"entradas":data["entradas"],"salidas":data["salidas"],"ganadas":data["ganadas"],"perdidas":data["perdidas"],"winrate":winrate,"fee_total":FEE_TOTAL*100,"usd_mxn":usdmxn,"meta_usd":META_MES_USD,"meta_mxn":META_MES_USD*usdmxn,"pct_mes":pct_mes,"gan_mes_mxn":data["gan_mes"]*usdmxn,"gan_acum_mxn":data["gan_acum_total"]*usdmxn,"historial": data["historial"][-50:], "capital_history": data["capital_history"][-100:],"rsi_compra": data.get("rsi_compra",35),"rsi_por_moneda": data.get("rsi_por_moneda",{}),"sl_pct": data.get("sl_pct",-2.0),"rsi_venta": data.get("rsi_venta",72.0),"filtro_ema": data.get("filtro_ema","ON")})

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
    if "rsi_coin" in j: data["rsi_coin"][j["rsi_coin"]["sym"]]=float(j["rsi_coin"]["val"])
    if "rsi_coin_reset" in j:
        if j["rsi_coin_reset"] in data["rsi_por_moneda"]: del data["rsi_por_moneda"][j["rsi_coin_reset"]]
    save(); return jsonify({"ok":True})

@app.route('/api/buy/<sym>', methods=['POST'])
def buy_api(sym):
    sym=sym.upper()
    if len(data["pos"])>=data["max_entradas"]: return jsonify({"ok":False, "msg":"max bolas"})
    if any(p['sym']==sym for p in data["pos"]): return jsonify({"ok":False, "msg":"ya en pos"})
    bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
    if bola < 5: return jsonify({"ok":False})
    price=P(sym); if price==0: return jsonify({"ok":False})
    ok,rsi,ema,mot,lim,sug,p_ok=ANALIZA(sym)
    entry_real = price * (1 + SLIPPAGE)
    data["pos"].append({"sym":sym,"monto":bola,"entry":entry_real,"ahora":price,"rsi_entry":rsi,"motivo":mot,"fecha":datetime.now().strftime("%d/%m %H:%M")})
    data["capital_actual"]-=bola; data["entradas"]+=1; save(); return jsonify({"ok":True})

@app.route('/api/sell/<sym>', methods=['POST'])
def sell_api(sym):
    sym=sym.upper()
    for p in data["pos"][:]:
        if p["sym"]==sym:
            price=P(sym); gan_bruta_pct=(price-p["entry"])/p["entry"]*100; gan_bruta_mxn=p["monto"]*gan_bruta_pct/100
            com_e=p["monto"]*FEE_ENTRADA; com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA; gan_neta_mxn=gan_bruta_mxn-com_e-com_s; gan_neta_pct=gan_bruta_pct-FEE_TOTAL*100
            data["capital_actual"]+=p["monto"]+gan_neta_mxn; data["gan_acum_total"]+=gan_neta_mxn; data["gan_mes"]+=gan_neta_mxn; data["gan_hoy"]+=gan_neta_mxn; data["salidas"]+=1
            if gan_neta_mxn>0: data["ganadas"]+=1
            else: data["perdidas"]+=1
            data["historial"].append({"fecha": datetime.now().strftime("%d/%m %H:%M"),"sym": sym,"entry": p["entry"],"exit": price,"monto": p["monto"],"gan_neta_pct": gan_neta_pct,"gan_neta_mxn": gan_neta_mxn,"capital_despues": data["capital_actual"],"bola_despues": data["capital_actual"]/data["max_entradas"]})
            data["capital_history"].append({"t": int(time.time()*1000), "cap": data["capital_actual"]})
            data["pos"].remove(p); save(); return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    data["auto"]=not data["auto"]; save(); return jsonify({"auto":data["auto"]})
@app.route('/api/backup')
def backup(): return jsonify(data)
@app.route('/api/restore', methods=['POST'])
def restore():
    j=request.json
    if j and "capital_actual" in j: data.update(j); save(); return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:8px}.header{border:2px solid #ffcc00;border-radius:22px;padding:16px;background:#111;text-align:center}.card{background:#151515;border:2px solid #333;border-radius:14px;padding:10px}.card.signal-buy{border-color:#00ff88;box-shadow:0 0 10px #00ff88}.btn{padding:10px;border-radius:8px;border:none;font-weight:bold;margin:3px;font-size:11px;width:31%}.btn-g{background:#00ff88;color:#000}.btn-r{background:#ff4444;color:#fff}.btn-y{background:#ffcc00;color:#000}.badge{font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold;display:inline-block}.badge-buy{background:#00ff88;color:#000}.badge-sell{background:#ff4444;color:#fff}.badge-wait{background:#333;color:#888}.badge-on{background:#00ff88;color:#000;cursor:pointer}.badge-off{background:#ff4444;color:#fff;cursor:pointer}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.config{background:#151515;padding:10px;border-radius:12px;margin:10px 0;display:flex;gap:10px;flex-wrap:wrap;justify-content:space-between;align-items:center}.sug-box{background:#1a1a00;border:1px solid #ffcc00;border-radius:12px;padding:10px;margin:10px 0;font-size:11px}table{width:100%;border-collapse:collapse;background:#151515;border-radius:12px;margin-top:10px;font-size:10px}th,td{padding:6px;border-bottom:1px solid #333;text-align:center}.neto{color:#00ff88;font-weight:bold}.perdida{color:#ff4444}.chart-box{background:#151515;border-radius:12px;padding:10px;margin-top:12px}</style></head><body>
<div class=header><b style=font-size:20px;color:#ffcc00>💰 MÁQUINA BOLA DE NIEVE - REAL FEES</b><div style=margin-top:8px;font-size:11px;background:#000;border-radius:8px;padding:6px;display:flex;justify-content:space-between"><span>USD/MXN $<span id=usdmxn>0</span></span><span id=cuantas>0/0</span><span>Win <span id=winrate>0%</span></span></div><div id=infoBola style=margin-top:8px></div></div>
<div class=config><div>💰 Cierre: <select id=tp onchange="setTP()"><option value=0.3>0.1% NETO (0.3% Bruto)</option><option value=0.4>0.2% NETO</option><option value=0.5>0.3% NETO</option><option value=0.6>0.4% NETO</option></select></div><div>🛑 SL: <select id=sl onchange="setSL()"><option value=-1.0>-1%</option><option value=-1.5>-1.5%</option><option value=-2.0>-2%</option><option value=-3.0>-3%</option></select></div><div>📤 RSI Venta: <select id=rsiV onchange="setRsiV()"><option value=68>68</option><option value=70>70</option><option value=72>72</option><option value=75>75</option></select></div><div>📈 P>EMA: <select id=emaF onchange="setEmaF()"><option value="ON">ON Seguro</option><option value="OFF">OFF Agresivo</option></select></div><div>📉 RSI Compra Global: <select id=rsiGlobal onchange="setRsiGlobal()"><option value=32>32</option><option value=35>35</option><option value=38>38</option><option value=40>40</option><option value=45>45</option><option value=50>50</option></select></div><div>🎯 Bolas: <select id=maxEnt onchange="setMax()"><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option></select></div><div><button class=btn btn-g id=autoBtn onclick="toggleAuto()" style=width:auto>...</button></div></div>
<div class=sug-box id=sugBox style="border:2px solid #00ff88"><b style=color:#00ff88>🤖 CEREBRO - QUÉ ES LO MEJOR HOY</b><div id=sugList style="margin-top:6px">Cargando...</div></div>
<div id=grid class=grid></div>
<table><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Neta</th><th>Acción</th></tr></thead><tbody id=tbody></tbody></table>
<script>
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json();
 let r2=await fetch('/api/state'); let s=await r2.json();
 document.getElementById('usdmxn').innerText=s.usd_mxn.toFixed(2);
 document.getElementById('cuantas').innerText=s.ganadas+'/'+s.salidas;
 document.getElementById('winrate').innerText=s.winrate.toFixed(0)+'%';
 document.getElementById('infoBola').innerHTML='🎯 BOLA: $'+s.bola.toFixed(2)+' USD ('+s.max_entradas+' bolas) = $'+s.capital.toFixed(2);
 document.getElementById('tp').value=s.tp; document.getElementById('maxEnt').value=s.max_entradas; document.getElementById('rsiGlobal').value=s.rsi_compra; document.getElementById('sl').value=s.sl_pct; document.getElementById('rsiV').value=s.rsi_venta; document.getElementById('emaF').value=s.filtro_ema;
 document.getElementById('autoBtn').innerText=s.auto?'AUTO ON 🤖':'AUTO OFF 🔔';
 let caidas = 0; for(let k in d){ if(!d[k].p_ema_ok) caidas++; }
 let cerebro = caidas>=6? `📉 CAIDA FUERTE ${caidas}/${Object.keys(d).length} -> LO MEJOR: SL -2% o -3% | RSI Venta 70 | EMA OFF` : caidas>=3? `⚠️ LATERAL ${caidas} -> SL -2% | Venta 72 | EMA ON` : `📈 ALCISTA -> SL -1.5% | Venta 75 | EMA ON`;
 document.getElementById('sugList').innerHTML = cerebro + '<hr>' + Object.keys(d).map(sym=>`<div><b>${sym}</b>: ${d[sym].sug}</div>`).join('');
 let h=''; for(let sym in d){
  let activa=s.coins_activas[sym]; let inPos=s.pos.find(p=>p.sym==sym); let hasBuy=d[sym].ok&&!inPos; let hasSell=inPos&&inPos.debe_vender;
  let cls='card'; if(!activa) cls+=' off'; else if(hasBuy) cls+=' signal-buy';
  let estadoBadge=hasBuy?'<span class=badge badge-buy>COMPRA</span>':hasSell?'<span class=badge badge-sell>VENDE</span>':'<span class=badge badge-wait>ESPERA</span>';
  let onBadge=activa?`<span class="badge badge-on" onclick="toggleCoin('${sym}')">ON 🟢</span>`:`<span class="badge badge-off" onclick="toggleCoin('${sym}')">OFF 🔴</span>`;
  h+=`<div class="${cls}"><div style=display:flex;justify-content:space-between><b>${sym} $${d[sym].price.toFixed(2)}</b>${onBadge}</div><div style=margin:4px 0>${estadoBadge}</div><small>RSI ${d[sym].rsi} (lim ${d[sym].limite})</small><br><small style=font-size:9px>${d[sym].motivo}</small><br><div style=margin-top:6px><button class=btn btn-g onclick="buy('${sym}')">COMPRAR</button><button class=btn btn-r onclick="sell('${sym}')">VENDER</button></div></div>`;} document.getElementById('grid').innerHTML=h;
 let tb=''; for(let p of s.pos){tb+=`<tr><td>${p.sym}</td><td>${p.entry.toFixed(2)}</td><td>${p.ahora.toFixed(2)}</td><td class=neto>${p.gan_neta_pct.toFixed(2)}% $${p.gan_neta_mxn.toFixed(2)}</td><td>Robot</td></tr>`;}
 document.getElementById('tbody').innerHTML=tb||'<tr><td colspan=5 style=text-align:center;color:#666>Sin posiciones</td></tr>';
}
async function toggleCoin(sym){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({toggle_coin:sym})});load();}
async function setRsiGlobal(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rsi_compra:parseFloat(document.getElementById('rsiGlobal').value)})});load();}
async function buy(s){await fetch('/api/buy/'+s,{method:'POST'});load();}
async function sell(s){await fetch('/api/sell/'+s,{method:'POST'});load();}
async function setTP(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tp:parseFloat(document.getElementById('tp').value)})});}
async function setSL(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sl_pct:parseFloat(document.getElementById('sl').value)})});}
async function setRsiV(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rsi_venta:parseFloat(document.getElementById('rsiV').value)})});}
async function setEmaF(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filtro_ema:document.getElementById('emaF').value})});}
async function setMax(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({max:parseInt(document.getElementById('maxEnt').value)})});}
async function toggleAuto(){await fetch('/api/toggle',{method:'POST'});load();}
load(); setInterval(load,8000);
</script></body></html>"""

@app.route('/webhook', methods=['POST','GET'])
def webhook():
    if request.method=='GET': return "ok",200
    d=request.json or {}
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(5)
    while True:
        try:
            for p in list(data["pos"]):
                price_p=P(p['sym']);
                if price_p==0: continue
                gan_bruta
