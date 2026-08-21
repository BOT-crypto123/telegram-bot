import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
FILE="bot_data.json"

FEE_ENTRADA = 0.001
FEE_SALIDA = 0.001
FEE_TOTAL = 0.002

data={
    "base_inicial": 10060.05,
    "capital_actual": 10370.10,
    "gan_acum_total": 310.05,
    "gan_mes": 310.05,
    "gan_hoy": 0.0,
    "historial_diario": [],
    "pos": [],
    "coins": ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas": 5,
    "tp_bruto": 0.5, # 0.5% bruto = 0.3% neto real - NO MUEVO NADA MAS
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
    cond1 = r_now < 32; cond2 = price > ema20*0.995; cond3 = r_now > r_prev
    ok = cond1 and cond2 and cond3
    motivo = f"RSI {r_now:.1f} {'✅' if cond1 else '❌'}<32, P>EMA {'✅' if cond2 else '❌'}, Mom {r_prev:.0f}->{r_now:.0f} {'✅' if cond3 else '❌'}"
    return ok, r_now, ema20, motivo

def tg(uid, txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 VER DASHBOARD","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.66 ON=ROBOT OFF=AVISA LIVE",200

@app.route('/api/prices')
def prices():
    out={}
    for sym in data["coins"]:
        ok,rsi,ema,mot = ANALIZA(sym)
        closes=C(sym); price=closes[-1] if closes else P(sym)
        action="COMPRAR" if ok else "VENDER" if rsi>72 else "SOSTENER"
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"action":action,"ok":ok,"motivo":mot,"activa":data["coins_activas"].get(sym,True)}
    return jsonify(out)

@app.route('/api/state')
def state():
    bola = data["capital_actual"] / data["max_entradas"] if data["max_entradas"] else 0
    for p in data["pos"]:
        price=P(p["sym"]); p["ahora"]=price
        gan_bruta_pct = ((price-p["entry"])/p["entry"]*100) if p["entry"] else 0
        gan_bruta_mxn = p["monto"] * gan_bruta_pct/100
        comision_total_mxn = p["monto"]*FEE_ENTRADA + (p["monto"]+gan_bruta_mxn)*FEE_SALIDA
        gan_neta_mxn = gan_bruta_mxn - comision_total_mxn
        gan_neta_pct = gan_bruta_pct - FEE_TOTAL*100
        p["gan_bruta_pct"]=gan_bruta_pct; p["gan_neta_pct"]=gan_neta_pct
        p["gan_bruta_mxn"]=gan_bruta_mxn; p["gan_neta_mxn"]=gan_neta_mxn
        p["comision_total_mxn"]=comision_total_mxn
        p["rsi_now"]=RSI(C(p["sym"])) if C(p["sym"]) else 50
        p["debe_vender"]= gan_bruta_pct>=data["tp_bruto"] or p["rsi_now"]>=72 or gan_bruta_pct<=-2
    # CUANTAS DE CUANTAS
    winrate = (data["ganadas"]/data["salidas"]*100) if data["salidas"] else 0
    return jsonify({
        "base": data["base_inicial"], "capital": data["capital_actual"], "gan_acum": data["gan_acum_total"],
        "gan_mes": data["gan_mes"], "gan_hoy": data["gan_hoy"], "bola": bola,
        "pos": data["pos"], "max_entradas": data["max_entradas"], "tp": data["tp_bruto"],
        "auto": data["auto"], "coins_activas": data["coins_activas"],
        "entradas": data["entradas"], "salidas": data["salidas"], "ganadas": data["ganadas"], "perdidas": data["perdidas"],
        "winrate": winrate,
        "fee_total": FEE_TOTAL*100
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
    ok,rsi,ema,mot=ANALIZA(sym)
    bola=data["capital_actual"]/data["max_entradas"]; price=P(sym)
    data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price,"rsi_entry":rsi,"motivo":mot})
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
            data["salidas"]+=1
            if gan_neta_mxn>0: data["ganadas"]+=1
            else: data["perdidas"]+=1
            data["pos"].remove(p); save()
            # SOLO AVISA SI ES GANANCIA - COMO PEDISTE
            if gan_neta_mxn>0:
                for u in data["alert_users"]:
                    tg(u,f"💰 CIERRE GANANCIA {sym}\nBRUTA {gan_bruta_pct:.2f}% = ${gan_bruta_mxn:.2f}\nComis -${com_e+com_s:.2f}\nNETA {gan_neta_pct:.2f}% = +${gan_neta_mxn:.2f}\nCuantas: {data['ganadas']}/{data['salidas']} ({data['ganadas']/data['salidas']*100:.0f}% win)\nCap ${data['capital_actual']:.2f} Bola ${data['capital_actual']/data['max_entradas']:.2f}")
            return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    data["auto"]=not data["auto"]; save(); return jsonify({"auto":data["auto"]})

@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}
.header{text-align:center;padding:14px;border:2px solid #ffcc00;border-radius:18px;background:#111;margin-bottom:10px}
.circ-wrap{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;margin-top:10px}
.circ{width:132px;height:132px;border-radius:50%;border:4px solid #333;display:flex;align-items:center;justify-content:center;flex-direction:column;background:#0a0a0a}
.circ.gold{border-color:#ffcc00;box-shadow:0 0 20px #ffcc00}.circ.green{border-color:#00ff88}.circ.blue{border-color:#00ccff}
.btn{padding:10px 12px;border-radius:8px;border:none;font-weight:bold;margin:3px;font-size:12px;width:31%}
.btn:disabled{opacity:0.25;background:#333!important;color:#555!important}
.btn-g{background:#00ff88;color:#000}.btn-r{background:#ff4444;color:#fff}.btn-y{background:#ffcc00;color:#000}
.card{background:#151515;border:2px solid #333;border-radius:14px;padding:10px;position:relative}
.card.signal-buy{border-color:#00ff88;box-shadow:0 0 12px #00ff88}.card.signal-sell{border-color:#ff4444;box-shadow:0 0 12px #ff4444}.card.off{opacity:0.4}
.badge{position:absolute;top:6px;right:6px;font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold}
.badge-buy{background:#00ff88;color:#000}.badge-sell{background:#ff4444;color:#fff}.badge-wait{background:#333;color:#888}
table{width:100%;border-collapse:collapse;background:#151515;border-radius:12px;margin-top:10px;font-size:11px}
th,td{padding:6px;border-bottom:1px solid #333;text-align:left}
.neto{color:#00ff88;font-weight:bold}.desglose{font-size:10px;color:#aaa}
.config{background:#151515;padding:10px;border-radius:12px;margin-bottom:10px;display:flex;gap:10px;flex-wrap:wrap;justify-content:space-between}
.sum{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px}
.sum div{background:#111;border:1px solid #333;border-radius:8px;padding:6px;text-align:center;font-size:12px}
</style></head><body>
<div class=header>
<b style=font-size:20px;color:#ffcc00>💰 MÁQUINA BOLA DE NIEVE</b>
<div class=circ-wrap>
<div class=circ gold><small style=color:#ffcc00;font-size:10px>BASE + ACUM</small><span style=font-size:11px;color:#aaa>Base $<span id=base>0</span></span><span style=font-size:22px;font-weight:bold;color:#00ff88>+$<span id=acum>0</span></span><span style=font-size:12px;color:#fff>Cap $<span id=cap>0</span></span></div>
<div class=circ blue><small>BOLA NIEVE</small><b style=font-size:20px;color:#00ccff>$<span id=bola>0</span></b><small id=bolaDet>0/0</small></div>
<div class=circ green><small>HOY NETO</small><b style=font-size:18px;color:#00ff88>$<span id=hoy>0</span></b><small>Mes $<span id=ganMes>0</span></small></div>
</div>
<div style=margin-top:10px;font-size:11px;background:#000;border-radius:8px;padding:6px><b>DESGLOSE REAL:</b> Bruta - 0.2% = Neta | TP Bruto <span id=tpBruto>0</span>% = <span id=tpNeto>0</span>% neto</div>
<div style=margin-top:6px;font-size:12px;background:#151515;border-radius:8px;padding:6px><b>CUANTAS DE CUANTAS:</b> <span id=cuantas>0/0</span> | Win <span id=winrate>0%</span> | Entr <span id=entr>0</span> | Sal <span id=sal>0</span></div>
</div>
<div class=config><div>💰 Cierre: <select id=tp onchange="setTP()"><option value=0.5>0.3% NETO (0.5% Bruto)</option><option value=0.6>0.4% NETO</option><option value=0.7>0.5% NETO</option><option value=0.8>0.6% NETO</option></select></div><div>🎯 Bolas: <select id=maxEnt onchange="setMax()"><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option></select></div><div><button class=btn btn-g id=autoBtn onclick="toggleAuto()" style=width:auto>...</button></div></div>
<div id=grid style=display:grid;grid-template-columns:1fr 1fr;gap:8px></div>
<table><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Bruta</th><th>Comis</th><th>Neta</th><th>Acción</th></tr></thead><tbody id=tbody></tbody></table>
<script>
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json();
 let r2=await fetch('/api/state'); let s=await r2.json();
 document.getElementById('base').innerText=s.base.toFixed(2); document.getElementById('cap').innerText=s.capital.toFixed(2);
 document.getElementById('acum').innerText=s.gan_acum.toFixed(2); document.getElementById('ganMes').innerText=s.gan_mes.toFixed(2);
 document.getElementById('hoy').innerText=s.gan_hoy.toFixed(2); document.getElementById('bola').innerText=s.bola.toFixed(2);
 document.getElementById('bolaDet').innerText=s.pos.length+'/'+s.max_entradas; document.getElementById('tp').value=s.tp;
 document.getElementById('tpBruto').innerText=s.tp.toFixed(1); document.getElementById('tpNeto').innerText=(s.tp - s.fee_total).toFixed(1);
 document.getElementById('maxEnt').value=s.max_entradas; document.getElementById('autoBtn').innerText=s.auto?'AUTO ON 🤖 COMPRA/VENDE SOLO':'AUTO OFF 🔔 SOLO AVISA ENTRADA';
 document.getElementById('entr').innerText=s.entradas; document.getElementById('sal').innerText=s.salidas;
 document.getElementById('cuantas').innerText=s.ganadas+'/'+s.salidas; document.getElementById('winrate').innerText=s.winrate.toFixed(0)+'%';
 let h=''; for(let sym in d){
  let activa=s.coins_activas[sym]; let inPos=s.pos.find(p=>p.sym==sym); let hasBuy=d[sym].ok&&!inPos; let hasSell=inPos&&inPos.debe_vender;
  let cls='card'; if(!activa) cls+=' off'; else if(hasBuy) cls+=' signal-buy'; else if(hasSell) cls+=' signal-sell';
  let badge=hasBuy?'<span class=badge badge-buy>🔔 COMPRA</span>':hasSell?'<span class=badge badge-sell>💰 VENDE</span>':'<span class=badge badge-wait>ESPERA</span>';
  h+=`<div class="${cls}">${badge}<b>${sym} $${d[sym].price.toFixed(2)}</b><br><small>RSI ${d[sym].rsi}</small><br><small style=font-size:9px>${d[sym].motivo}</small><br><div style=margin-top:6px>`;
  if(s.auto){h+=`<div style=text-align:center;padding:6px;color:#00ff88>🤖 ROBOT ACTIVO</div><button class=btn btn-y onclick="location.href='/chart/${sym}'" style=width:95%>GRÁFICA</button>`;}
  else{let bd=hasBuy&&activa?'':'disabled';let sd=hasSell&&activa?'':'disabled';h+=`<button class=btn btn-g onclick="buy('${sym}')" ${bd}>COMPRAR</button><button class=btn btn-r onclick="sell('${sym}')" ${sd}>VENDER</button><button class=btn btn-y onclick="location.href='/chart/${sym}'">GRÁFICA</button>`;}
  h+=`</div></div>`;} document.getElementById('grid').innerHTML=h;
 let tb=''; for(let p of s.pos){tb+=`<tr><td>${p.sym}</td><td>${p.entry.toFixed(2)}</td><td>${p.ahora.toFixed(2)}</td><td class=desglose>+${p.gan_bruta_pct.toFixed(2)}%<br>$${p.gan_bruta_mxn.toFixed(2)}</td><td class=desglose style=color:#ff4444>-${s.fee_total.toFixed(1)}%<br>-$${p.comision_total_mxn.toFixed(2)}</td><td class=neto>${p.gan_neta_pct.toFixed(2)}%<br>$${p.gan_neta_mxn.toFixed(2)}</td><td>${s.auto?'<span style=color:#00ff88>Robot</span>':`<button class=btn btn-r onclick="sell('${p.sym}')">Cerrar</button>`}</td></tr>`;}
 document.getElementById('tbody').innerHTML=tb||'<tr><td colspan=7 style=text-align:center;color:#666>Sin posiciones - Esperando RSI<32</td></tr>';
}
async function buy(s){await fetch('/api/buy/'+s,{method:'POST'});load();}
async function sell(s){await fetch('/api/sell/'+s,{method:'POST'});load();}
async function setTP(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tp:parseFloat(document.getElementById('tp').value)})});}
async function setMax(){await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({max:parseInt(document.getElementById('maxEnt').value)})});}
async function toggleAuto(){await fetch('/api/toggle',{method:'POST'});load();}
load(); setInterval(load,8000);
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
            bola=data["capital_actual"]/data["max_entradas"]
            win=data["ganadas"]/data["salidas"]*100 if data["salidas"] else 0
            tg(chat,f"BOLA DE NIEVE\nBase ${data['base_inicial']:.2f} Acum +${data['gan_acum_total']:.2f}\nCap ${data['capital_actual']:.2f} Bola ${bola:.2f}\nCuantas: {data['ganadas']}/{data['salidas']} ({win:.0f}% win)\n{base}/dashboard")
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(5)
    while True:
        try:
            bola = data["capital_actual"] / data["max_entradas"] if data["max_entradas"] else 0
            for sym in data["coins"]:
                if not data["coins_activas"].get(sym,True): continue
                ok,rsi,ema,mot=ANALIZA(sym)
                closes=C(sym)
                if not closes: continue
                price=closes[-1]
                # ENTRADA
                if ok and len(data["pos"])<data["max_entradas"] and not any(p['sym']==sym for p in data["pos"]):
                    if data["auto"]:
                        # ON = COMPRA SOLA - NO AVISA ENTRADA
                        data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price,"motivo":mot}); data["capital_actual"]-=bola; data["entradas"]+=1; save()
                    else:
                        # OFF = SOLO NOTIFICA
                        last=data["last_alert"].get(sym,0)
                        if time.time()-last>3600:
                            for u in data["alert_users"]: tg(u,f"🔔 ENTRADA DETECTADA {sym}\n{mot}\nPrecio ${price:.2f} Bola ${bola:.2f}\nAUTO OFF - Entra a dashboard y compra manual")
                            data["last_alert"][sym]=time.time(); save()
                # SALIDA
                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        gan_bruta=(price-p["entry"])/p["entry"]*100
                        # SOLO VENDE SI AUTO ON
                        if data["auto"] and (gan_bruta>=data["tp_bruto"] or rsi>=72 or gan_bruta<=-2):
                            gan_bruta_mxn=p["monto"]*gan_bruta/100
                            com_e=p["monto"]*FEE_ENTRADA; com_s=(p["monto"]+gan_bruta_mxn)*FEE_SALIDA
                            gan_neta_mxn=gan_bruta_mxn-com_e-com_s
                            data["capital_actual"]+=p["monto"]+gan_neta_mxn
                            data["gan_acum_total"]+=gan_neta_mxn; data["gan_mes"]+=gan_neta_mxn; data["gan_hoy"]+=gan_neta_mxn
                            data["salidas"]+=1; data["ganadas"]+=1 if gan_neta_mxn>0 else 0; data["perdidas"]+=0 if gan_neta_mxn>0 else 1
                            data["pos"].remove(p); save()
                            # TELEGRAM SOLO SI ES GANANCIA - COMO PEDISTE
                            if gan_neta_mxn>0:
                                win=data["ganadas"]/data["salidas"]*100 if data["salidas"] else 0
                                for u in data["alert_users"]: tg(u,f"💰 CIERRE GANANCIA {sym}\nNETA +${gan_neta_mxn:.2f} ({gan_bruta-FEE_TOTAL*100:.2f}%)\nCuantas: {data['ganadas']}/{data['salidas']} Win {win:.0f}%\nCap ${data['capital_actual']:.2f} Bola ${data['capital_actual']/data['max_entradas']:.2f}")
            time.sleep(60)
        except Exception as e:
            print(e); time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
