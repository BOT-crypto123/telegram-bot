import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
FILE="bot_data.json"
FEE_ENTRADA=0.001; FEE_SALIDA=0.001; FEE_TOTAL=0.002; SLIPPAGE=0.0005; META_MES_USD=500.0
data={"base_inicial":0.0,"capital_actual":500.0,"gan_acum_total":0.0,"gan_mes":0.0,"gan_hoy":0.0,"pos":[],"historial":[],"capital_history":[{"t":int(time.time()*1000),"cap":500.0}],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"coins_activas":{"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},"max_entradas":10,"tp_bruto":0.3,"auto":True,"alert_users":[],"entradas":0,"salidas":0,"ganadas":0,"perdidas":0,"usd_mxn":16.96,"rsi_compra":35.0,"rsi_por_moneda":{},"sl_pct":-2.0,"rsi_venta":72.0,"filtro_ema":"ON"}
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
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=100",timeout=5).json()
        if isinstance(r,list) and len(r)>20: return [float(x[4]) for x in r]
    except: pass
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
    vols=sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(-30,0))/30*100
    if vols>2.5: return 45, f"Volatil {vols:.1f}% ponle 45"
    elif vols>1.5: return 40, f"Volatil {vols:.1f}% ponle 40"
    else: return 33, f"Estable {vols:.1f}% ponle 32-35"
def CEREBRO(sym, closes):
    if len(closes)<30: return "Sin datos"
    rsi=RSI(closes)
    vols=sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(-30,0))/30*100
    if vols>3.0: return f"APAGA {sym} vol {vols:.1f}%"
    if rsi>68: return f"ESPERA {sym} RSI {rsi:.0f}"
    if rsi<35: return f"PRENDE {sym} RSI {rsi:.0f}"
    return f"OK {sym}"
def ANALIZA(sym):
    closes=C(sym)
    if len(closes)<30:
        pr=P(sym)
        return False,50.0,pr,"Sin datos",35,"","Sin datos"
    r_prev,r_now=RSI_HIST(closes); ema20=EMA(closes,20); price=closes[-1]
    limite=data.get("rsi_por_moneda",{}).get(sym,data.get("rsi_compra",35.0))
    if data.get("filtro_ema","ON")=="ON": ok=(r_now<limite) and (price>ema20*0.995) and (r_now>r_prev)
    else: ok=(r_now<limite) and (r_now>r_prev)
    mot=f"RSI {r_now:.1f} <{limite:.0f} Mom {r_prev:.0f}->{r_now:.0f}"
    sv,st=SUGERIR_RSI(sym,closes); cerebro=CEREBRO(sym,closes)
    return ok,r_now,ema20,mot,limite,st,cerebro
def get_usdmxn():
    try:
        r=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=4).json()
        return float(r["rates"]["MXN"])
    except:
        try: return float(requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=USDTMXN",timeout=3).json()['price'])
        except: return 17.0
@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.81 FIX DASHBOARD",200
@app.route('/api/prices')
def prices():
    out={}
    for sym in data["coins"]:
        ok,rsi,ema,mot,limite,sug,cerebro=ANALIZA(sym)
        closes=C(sym); price=closes[-1] if closes else P(sym)
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"action":"COMPRAR" if ok else "SOSTENER","ok":ok,"motivo":mot,"activa":data["coins_activas"].get(sym,True),"limite":limite,"sug":sug,"cerebro":cerebro}
    return jsonify(out)
