import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
FILE="bot_data.json"

data={
    "base_inicial": 10060.05,
    "capital_actual": 10370.10,
    "gan_acum_total": 310.05,
    "gan_mes": 310.05,
    "gan_hoy": 0.0,
    "historial_diario": [],
    "pos": [], # cada pos: sym, monto, entry, ahora, rsi_entry, ema_entry, gan_pct
    "coins": ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas": 5,
    "tp_bruto": 0.4, # 0.4 bruto = 0.3 neto real
    "auto": True,
    "alert_users": [],
    "entradas": 15, "salidas": 12, "ganadas": 10, "perdidas": 2,
    "last_alert": {}
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
    rs=g/l if l else 100
    return 100-(100/(1+rs))
def EMA(cl,p=20):
    if len(cl)<p: return cl[-1]
    k=2/(p+1); e=cl[0]
    for c in cl[1:]: e=c*k+e*(1-k)
    return e
def RSI_HISTORY(cl):
    # para momentum: RSI anterior vs actual
    if len(cl)<16: return 50,50
    rsi_now=RSI(cl[-14:])
    rsi_prev=RSI(cl[-15:-1])
    return rsi_prev, rsi_now

def ANALIZA_ENTRADA(sym):
    closes=C(sym)
    if len(closes)<30: return False, 50, 0, "Sin datos"
    rsi_prev, rsi_now = RSI_HISTORY(closes)
    ema20 = EMA(closes,20)
    price = closes[-1]

    # ESTRATEGIA COMPLETA
    cond1 = rsi_now < 32 # sobreventa
    cond2 = price > ema20 * 0.995 # no cuchillo, ya rebotando cerca de EMA
    cond3 = rsi_now > rsi_prev # momentum subiendo
    cond4 = rsi_now < 70 # no sobrecompra

    ok = cond1 and cond2 and cond3 and cond4
    motivo = f"RSI {rsi_now:.1f} {'✅' if cond1 else '❌'}<32, Price>{'%.2f'%ema20} {'✅' if cond2 else '❌'}, Mom {rsi_prev:.1f}->{rsi_now:.1f} {'✅' if cond3 else '❌'}"
    return ok, rsi_now, ema20, motivo

def tg(uid, txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 VER DASHBOARD","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.63 ESTRATEGIA COMPLETA LIVE",200

@app.route('/api/prices')
def prices():
    out={}
    for sym in data["coins"]:
        ok, rsi, ema, motivo = ANALIZA_ENTRADA(sym)
        closes=C(sym); price=closes[-1] if closes else P(sym)
        action="COMPRAR" if ok else "SOSTENER"
        # si RSI>72 ya es venta si estas dentro
        if rsi>72: action="VENDER"
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"action":action,"ok":ok,"motivo":motivo,"activa":data["coins_activas"].get(sym,True)}
    return jsonify(out)

@app.route('/api/state')
def state():
    bola = data["capital_actual"] / data["max_entradas"] if data["max_entradas"] else 0
    for p in data["pos"]:
        price=P(p["sym"]); p["ahora"]=price
        p["gan_pct"]=((price-p["entry"])/p["entry"]*100) if p["entry"] else 0
        # analiza salida
        closes=C(p["sym"])
        if closes:
            rsi=RSI(closes)
            p["rsi_now"]=rsi
            p["debe_vender"]= p["gan_pct"]>=data["tp_bruto"] or rsi>=72 or p["gan_pct"]<=-2
        else:
            p["rsi_now"]=50; p["debe_vender"]=False
    return jsonify({
        "base": data["base_inicial"], "capital": data["capital_actual"], "gan_acum": data["gan_acum_total"],
        "gan_mes": data["gan_mes"], "gan_hoy": data["gan_hoy"], "bola": bola,
        "historial": data["historial_diario"][-30:], "pos": data["pos"],
        "max_entradas": data["max_entradas"], "tp": data["tp_bruto"], "auto": data["auto"],
        "coins_activas": data["coins_activas"], "entradas": data["entradas"],
        "salidas": data["salidas"], "ganadas": data["ganadas"], "perdidas": data["perdidas"]
    })

@app.route('/api/config', methods=['POST'])
def config():
    j=request.json or {}
    if "tp" in j: data["tp_bruto"]=float(j["tp"])
    if "max" in j: data["max_entradas"]=int(j["max"])
    if "toggle_coin" in j: c=j["toggle_coin"]; data["coins_activas"][c]=not data["coins_activas"].get(c,True)
    save(); return jsonify({"ok":True})

@app.route('/api/buy/<sym>', methods=['POST'])
def buy_api(sym):
    sym=sym.upper()
    if len(data["pos"])>=data["max_entradas"]: return jsonify({"ok":False,"msg":"max bolas"})
    if any(p['sym']==sym for p in data["pos"]): return jsonify({"ok":False})
    ok,rsi,ema,motivo=ANALIZA_ENTRADA(sym)
    # en manual si dejas comprar aunque no haya señal perfecta, pero te avisamos
    bola=data["capital_actual"]/data["max_entradas"]; price=P(sym)
    data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price,"rsi_entry":rsi,"ema_entry":ema,"motivo":motivo})
    data["capital_actual"]-=bola; data["entradas"]+=1; save(); return jsonify({"ok":True,"analisis":motivo})

