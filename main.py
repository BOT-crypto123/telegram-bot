import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
FILE="bot_data.json"
FEE_ENTRADA=0.001; FEE_SALIDA=0.001; FEE_TOTAL=0.002
META_MES_USD=500.0
data={
    "base_inicial": 0.0,"capital_actual": 500.0,"gan_acum_total": 0.0,"gan_mes": 0.0,"gan_hoy": 0.0,
    "pos": [],"historial": [],"capital_history": [{"t": int(time.time()*1000), "cap": 500.0}],
    "coins": ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas": {"BTC":False,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas": 10,"tp_bruto": 0.3,"auto": True,"alert_users": [],
    "entradas": 0, "salidas": 0, "ganadas": 0, "perdidas": 0,"last_alert": {}, "usd_mxn": 16.96
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
    try: return float(requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT",timeout=3).json()['price'])
    except: return 0
def C(s):
    try: return [float(x[4]) for x in requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=80",timeout=5).json()]
    except: return []
def RSI(cl,p=14):
    if len(cl)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        d=cl[-i]-cl[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 100
    return 100-(100/(1+g/l if l else 1))
def EMA(cl,p=20):
    if len(cl)<p: return cl[-1]
    k=2/(p+1); e=cl[0]
    for c in cl[1:]: e=c*k+e*(1-k)
    return e
def RSI_HIST(cl):
    if len(cl)<16: return 50,50
    return RSI(cl[-15:-1]), RSI(cl[-14:])
def ANALIZA(sym):
    closes=C(sym)
    if len(closes)<30: return False, 50, 0, "Sin datos"
    r_prev, r_now = RSI_HIST(closes)
    ema20 = EMA(closes,20); price=closes[-1]
    ok = (r_now < 35) and (price > ema20*0.995) and (r_now > r_prev)
    mot = f"RSI {r_now:.1f} {'✅' if r_now<32 else '❌'}<35, P>EMA {'✅' if price>ema20*0.995 else '❌'}, Mom {r_prev:.0f}->{r_now:.0f} {'✅' if r_now>r_prev else '❌'}"
    return ok, r_now, ema20, mot
def get_usdmxn():
    try:
        r=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=4).json()
        return float(r["rates"]["MXN"])
    except:
        try: return float(requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=USDTMXN",timeout=3).json()['price'])
        except: return 17.0
def tg(uid, txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 VER DASHBOARD","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.73 NOTI COMBINADA",200

@app.route('/api/prices')
def prices():
    out={}
    for sym in data["coins"]:
        ok,rsi,ema,mot = ANALIZA(sym)
        closes=C(sym); price=closes[-1] if closes else P(sym)
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"action":"COMPRAR" if ok else "VENDER" if rsi>72 else "SOSTENER","ok":ok,"motivo":mot,"activa":data["coins_activas"].get(sym,True)}
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
        p["comision_total_mxn"]=com
        p["rsi_now"]=RSI(C(p["sym"])) if C(p["sym"]) else 50
        p["debe_vender"]=gan_bruta_pct>=data["tp_bruto"] or p["rsi_now"]>=72 or gan_bruta_pct<=-2
    winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
    pct_mes=min(100,(data["gan_mes"]/META_MES_USD*100)) if META_MES_USD else 0
    return jsonify({
        "base":data["base_inicial"],"capital":data["capital_actual"],"gan_acum":data["gan_acum_total"],
        "gan_mes":data["gan_mes"],"gan_hoy":data["gan_hoy"],"bola":bola,"bola_mxn":bola*usdmxn,
        "pos":data["pos"],"max_entradas":data["max_entradas"],"tp":data["tp_bruto"],
        "auto":data["auto"],"coins_activas":data["coins_activas"],
        "entradas":data["entradas"],"salidas":data["salidas"],"ganadas":data["ganadas"],"perdidas":data["perdidas"],
        "winrate":winrate,"fee_total":FEE_TOTAL*100,
        "usd_mxn":usdmxn,"meta_usd":META_MES_USD,"meta_mxn":META_MES_USD*usdmxn,"pct_mes":pct_mes,
        "gan_mes_mxn":data["gan_mes"]*usdmxn,"gan_acum_mxn":data["gan_acum_total"]*usdmxn,
        "historial": data["historial"][-50:], "capital_history": data["capital_history"][-100:]
    })

@app.route('/api/config', methods=['POST'])
def config():
    j=request.json or {}
    if "tp" in j: data["tp_bruto"]=float(j["tp"])
    if "max" in j: data["max_entradas"]=int(j["max"])
    if "toggle_coin" in j: data["coins_activas"][j["toggle_coin"]]=not data["coins_activas"].get(j["toggle_coin"],True)
    save(); return jsonify({"ok":True})

@app.route('/api/buy/<sym>', methods=['POST'])
def buy_api(sym):
    sym=sym.upper()
    if len(data["pos"])>=data["max_entradas"]: return jsonify({"ok":False})
    if any(p['sym']==sym for p in data["pos"]): return jsonify({"ok":False})
    bola=data["capital_actual"]/data["max_entradas"]; price=P(sym)
    ok,rsi,ema,mot=ANALIZA(sym)
    data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price,"rsi_entry":rsi,"motivo":mot,"fecha":datetime.now().strftime("%d/%m %H:%M")})
    data["capital_actual"]-=bola; data["entradas"]+=1; save(); return jsonify({"ok":True})

@app.route('/api/sell/<sym>', methods=['POST'])
def sell_api(sym):
    sym=sym.upper()
    for p in data["pos"][:]:
        if p["sym"]==sym:
            price=P(sym)
            gan_bruta_pct=(price-p["entry"])/p["entry"]*100
            gan_bruta_mxn=p["monto"]*gan_bruta_pct/100
            com_e=p["monto"]*FEE_ENTRADA; com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
            gan_neta_mxn=gan_bruta_mxn-com_e-com_s
            gan_neta_pct=gan_bruta_pct-FEE_TOTAL*100
            data["capital_actual"]+=p["monto"]+gan_neta_mxn
            data["gan_acum_total"]+=gan_neta_mxn; data["gan_mes"]+=gan_neta_mxn; data["gan_hoy"]+=gan_neta_mxn
            data["salidas"]+=1; data["ganadas"]+=1 if gan_neta_mxn>0 else 0; data["perdidas"]+=0 if gan_neta_mxn>0 else 1
            data["historial"].append({
                "fecha": datetime.now().strftime("%d/%m %H:%M"), "sym": sym,
                "entry": p["entry"], "exit": price, "monto": p["monto"],
                "gan_neta_pct": gan_neta_pct, "gan_neta_mxn": gan_neta_mxn,
                "capital_despues": data["capital_actual"], "bola_despues": data["capital_actual"]/data["max_entradas"]
            })
            data["capital_history"].append({"t": int(time.time()*1000), "cap": data["capital_actual"]})
            # === NOTIFICACION SOLO SI GANA ===
            if gan_neta_mxn>0:
                winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
                bola_despues=data["capital_actual"]/data["max_entradas"]
                msg=(f"✅ TRADE GANADO {sym}\n\n🟢 ENTRADA: {sym} ${p['entry']:.2f}\nBola: ${p['monto']:.2f} - RSI {p.get('rsi_entry',0):.1f}\n{p.get('fecha','')}\n\n💰 SALIDA: {sym} ${price:.2f}\n+${gan_neta_mxn:.2f} MXN ({gan_neta_pct:.2f}% NETO)\nCapital ahora: ${data['capital_actual']:.2f}\nBola ahora: ${bola_despues:.2f} USD\n\n📊 {data['ganadas']}/{data['salidas']} ganadas ({winrate:.0f}% winrate)\nAcum: ${data['gan_acum_total']:.2f} USD")
                for u in data["alert_users"]: tg(u, msg)
            data["pos"].remove(p); save()
            return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    data["auto"]=not data["auto"]; save(); return jsonify({"auto":data["auto"]})

@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:8px}
.header{border:2px solid #ffcc00;border-radius:22px;padding:16px;background:#111;text-align:center}
.circs{display:flex;justify-content:center;gap:20px;flex-wrap:wrap;margin-top:14px}
.circ-box{position:relative;width:175px;height:175px}
.circ-bg{fill:none;stroke:#222;stroke-width:11}
.circ-progress{fill:none;stroke:#ffcc00;stroke-width:11;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%;transition:stroke-dashoffset 1s}
.circ-progress.green{stroke:#00ff88}
.circ-inner{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;width:130px}
.small{font-size:11px;color:#888}
.big-mxn{font-size:30px;font-weight:bold;color:#00ff88;line-height:1}
.big-usd{font-size:14px;color:#ffcc00;font-weight:bold}
.card{background:#151515;border:2px solid #333;border-radius:14px;padding:10px;position:relative}
.card.off{opacity:0.35;border-color:#ff4444}
.card.signal-buy{border-color:#00ff88;box-shadow:0 0 10px #00ff88}
.btn{padding:10px;border-radius:8px;border:none;font-weight:bold;margin:3px;font-size:11px;width:31%}
.btn:disabled{opacity:0.2;background:#333!important;color:#555!important}
.btn-g{background:#00ff88;color:#000}.btn-r{background:#ff4444;color:#fff}.btn-y{background:#ffcc00;color:#000}
.badge{font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold;display:inline-block}
.badge-buy{background:#00ff88;color:#000}.badge-sell{background:#ff4444;color:#fff}.badge-wait{background:#333;color:#888}
.badge-on{background:#00ff88;color:#000;cursor:pointer}.badge-off{background:#ff4444;color:#fff;cursor:pointer}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.config{background:#151515;padding:10px;border-radius:12px;margin:10px 0;display:flex;gap:10px;flex-wrap:wrap;justify-content:space-between;align-items:center}
.info-bola{background:#000;border:1px solid #00ff88;border-radius:10px;padding:8px;margin-top:10px;text-align:center;font-size:12px}
table{width:100%;border-collapse:collapse;background:#151515;border-radius:12px;margin-top:10px;font-size:10px}
th,td{padding:6px;border-bottom:1px solid #333;text-align:center}
.neto{color:#00ff88;font-weight:bold}.perdida{color:#ff4444}
.chart-box{background:#151515;border-radius:12px;padding:10px;margin-top:12px}
</style></head><body>
<div class=header>
<b style=font-size:20px;color:#ffcc00>💰 MÁQUINA BOLA DE NIEVE</b>
<div class=circs>
<div class=circ-box>
<svg width=175 height=175><circle class=circ-bg cx=87.5 cy=87.5 r=72></circle><circle id=progressMes class="circ-progress" cx=87.5 cy=87.5 r=72 stroke-dasharray="452" stroke-dashoffset="452"></circle></svg>
<div class=circ-inner>
<div class=big-usd>500 USD</div>
<div class=big-mxn>$<span id=metaMxn>8480</span></div>
<div class=small>MXN</div>
<div class=small id=pctMesTxt style=color:#00ccff;margin-top:4px>0% - $0.00</div>
</div>
</div>
<div class=circ-box>
<svg width=175 height=175><circle class=circ-bg cx=87.5 cy=87.5 r=72></circle><circle id=progressAcum class="circ-progress green" cx=87.5 cy=87.5 r=72 stroke-dasharray="452" stroke-dashoffset="452"></circle></svg>
<div class=circ-inner>
<div class=small>ACUMULADO</div>
<div class=big style=color:#00ccff;font-size:18px>$<span id=acumUsd>0.00</span></div>
<div class=small>USD</div>
<div class=big-mxn style=font-size:20px>$<span id=acumMxn>0</span></div>
<div class=small>MXN desde 00.00</div>
</div>
</div>
</div>
<div class=info-bola id=infoBola>🎯 BOLA: $0 USD / $0 MXN (0 bolas)</div>
<div style=margin-top:8px;font-size:11px;background:#000;border-radius:8px;padding:6px;display:flex;justify-content:space-between">
<span>USD/MXN $<span id=usdmxn>0</span></span><span id=cuantas>0/0</span><span>Win <span id=winrate>0%</span></span><span>NETO <span id=tpNeto>0.1%</span></span>
</div>
</div>
<div class=config><div>💰 Cierre: <select id=tp onchange="setTP()"><option value=0.3>0.1% NETO (0.3% Bruto)</option><option value=0.4>0.2% NETO</option><option value=0.5>0.3% NETO</option><option value=0.6>0.4% NETO</option></select></div><div>🎯 Bolas: <select id=maxEnt onchange="setMax()"><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option></select></div><div><button class=btn btn-g id=autoBtn onclick="toggleAuto()" style=width:auto>...</button></div></div>
<div id=grid class=grid></div>
<div class=chart-box><b style=color:#ffcc00>📈 EVOLUCIÓN CAPITAL</b><canvas id=capitalChart height=180></canvas></div>
<table><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Neta</th><th>Acción</th></tr></thead><tbody id=tbody></tbody></table>
<div class=chart-box><b style=color:#00ff88>📋 REGISTRO COMPLETO</b>
<table id=histTable><thead><tr><th>Fecha</th><th>Moneda</th><th>Monto</th><th>Entry->Exit</th><th>% Neta</th><th>Gan MXN</th><th>Capital</th><th>Bola</th></tr></thead><tbody id=histBody></tbody></table>
</div>
<script>
let chart;
function initChart(){
 let ctx=document.getElementById('capitalChart').getContext('2d');
 chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[{label:'Capital USD',data:[],borderColor:'#00ff88',backgroundColor:'rgba(0,255,136,0.1)',fill:true,tension:0.4,borderWidth:2},{label:'Bola USD',data:[],borderColor:'#ffcc00',borderDash:[5,5],fill:false,tension:0.4,borderWidth:1}]},options:{responsive:true,plugins:{legend:{labels:{color:'#fff'}}},scales:{x:{ticks:{color:'#888'}},y:{ticks:{color:'#888'}}}}});
}
function setProgress(id, pct){let c=document.getElementById(id);let circ=2*Math.PI*72;let off=circ-(pct/100)*circ;c.style.strokeDashoffset=off;}
async function toggleCoin(sym){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({toggle_coin:sym})});load();}
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json();
 let r2=await fetch('/api/state'); let s=await r2.json();
 document.getElementById('metaMxn').innerText=s.meta_mxn.toFixed(0);
 document.getElementById('acumUsd').innerText=s.gan_acum.toFixed(2);
 document.getElementById('acumMxn').innerText=s.gan_acum_mxn.toFixed(0);
 document.getElementById('usdmxn').innerText=s.usd_mxn.toFixed(2);
 document.getElementById('pctMesTxt').innerText=s.pct_mes.toFixed(0)+'% - $'+s.gan_mes.toFixed(2)+' USD';
 document.getElementById('cuantas').innerText=s.ganadas+'/'+s.salidas;
 document.getElementById('winrate').innerText=s.winrate.toFixed(0)+'%';
 document.getElementById('tpNeto').innerText=(s.tp - s.fee_total).toFixed(1)+'%';
 document.getElementById('tp').value=s.tp; document.getElementById('maxEnt').value=s.max_entradas;
 document.getElementById('autoBtn').innerText=s.auto?'AUTO ON 🤖':'AUTO OFF 🔔';
 document.getElementById('infoBola').innerHTML='🎯 BOLA: $'+s.bola.toFixed(2)+' USD / $'+s.bola_mxn.toFixed(0)+' MXN ('+s.max_entradas+' bolas) = $'+s.capital.toFixed(2)+' / '+s.max_entradas;
 setProgress('progressMes', s.pct_mes); setProgress('progressAcum', Math.min(100, s.gan_acum/500*100));
 if(chart){
   let labels=s.capital_history.map(h=>new Date(h.t).toLocaleTimeString());
   let caps=s.capital_history.map(h=>h.cap);
   let bolas=caps.map(c=>c/s.max_entradas);
   chart.data.labels=labels; chart.data.datasets[0].data=caps; chart.data.datasets[1].data=bolas; chart.update();
 }
 let h=''; for(let sym in d){
  let activa=s.coins_activas[sym]; let inPos=s.pos.find(p=>p.sym==sym); let hasBuy=d[sym].ok&&!inPos; let hasSell=inPos&&inPos.debe_vender;
  let cls='card'; if(!activa) cls+=' off'; else if(hasBuy) cls+=' signal-buy';
  let estadoBadge=hasBuy?'<span class=badge badge-buy>COMPRA</span>':hasSell?'<span class=badge badge-sell>VENDE</span>':'<span class=badge badge-wait>ESPERA</span>';
  let onBadge=activa?`<span class="badge badge-on" onclick="toggleCoin('${sym}')">ON 🟢</span>`:`<span class="badge badge-off" onclick="toggleCoin('${sym}')">OFF 🔴</span>`;
  h+=`<div class="${cls}"><div style=display:flex;justify-content:space-between><div><b>${sym} $${d[sym].price.toFixed(2)}</b></div><div>${onBadge}</div></div><div style=margin:4px 0>${estadoBadge}</div><small>RSI ${d[sym].rsi}</small><br><small style=font-size:9px>${d[sym].motivo}</small><br><div style=margin-top:6px>`;
  if(s.auto){h+=`<div style=text-align:center;padding:6px;color:${activa?'#00ff88':'#ff4444'}>${activa?'🤖 ROBOT ON':'⛔ APAGADA'}</div><button class=btn btn-y onclick="location.href='/chart/${sym}'" style=width:95% ${!activa?'disabled':''}>GRÁFICA</button>`;}
  else{let bd=hasBuy&&activa?'':'disabled';let sd=hasSell&&activa?'':'disabled';h+=`<button class=btn btn-g onclick="buy('${sym}')" ${bd}>COMPRAR</button><button class=btn btn-r onclick="sell('${sym}')" ${sd}>VENDER</button><button class=btn btn-y onclick="location.href='/chart/${sym}'" ${!activa?'disabled':''}>GRÁFICA</button>`;}
  h+=`</div></div>`;} document.getElementById('grid').innerHTML=h;
 let tb=''; for(let p of s.pos){tb+=`<tr><td>${p.sym}</td><td>${p.entry.toFixed(2)}</td><td>${p.ahora.toFixed(2)}</td><td class=neto>${p.gan_neta_pct.toFixed(2)}% $${p.gan_neta_mxn.toFixed(2)}</td><td>${s.auto?'Robot':`<button class=btn btn-r onclick="sell('${p.sym}')">Cerrar</button>`}</td></tr>`;}
 document.getElementById('tbody').innerHTML=tb||'<tr><td colspan=5 style=text-align:center;color:#666>Sin posiciones</td></tr>';
 let hist=''; for(let i=s.historial.length-1;i>=0;i--){let tr=s.historial[i];let cls=tr.gan_neta_mxn>=0?'neto':'perdida';hist+=`<tr><td>${tr.fecha}</td><td>${tr.sym}</td><td>$${tr.monto.toFixed(2)}</td><td>${tr.entry.toFixed(2)}->${tr.exit.toFixed(2)}</td><td class=${cls}>${tr.gan_neta_pct.toFixed(2)}%</td><td class=${cls}>$${tr.gan_neta_mxn.toFixed(2)}</td><td>$${tr.capital_despues.toFixed(2)}</td><td>$${tr.bola_despues.toFixed(2)}</td></tr>`;}
 document.getElementById('histBody').innerHTML=hist||'<tr><td colspan=8 style=text-align:center;color:#666">Sin trades aún</td></tr>';
}
async function buy(s){await fetch('/api/buy/'+s,{method:'POST'});load();}
async function sell(s){await fetch('/api/sell/'+s,{method:'POST'});load();}
async function setTP(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tp:parseFloat(document.getElementById('tp').value)})});}
async function setMax(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({max:parseInt(document.getElementById('maxEnt').value)})});}
async function toggleAuto(){await fetch('/api/toggle',{method:'POST'});load();}
initChart();load(); setInterval(load,8000);
</script></body></html>"""

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    return f"<html><body style=background:#000><a href=/dashboard><button>Volver</button></a><h3 style=color:#fff>{sym}</h3><div id=c style=height:85vh></div><script src='https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js'></script><script>fetch('https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=150').then(r=>r.json()).then(kl=>{{let d=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));let ch=LightweightCharts.createChart(document.getElementById('c'),{{layout:{{background:{{color:'#000'}},textColor:'#fff'}}}});let s=ch.addCandlestickSeries();s.setData(d);}})</script></body></html>"

@app.route('/webhook', methods=['POST','GET'])
def webhook():
    if request.method=='GET': return "ok",200
    d=request.json or {}
    if "message" in d:
        chat=d["message"]["chat"]["id"]; txt=d["message"].get("text","").upper()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if "DASHBOARD" in txt or "/START" in txt:
            base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
            tg(chat,f"500 USD = ${data['usd_mxn']*500:.0f} MXN\nAcum: ${data['gan_acum_total']:.2f} desde 00.00\n{base}/dashboard")
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(5)
    while True:
        try:
            bola=data["capital_actual"]/data["max_entradas"] if data["max_entradas"] else 0
            for sym in data["coins"]:
                if not data["coins_activas"].get(sym,True): continue
                ok,rsi,ema,mot=ANALIZA(sym)
                closes=C(sym)
                if not closes: continue
                price=closes[-1]
                if ok and len(data["pos"])<data["max_entradas"] and not any(p['sym']==sym for p in data["pos"]):
                    if data["auto"]:
                        data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price,"rsi_entry":rsi,"motivo":mot,"fecha":datetime.now().strftime("%d/%m %H:%M")}); data["capital_actual"]-=bola; data["entradas"]+=1; save()
                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        gan_bruta=(price-p["entry"])/p["entry"]*100
                        if data["auto"] and (gan_bruta>=data["tp_bruto"] or rsi>=72 or gan_bruta<=-2):
                            gan_bruta_mxn=p["monto"]*gan_bruta/100
                            com_e=p["monto"]*FEE_ENTRADA; com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
                            gan_neta_mxn=gan_bruta_mxn-com_e-com_s
                            gan_neta_pct=gan_bruta-FEE_TOTAL*100
                            data["capital_actual"]+=p["monto"]+gan_neta_mxn
                            data["gan_acum_total"]+=gan_neta_mxn; data["gan_mes"]+=gan_neta_mxn; data["gan_hoy"]+=gan_neta_mxn
                            data["salidas"]+=1;
                            if gan_neta_mxn>0: data["ganadas"]+=1
                            else: data["perdidas"]+=1
                            data["historial"].append({"fecha": datetime.now().strftime("%d/%m %H:%M"),"sym": sym,"entry": p["entry"],"exit": price,"monto": p["monto"],"gan_neta_pct": gan_neta_pct,"gan_neta_mxn": gan_neta_mxn,"capital_despues": data["capital_actual"],"bola_despues": data["capital_actual"]/data["max_entradas"]})
                            data["capital_history"].append({"t": int(time.time()*1000), "cap": data["capital_actual"]})
                            # === NOTIFICACION SOLO SI GANA ===
                            if gan_neta_mxn>0:
                                winrate=(data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
                                bola_despues=data["capital_actual"]/data["max_entradas"]
                                msg=(f"✅ TRADE GANADO {sym}\n\n🟢 ENTRADA: {sym} ${p['entry']:.2f}\nBola: ${p['monto']:.2f} - RSI {p.get('rsi_entry',0):.1f}\n{p.get('fecha','')}\n\n💰 SALIDA: {sym} ${price:.2f}\n+${gan_neta_mxn:.2f} MXN ({gan_neta_pct:.2f}% NETO)\nCapital ahora: ${data['capital_actual']:.2f}\nBola ahora: ${bola_despues:.2f} USD\n\n📊 {data['ganadas']}/{data['salidas']} ganadas ({winrate:.0f}% winrate)\nAcum: ${data['gan_acum_total']:.2f} USD")
                                for u in data["alert_users"]: tg(u, msg)
                            data["pos"].remove(p); save()
            time.sleep(60)
        except Exception as e:
            print(e); time.sleep(10)
threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