@app.route('/api/state')
def state():
    usdmxn=get_usdmxn(); data["usd_mxn"]=usdmxn; bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
    for p in data["pos"]:
        price=P(p["sym"]); p["ahora"]=price; gan_bruta_pct=((price-p["entry"])/p["entry"]*100) if p["entry"] else 0; gan_bruta_mxn=p["monto"]*gan_bruta_pct/100; com=p["monto"]*FEE_ENTRADA+(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
        p["gan_bruta_pct"]=gan_bruta_pct; p["gan_neta_pct"]=gan_bruta_pct-FEE_TOTAL*100; p["gan_neta_mxn"]=gan_bruta_mxn-com; p["rsi_now"]=RSI(C(p["sym"])) if C(p["sym"]) else 50
        p["debe_vender"]=gan_bruta_pct>=data["tp_bruto"] or p["rsi_now"]>=data["rsi_venta"] or gan_bruta_pct<=data["sl_pct"]
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0; pct_mes=min(100,(data["gan_mes"]/META_MES_USD*100)) if META_MES_USD else 0
    return jsonify({"capital":data["capital_actual"],"gan_acum":data["gan_acum_total"],"gan_mes":data["gan_mes"],"bola":bola,"bola_mxn":bola*usdmxn,"pos":data["pos"],"max_entradas":data["max_entradas"],"tp":data["tp_bruto"],"sl_pct":data["sl_pct"],"rsi_venta":data["rsi_venta"],"filtro_ema":data["filtro_ema"],"auto":data["auto"],"coins_activas":data["coins_activas"],"salidas":data["salidas"],"ganadas":data["ganadas"],"winrate":winrate,"fee_total":FEE_TOTAL*100,"usd_mxn":usdmxn,"meta_mxn":META_MES_USD*usdmxn,"pct_mes":pct_mes,"gan_mes_mxn":data["gan_mes"]*usdmxn,"gan_acum_mxn":data["gan_acum_total"]*usdmxn,"historial":data["historial"][-50:],"capital_history":data["capital_history"][-100:],"rsi_compra":data.get("rsi_compra",35),"rsi_por_moneda":data.get("rsi_por_moneda",{})})
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
    sym=sym.upper(); bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0; price=P(sym)
    if price==0 or bola<5: return jsonify({"ok":False})
    ok,rsi,ema,mot,lim,sug,cerebro=ANALIZA(sym); entry_real=price*(1+SLIPPAGE)
    data["pos"].append({"sym":sym,"monto":bola,"entry":entry_real,"ahora":price,"rsi_entry":rsi,"motivo":mot,"fecha":datetime.now().strftime("%d/%m %H:%M")})
    data["capital_actual"]-=bola; data["entradas"]+=1; save(); return jsonify({"ok":True})
@app.route('/api/sell/<sym>', methods=['POST'])
def sell_api(sym):
    sym=sym.upper()
    for p in data["pos"][:]:
        if p["sym"]==sym:
            price=P(sym); gan_bruta_pct=(price-p["entry"])/p["entry"]*100; gan_bruta_mxn=p["monto"]*gan_bruta_pct/100; com_e=p["monto"]*FEE_ENTRADA; com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA; gan_neta_mxn=gan_bruta_mxn-com_e-com_s
            data["capital_actual"]+=p["monto"]+gan_neta_mxn; data["gan_acum_total"]+=gan_neta_mxn; data["gan_mes"]+=gan_neta_mxn; data["salidas"]+=1
            if gan_neta_mxn>0: data["ganadas"]+=1
            else: data["perdidas"]+=1
            data["historial"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"sym":sym,"entry":p["entry"],"exit":price,"monto":p["monto"],"gan_neta_pct":gan_bruta_pct-FEE_TOTAL*100,"gan_neta_mxn":gan_neta_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
            data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]}); data["pos"].remove(p); save(); return jsonify({"ok":True})
    return jsonify({"ok":False})
@app.route('/api/toggle', methods=['POST'])
def toggle(): data["auto"]=not data["auto"]; save(); return jsonify({"auto":data["auto"]})
@app.route('/webhook', methods=['POST','GET'])
def webhook():
    if request.method=='GET': return "ok",200
    d=request.json or {}
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        save()
    return {"ok":True}