@app.route('/api/sell/<sym>', methods=['POST'])
def sell_api(sym):
    sym=sym.upper()
    for p in data["pos"][:]:
        if p["sym"]==sym:
            price=P(sym); gan=(price-p["entry"])/p["entry"]*100; gan_mxn=p["monto"]*gan/100
            data["capital_actual"]+=p["monto"]+gan_mxn; data["gan_acum_total"]+=gan_mxn; data["gan_mes"]+=gan_mxn; data["gan_hoy"]+=gan_mxn
            data["salidas"]+=1; data["ganadas"]+=1 if gan>0 else 0; data["perdidas"]+=0 if gan>0 else 1
            data["pos"].remove(p); save()
            if gan>0:
                for u in data["alert_users"]: tg(u,f"💰 CIERRE {sym} +{gan:.2f}% = +${gan_mxn:.2f}\nEstrategia: {p.get('motivo','')}\nCap ${data['capital_actual']:.2f} Bola ${data['capital_actual']/data['max_entradas']:.2f}")
            return jsonify({"ok":True,"gan":gan})
    return jsonify({"ok":False})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    data["auto"]=not data["auto"]; save(); return jsonify({"auto":data["auto"]})

@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}
.header{text-align:center;padding:12px;border:2px solid #ffcc00;border-radius:14px;background:#111;margin-bottom:10px}
.circle-wrap{display:flex;justify-content:space-around;flex-wrap:wrap;gap:10px}
.circle{width:108px;height:108px;border-radius:50%;border:4px solid #333;display:flex;align-items:center;justify-content:center;flex-direction:column}
.circle.gold{border-color:#ffcc00;box-shadow:0 0 15px #ffcc00}.circle.green{border-color:#00ff88}.circle.blue{border-color:#00ccff}
.config{background:#151515;padding:10px;border-radius:12px;margin-bottom:10px;display:flex;gap:10px;flex-wrap:wrap;justify-content:space-between}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.card{background:#151515;border:2px solid #333;border-radius:14px;padding:10px;position:relative}
.card.signal-buy{border-color:#00ff88;box-shadow:0 0 12px #00ff88}
.card.signal-sell{border-color:#ff4444;box-shadow:0 0 12px #ff4444}
.card.off{opacity:0.4}
.btn{padding:10px 12px;border-radius:8px;border:none;font-weight:bold;margin:3px;font-size:13px;width:31%}
.btn:disabled{opacity:0.25;background:#333!important;color:#555!important}
.btn-g{background:#00ff88;color:#000}.btn-r{background:#ff4444;color:#fff}.btn-y{background:#ffcc00;color:#000}.btn-b{background:#333;color:#fff}
.badge{position:absolute;top:6px;right:6px;font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold}
.badge-buy{background:#00ff88;color:#000}.badge-sell{background:#ff4444;color:#fff}.badge-wait{background:#333;color:#888}
table{width:100%;border-collapse:collapse;background:#151515;border-radius:12px;margin-top:10px;font-size:12px}
th,td{padding:6px;border-bottom:1px solid #333;text-align:left}
</style></head><body>
<div class=header>
<b style=font-size:18px;color:#ffcc00>💰 MÁQUINA DE HACER DINERO<br>BOLA DE NIEVE + ESTRATEGIA</b>
<div class=circle-wrap>
<div class=circle gold><small>MES</small><b id=mesPct>0%</b><small>$<span id=ganMes>0</span></small></div>
<div class=circle green><small>CAPITAL</small><b>$<span id=cap>0</span></b></div>
<div class=circle blue><small>BOLA</small><b>$<span id=bola>0</span></b></div>
</div>
<div style=font-size:11px;margin-top:6px>TP <span id=tpTxt>0</span>% Neto | <span id=modoTxt>...</span> | Estrategia: RSI14<32 + Price>EMA20 + Momentum↑</div>
</div>
<div class=config>
<div>TP: <select id=tp onchange="setTP()"><option value=0.4>0.3% Neto (0.4 Bruto)</option><option value=0.5>0.4% Neto</option><option value=0.6>0.5% Neto</option><option value=0.7>0.6% Neto</option></select></div>
<div>Bolas: <select id=maxEnt onchange="setMax()"><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option></select></div>
<div><button class=btn btn-g id=autoBtn onclick="toggleAuto()" style=width:auto>...</button></div>
</div>
<div class=grid id=grid></div>
<table><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Gan%</th><th>RSI</th><th>Acción</th></tr></thead><tbody id=tbody></tbody></table>
<script>
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json();
 let r2=await fetch('/api/state'); let s=await r2.json();
 document.getElementById('cap').innerText=s.capital.toFixed(2);
 document.getElementById('bola').innerText=s.bola.toFixed(2);
 document.getElementById('ganMes').innerText=s.gan_mes.toFixed(2);
 document.getElementById('tp').value=s.tp; document.getElementById('maxEnt').value=s.max_entradas;
 document.getElementById('tpTxt').innerText=(s.tp-0.1).toFixed(1);
 document.getElementById('modoTxt').innerText=s.auto?'AUTO ON 🤖 Robot con estrategia':'AUTO OFF 🔔 Avisa señal';
 document.getElementById('autoBtn').innerText=s.auto?'AUTO ON - ESTRATEGIA ACTIVA':'AUTO OFF - ESPERANDO SEÑAL';
 document.getElementById('mesPct').innerText=Math.min(100,(s.gan_mes/1000*100)).toFixed(0)+'%';
 let h='';
 for(let sym in d){
  let activa=s.coins_activas[sym];
  let inPos = s.pos.find(p=>p.sym==sym);
  let hasBuy = d[sym].ok &&!inPos;
  let hasSell = inPos && inPos.debe_vender;
  let cardClass='card'; if(!activa) cardClass+=' off'; else if(hasBuy) cardClass+=' signal-buy'; else if(hasSell) cardClass+=' signal-sell';
  let badge=''; if(hasBuy) badge='<span class=badge badge-buy>🔔 COMPRA</span>'; else if(hasSell) badge='<span class=badge badge-sell>💰 VENDE</span>'; else badge='<span class=badge badge-wait>ESPERA</span>';
  h+=`<div class="${cardClass}">${badge}<b>${sym} $${d[sym].price.toFixed(2)}</b><br><small>RSI ${d[sym].rsi} EMA ${d[sym].ema}</small><br><small style=font-size:10px;color:${d[sym].ok?'#00ff88':'#888'}>${d[sym].motivo}</small><br><div style=margin-top:6px>`;
  if(s.auto){
    h+=`<div style=text-align:center;padding:6px;color:#00ff88;font-size:12px>🤖 ${inPos?'En posición - Esperando TP/RSI72':'Analizando estrategia...'}</div><button class=btn btn-y onclick="location.href='/chart/${sym}'" style=width:95%>GRÁFICA</button>`;
  } else {
    let buyDis = hasBuy && activa? '' : 'disabled'; let sellDis = hasSell && activa? '' : 'disabled';
    h+=`<button class=btn btn-g onclick="buy('${sym}')" ${buyDis}>COMPRAR</button><button class=btn btn-r onclick="sell('${sym}')" ${sellDis}>VENDER</button><button class=btn btn-y onclick="location.href='/chart/${sym}'">GRÁFICA</button><br><small style=color:${hasBuy||hasSell?'#00ff88':'#666'};font-size:10px>${hasBuy||hasSell?'✅ SEÑAL ESTRATEGIA ACTIVA':'⏸️ Sin señal - bloqueado'}</small>`;
  }
  h+=`</div></div>`;
 }
 document.getElementById('grid').innerHTML=h;
 let tb=''; for(let p of s.pos){ tb+=`<tr><td>${p.sym}<br><small style=font-size:9px>${p.motivo||''}</small></td><td>${p.entry.toFixed(2)}</td><td>${p.ahora.toFixed(2)}</td><td>${p.gan_pct.toFixed(2)}% abierta</td><td>${(p.rsi_now||0).toFixed(1)}</td><td>${s.auto?'<span style=color:#00ff88>Robot</span>':`<button class=btn btn-r onclick="sell('${p.sym}')" ${p.debe_vender?'':'disabled'}>Cerrar</button>`}</td></tr>`; }
 document.getElementById('tbody').innerHTML=tb||'<tr><td colspan=6 style=text-align:center;color:#666>Sin posiciones - Estrategia: RSI<32 + Price>EMA20*0.995 + Momentum RSI↑</td></tr>';
}
async function buy(s){ await fetch('/api/buy/'+s,{method:'POST'}); load(); }
async function sell(s){ await fetch('/api/sell/'+s,{method:'POST'}); load(); }
async function setTP(){ await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tp:parseFloat(document.getElementById('tp').value)})}); }
async function setMax(){ await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({max:parseInt(document.getElementById('maxEnt').value)})}); }
async function toggleAuto(){ await fetch('/api/toggle',{method:'POST'}); load(); }
load(); setInterval(load,8000);
</script></body></html>"""

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    return f"<html><head><meta name=viewport content='width=device-width,initial-scale=1'><script src='https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js'></script></head><body style=background:#000><a href=/dashboard><button>Volver</button></a><h3 style=color:#fff>{sym} - RSI14 + EMA20 Estrategia</h3><div id=c style=height:85vh></div><script>fetch('https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=150').then(r=>r.json()).then(kl=>{{let d=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));let ch=LightweightCharts.createChart(document.getElementById('c'),{{layout:{{background:{{color:'#000'}},textColor:'#fff'}}}});let s=ch.addCandlestickSeries();s.setData(d);}})</script></body></html>"

@app.route('/webhook', methods=['POST','GET'])
def webhook():
    if request.method=='GET': return "ok",200
    d=request.json or {}
    if "message" in d:
        c=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
        if c not in data["alert_users"]: data["alert_users"].append(c)
        if "DASHBOARD" in t or "/START" in t:
            base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
            modo = "ON - Estrategia automática" if data["auto"] else "OFF - Solo avisa señal"
            tg(c,f"MÁQUINA BOLA NIEVE + ESTRATEGIA\nCap ${data['capital_actual']:.2f} Bola ${data['capital_actual']/data['max_entradas']:.2f}\nModo: {modo}\nTP {data['tp_bruto']-0.1:.1f}% Neto\nEstrategia: RSI<32 + Price>EMA20 + Mom↑\n{base}/dashboard")
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(5)
    while True:
        try:
            bola = data["capital_actual"] / data["max_entradas"] if data["max_entradas"] else 0
            for sym in data["coins"]:
                if not data["coins_activas"].get(sym,True): continue
                ok, rsi, ema, motivo = ANALIZA_ENTRADA(sym)
                closes=C(sym)
                if not closes: continue
                price=closes[-1]
                is_entry = ok and len(data["pos"])<data["max_entradas"] and not any(p['sym']==sym for p in data["pos"])

                if is_entry:
                    if data["auto"]:
                        data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price,"rsi_entry":rsi,"ema_entry":ema,"motivo":motivo})
                        data["capital_actual"]-=bola; data["entradas"]+=1; save()
                    else:
                        last = data["last_alert"].get(sym,0)
                        if time.time() - last > 3600:
                            for u in data["alert_users"]:
                                tg(u,f"🔔 ENTRADA ESTRATEGIA {sym}\n{motivo}\nPrecio ${price:.2f} Bola ${bola:.2f}\nAUTO OFF - Entra a dashboard, botón COMPRAR activo")
                            data["last_alert"][sym]=time.time(); save()

                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        gan=(price-p["entry"])/p["entry"]*100
                        # SALIDA POR ESTRATEGIA
                        debe_vender = gan>=data["tp_bruto"] or rsi>=72 or gan<=-2
                        if data["auto"] and debe_vender:
                            gan_mxn=p["monto"]*gan/100; data["capital_actual"]+=p["monto"]+gan_mxn
                            data["gan_acum_total"]+=gan_mxn; data["gan_mes"]+=gan_mxn; data["gan_hoy"]+=gan_mxn
                            data["salidas"]+=1; data["ganadas"]+=1 if gan>0 else 0; data["perdidas"]+=0 if gan>0 else 1
                            data["pos"].remove(p); save()
                            if gan>0:
                                for u in data["alert_users"]: tg(u,f"💰 {sym} +{gan:.2f}% = +${gan_mxn:.2f}\nMotivo cierre: {'TP' if gan>=data['tp_bruto'] else 'RSI>72' if rsi>=72 else 'STOP'}\nCap ${data['capital_actual']:.2f}")

            # CIERRE DIARIO
            now=datetime.utcnow()
            if now.hour==4 and now.minute<5:
                fecha=now.strftime("%Y-%m-%d")
                if not any(h["fecha"]==fecha for h in data["historial_diario"]):
                    data["historial_diario"].append({"fecha":fecha,"gan":data["gan_hoy"],"capital":data["capital_actual"]})
                    if len(data["historial_diario"])>90: data["historial_diario"]=data["historial_diario"][-90:]
                    if now.day==1:
                        for u in data["alert_users"]: tg(u,f"📅 CIERRE MES ${data['gan_mes']:.2f} Cap ${data['capital_actual']:.2f}")
                        data["gan_mes"]=0
                    data["gan_hoy"]=0; save()
                time.sleep(60)
            time.sleep(60)
        except Exception as e:
            print(e); time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