DASH_HTML="""
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:8px}
.header{border:2px solid #ffcc00;border-radius:22px;padding:16px;background:#111;text-align:center}
.circs{display:flex;justify-content:center;gap:20px;flex-wrap:wrap;margin-top:14px}
.circ-box{position:relative;width:175px;height:175px}.circ-bg{fill:none;stroke:#222;stroke-width:11}
.circ-progress{fill:none;stroke:#ffcc00;stroke-width:11;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}
.circ-progress.green{stroke:#00ff88}.circ-inner{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;width:130px}
.small{font-size:11px;color:#888}.big-mxn{font-size:30px;font-weight:bold;color:#00ff88}
.big-usd{font-size:14px;color:#ffcc00;font-weight:bold}
.card{background:#151515;border:2px solid #333;border-radius:14px;padding:10px}
.card.off{opacity:0.35;border-color:#ff4444}.card.signal-buy{border-color:#00ff88;box-shadow:0 0 10px #00ff88}
.btn{padding:10px;border-radius:8px;border:none;font-weight:bold;margin:3px;font-size:11px;width:31%}
.btn:disabled{opacity:0.2}.btn-g{background:#00ff88;color:#000}.btn-r{background:#ff4444;color:#fff}.btn-y{background:#ffcc00;color:#000}
.badge{font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold;display:inline-block}
.badge-buy{background:#00ff88;color:#000}.badge-sell{background:#ff4444;color:#fff}.badge-wait{background:#333;color:#888}
.badge-on{background:#00ff88;color:#000;cursor:pointer}.badge-off{background:#ff4444;color:#fff;cursor:pointer}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.config{background:#151515;padding:10px;border-radius:12px;margin:10px 0;display:flex;gap:10px;flex-wrap:wrap}
.info-bola{background:#000;border:1px solid #00ff88;border-radius:10px;padding:8px;margin-top:10px;text-align:center;font-size:12px}
.sug-box{background:#1a1a00;border:1px solid #ffcc00;border-radius:12px;padding:10px;margin:10px 0;font-size:11px}
table{width:100%;border-collapse:collapse;background:#151515;border-radius:12px;margin-top:10px;font-size:10px}
th,td{padding:6px;border-bottom:1px solid #333;text-align:center}.neto{color:#00ff88;font-weight:bold}.perdida{color:#ff4444}
.chart-box{background:#151515;border-radius:12px;padding:10px;margin-top:12px}
</style></head><body>
<div class=header><b style=color:#ffcc00>💰 MÁQUINA BOLA DE NIEVE - FIX 500</b>
<div class=circs><div class=circ-box><svg width=175 height=175><circle class=circ-bg cx=87.5 cy=87.5 r=72></circle><circle id=progressMes class=circ-progress cx=87.5 cy=87.5 r=72 stroke-dasharray=452 stroke-dashoffset=452></circle></svg><div class=circ-inner><div class=big-usd>500 USD</div><div class=big-mxn>$<span id=metaMxn>0</span></div><div class=small id=pctMesTxt>0%</div></div></div>
<div class=circ-box><svg width=175 height=175><circle class=circ-bg cx=87.5 cy=87.5 r=72></circle><circle id=progressAcum class="circ-progress green" cx=87.5 cy=87.5 r=72 stroke-dasharray=452 stroke-dashoffset=452></circle></svg><div class=circ-inner><div class=small>ACUM</div><div style=color:#00ccff;font-size:18px>$<span id=acumUsd>0</span></div><div class=big-mxn style=font-size:20px>$<span id=acumMxn>0</span></div></div></div></div>
<div class=info-bola id=infoBola>BOLA: $0</div>
<div style=margin-top:8px;font-size:11px;background:#000;border-radius:8px;padding:6px;display:flex;justify-content:space-between><span>USD/MXN $<span id=usdmxn>0</span></span><span id=cuantas>0/0</span><span>Win <span id=winrate>0%</span></span><span>NETO <span id=tpNeto>0%</span></span></div></div>
<div class=config>
<div>💰 Cierre: <select id=tp onchange=setTP()><option value=0.3>0.1% NETO</option><option value=0.4>0.2% NETO</option><option value=0.5>0.3% NETO</option><option value=0.6>0.4% NETO</option></select></div>
<div>📉 SL: <select id=sl onchange=setSL()><option value=-1>-1%</option><option value=-2>-2%</option><option value=-3>-3%</option><option value=-4>-4%</option></select></div>
<div>📈 Venta: <select id=rsiV onchange=setRsiV()><option value=70>70</option><option value=72>72</option><option value=75>75</option><option value=78>78</option></select></div>
<div>🧠 EMA: <select id=ema onchange=setEMA()><option value=ON>ON</option><option value=OFF>OFF</option></select></div>
<div>📉 RSI: <select id=rsiGlobal onchange=setRsiGlobal()><option value=32>32</option><option value=35>35</option><option value=38>38</option><option value=40>40</option><option value=45>45</option><option value=50>50</option></select></div>
<div>🎯 Bolas: <select id=maxEnt onchange=setMax()><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option></select></div>
<div><button class=btn btn-g id=autoBtn onclick=toggleAuto() style=width:auto>...</button></div>
</div>
<div class=sug-box><b style=color:#ffcc00>🤖 CEREBRO</b><div id=sugList>Cargando...</div></div>
<div id=grid class=grid></div>
<div class=chart-box><b style=color:#ffcc00>📈 EVOLUCIÓN</b><canvas id=capitalChart height=180></canvas></div>
<table><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Neta</th><th>Acción</th></tr></thead><tbody id=tbody></tbody></table>
<div class=chart-box><b>📋 REGISTRO</b><table><thead><tr><th>Fecha</th><th>Moneda</th><th>Monto</th><th>Entry->Exit</th><th>% Neta</th><th>Gan MXN</th><th>Capital</th><th>Bola</th></tr></thead><tbody id=histBody></tbody></table></div>
<script>
let chart;function initChart(){let ctx=document.getElementById('capitalChart').getContext('2d');chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[{label:'Capital USD',data:[],borderColor:'#00ff88',backgroundColor:'rgba(0,255,136,0.1)',fill:true,tension:0.4},{label:'Bola USD',data:[],borderColor:'#ffcc00',borderDash:[5,5],fill:false,tension:0.4}]},options:{responsive:true,plugins:{legend:{labels:{color:'#fff'}}},scales:{x:{ticks:{color:'#888'}},y:{ticks:{color:'#888'}}}});}
function setProgress(id,pct){let c=document.getElementById(id);let circ=452;let off=circ-(pct/100)*circ;c.style.strokeDashoffset=off;}
async function toggleCoin(s){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({toggle_coin:s})});load();}
async function setRsiGlobal(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rsi_compra:parseFloat(document.getElementById('rsiGlobal').value)})});load();}
async function setRsiCoin(s){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rsi_coin:{sym:s,val:parseFloat(document.getElementById('rsi_'+s).value)}})});load();}
async function resetRsiCoin(s){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rsi_coin_reset:s})});load();}
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json(); let r2=await fetch('/api/state'); let s=await r2.json();
 document.getElementById('metaMxn').innerText=s.meta_mxn.toFixed(0); document.getElementById('acumUsd').innerText=s.gan_acum.toFixed(2);
 document.getElementById('acumMxn').innerText=s.gan_acum_mxn.toFixed(0); document.getElementById('usdmxn').innerText=s.usd_mxn.toFixed(2);
 document.getElementById('pctMesTxt').innerText=s.pct_mes.toFixed(0)+'% - $'+s.gan_mes.toFixed(2); document.getElementById('cuantas').innerText=s.ganadas+'/'+s.salidas;
 document.getElementById('winrate').innerText=s.winrate.toFixed(0)+'%'; document.getElementById('tpNeto').innerText=(s.tp-s.fee_total).toFixed(1)+'%';
 document.getElementById('tp').value=s.tp; document.getElementById('sl').value=s.sl_pct; document.getElementById('rsiV').value=s.rsi_venta; document.getElementById('ema').value=s.filtro_ema;
 document.getElementById('maxEnt').value=s.max_entradas; document.getElementById('rsiGlobal').value=s.rsi_compra;
 document.getElementById('autoBtn').innerText=s.auto?'AUTO ON':'AUTO OFF'; document.getElementById('infoBola').innerHTML='BOLA: $'+s.bola.toFixed(2)+' USD / $'+s.bola_mxn.toFixed(0)+' MXN ('+s.max_entradas+' bolas)';
 setProgress('progressMes',s.pct_mes); setProgress('progressAcum',Math.min(100,s.gan_acum/500*100));
 if(chart){let labels=s.capital_history.map(h=>new Date(h.t).toLocaleTimeString()); let caps=s.capital_history.map(h=>h.cap); let bolas=caps.map(c=>c/s.max_entradas); chart.data.labels=labels; chart.data.datasets[0].data=caps; chart.data.datasets[1].data=bolas; chart.update();}
 let sugHtml=''; for(let sym in d){sugHtml+='<div style=margin:4px 0;padding:4px;background:#000;border-radius:6px><b>'+sym+'</b>: '+d[sym].sug+' <br><span style=color:#00ff88>'+d[sym].cerebro+'</span> | Limite: '+d[sym].limite+'</div>';}
 document.getElementById('sugList').innerHTML=sugHtml;
 let h=''; for(let sym in d){let activa=s.coins_activas[sym]; let inPos=s.pos.find(p=>p.sym==sym); let hasBuy=d[sym].ok&&!inPos; let hasSell=inPos&&inPos.debe_vender;
 let cls='card'; if(!activa) cls+=' off'; else if(hasBuy) cls+=' signal-buy';
 let estado=hasBuy?'<span class=badge badge-buy>COMPRA</span>':hasSell?'<span class=badge badge-sell>VENDE</span>':'<span class=badge badge-wait>ESPERA</span>';
 let onB=activa?'<span class="badge badge-on" onclick="toggleCoin(\\''+sym+'\\')">ON</span>':'<span class="badge badge-off" onclick="toggleCoin(\\''+sym+'\\')">OFF</span>';
 let rsiIn='<div><input id=rsi_'+sym+' type=number value='+d[sym].limite+' style=width:45px;background:#000;color:#fff;border:1px solid #555;border-radius:4px><button onclick="setRsiCoin(\\''+sym+'\\')" style=background:#ffcc00;border:none;border-radius:4px;padding:2px>SET</button><button onclick="resetRsiCoin(\\''+sym+'\\')" style=background:#333;color:#fff;border:none;border-radius:4px;padding:2px>RESET</button></div>';
 h+='<div class="'+cls+'"><div style=display:flex;justify-content:space-between><b>'+sym+' $'+d[sym].price.toFixed(2)+'</b>'+onB+'</div><div>'+estado+'</div><small>RSI '+d[sym].rsi+' lim '+d[sym].limite+'</small><br><small>'+d[sym].motivo+'</small><br><small style=color:#ffcc00>'+d[sym].sug+'</small><br><small style=color:#00ff88>'+d[sym].cerebro+'</small>'+rsiIn+'</div>';}
 document.getElementById('grid').innerHTML=h;
 let tb=''; for(let p of s.pos){tb+='<tr><td>'+p.sym+'</td><td>'+p.entry.toFixed(2)+'</td><td>'+p.ahora.toFixed(2)+'</td><td class=neto>'+p.gan_neta_pct.toFixed(2)+'%</td><td>'+(s.auto?'Robot':'<button onclick="sell(\\''+p.sym+'\\')">Cerrar</button>')+'</td></tr>';}
 document.getElementById('tbody').innerHTML=tb||'<tr><td colspan=5>Sin posiciones</td></tr>';
 let hist=''; for(let i=s.historial.length-1;i>=0;i--){let tr=s.historial[i]; let cls=tr.gan_neta_mxn>=0?'neto':'perdida'; hist+='<tr><td>'+tr.fecha+'</td><td>'+tr.sym+'</td><td>$'+tr.monto.toFixed(2)+'</td><td>'+tr.entry.toFixed(2)+'->'+tr.exit.toFixed(2)+'</td><td class='+cls+'>'+tr.gan_neta_pct.toFixed(2)+'%</td><td class='+cls+'>$'+tr.gan_neta_mxn.toFixed(2)+'</td><td>$'+tr.capital_despues.toFixed(2)+'</td><td>$'+tr.bola_despues.toFixed(2)+'</td></tr>';}
 document.getElementById('histBody').innerHTML=hist||'<tr><td colspan=8>Sin trades</td></tr>';
}
async function buy(s){await fetch('/api/buy/'+s,{method:'POST'});load();}
async function sell(s){await fetch('/api/sell/'+s,{method:'POST'});load();}
async function setTP(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tp:parseFloat(document.getElementById('tp').value)})});}
async function setSL(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sl_pct:parseFloat(document.getElementById('sl').value)})});}
async function setRsiV(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rsi_venta:parseFloat(document.getElementById('rsiV').value)})});}
async function setEMA(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filtro_ema:document.getElementById('ema').value})});}
async function setMax(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({max:parseInt(document.getElementById('maxEnt').value)})});}
async function toggleAuto(){await fetch('/api/toggle',{method:'POST'});load();}
initChart();load(); setInterval(load,8000);
</script></body></html>
"""

@app.route('/dashboard')
def dash():
    # primero intenta archivo externo, si no existe usa el de respaldo
    try:
        if os.path.exists('dashboard.html'):
            with open('dashboard.html','r',encoding='utf-8') as f:
                txt=f.read()
                if len(txt)>1000:
                    return txt
    except:
        pass
    return DASH_HTML

def auto_loop():
    time.sleep(5)
    while True:
        try:
            for p in list(data["pos"]):
                price_p=P(p['sym'])
                if price_p==0: continue
                gan_bruta=(price_p-p['entry'])/p['entry']*100
                if data["auto"] and (gan_bruta>=data["tp_bruto"] or gan_bruta<=data["sl_pct"] or RSI(C(p['sym']))>=data["rsi_venta"]):
                    gan_bruta_mxn=p["monto"]*gan_bruta/100; com_e=p["monto"]*FEE_ENTRADA; com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA; gan_neta_mxn=gan_bruta_mxn-com_e-com_s
                    data["capital_actual"]+=p["monto"]+gan_neta_mxn; data["gan_acum_total"]+=gan_neta_mxn; data["gan_mes"]+=gan_neta_mxn; data["salidas"]+=1
                    if gan_neta_mxn>0: data["ganadas"]+=1
                    else: data["perdidas"]+=1
                    data["historial"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"sym":p["sym"],"entry":p["entry"],"exit":price_p,"monto":p["monto"],"gan_neta_pct":gan_bruta-FEE_TOTAL*100,"gan_neta_mxn":gan_neta_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
                    data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]}); data["pos"].remove(p); save()
            if data["auto"] and len(data["pos"])<data["max_entradas"]:
                for sym in data["coins"]:
                    if not data["coins_activas"].get(sym,True): continue
                    if any(q['sym']==sym for q in data["pos"]): continue
                    ok,rsi,ema,mot,lim,sug,cerebro=ANALIZA(sym)
                    if ok:
                        bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
                        if bola<5: break
                        price=P(sym)
                        if price==0: continue
                        entry_real=price*(1+SLIPPAGE)
                        data["pos"].append({"sym":sym,"monto":bola,"entry":entry_real,"ahora":price,"rsi_entry":rsi,"motivo":mot,"fecha":datetime.now().strftime("%d/%m %H:%M")})
                        data["capital_actual"]-=bola; data["entradas"]+=1; save()
                        if len(data["pos"])>=data["max_entradas"]: break
            time.sleep(15)
        except Exception as e:
            print(f"ERROR {e}"); time.sleep(10)
threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
