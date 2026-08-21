import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
FILE="bot_data.json"

data={
    "base_inicial": 10060.05,
    "capital_actual": 10370.10, # base + lo acumulado que traes
    "gan_acum_total": 310.05,
    "gan_hoy": 0.0,
    "historial_diario": [ # aqui se va guardando diario diario
        # {"fecha":"2026-08-20","gan": 150.5, "capital": 10210.0},
        # {"fecha":"2026-08-21","gan": 159.55, "capital": 10370.10}
    ],
    "pos": [],
    "coins": ["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},
    "max_entradas": 5,
    "tp_bruto": 0.4,
    "auto": True,
    "alert_users": [],
    "entradas":0,"salidas":0,"ganadas":0,"perdidas":0
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
    return 100-(100/(1+g/l))
def EMA(cl,p=20):
    if len(cl)<p: return cl[-1]
    k=2/(p+1); e=cl[0]
    for c in cl[1:]: e=c*k+e*(1-k)
    return e

def tg(uid, txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 Dashboard","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/', methods=['GET','HEAD','POST'])
def root():
    if request.method=='POST': return webhook()
    return "V1002.42 BOLA DE NIEVE LIVE",200

@app.route('/api/state')
def state():
    # BOLA DE NIEVE: cada bola = capital_actual / max_entradas
    bola = data["capital_actual"] / data["max_entradas"] if data["max_entradas"] else 0
    total = data["capital_actual"] + data["gan_hoy"]
    # promedio diario para proyeccion
    avg_diario = sum([d["gan"] for d in data["historial_diario"][-7:]])/7 if len(data["historial_diario"])>=7 else data["gan_hoy"]
    if avg_diario==0 and data["gan_acum_total"]: avg_diario = data["gan_acum_total"]/20 # estimado si es nuevo

    for p in data["pos"]:
        p["ahora"]=P(p["sym"])
        p["gan_pct"]=((p["ahora"]-p["entry"])/p["entry"]*100) if p["entry"] else 0

    return jsonify({
        "base": data["base_inicial"],
        "capital_actual": data["capital_actual"],
        "gan_acum": data["gan_acum_total"],
        "gan_hoy": data["gan_hoy"],
        "bola_actual": bola,
        "historial": data["historial_diario"][-30:], # ultimos 30 dias
        "pos": data["pos"],
        "max_entradas": data["max_entradas"],
        "tp": data["tp_bruto"],
        "auto": data["auto"],
        "avg_diario": avg_diario,
        "entradas": data["entradas"],"salidas": data["salidas"],"ganadas": data["ganadas"],"perdidas": data["perdidas"]
    })

@app.route('/api/proyeccion')
def proyeccion():
    # Proyeccion 30 meses bola de nieve
    capital = data["capital_actual"]
    avg_pct_diario = 0.015 # 1.5% diario estimado si ganas 0.4% por 3-4 trades
    # si tienes historial real, lo calculamos
    if data["historial_diario"]:
        total_gan = sum([h["gan"] for h in data["historial_diario"]])
        dias = len(data["historial_diario"])
        if dias>0 and capital>0:
            avg_pct_diario = (total_gan / capital) / dias
            avg_pct_diario = max(0.005, min(avg_pct_diario, 0.05)) # entre 0.5% y 5% diario

    proy=[]
    cap=capital
    for mes in range(1,31):
        # 30 dias por mes
        for _ in range(30):
            cap = cap * (1 + avg_pct_diario)
        proy.append({"mes":mes,"capital": round(cap,2), "ganancia": round(cap - capital,2)})
    return jsonify({"capital_inicial": capital, "pct_diario": round(avg_pct_diario*100,2), "proyeccion": proy})

@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}
.header{text-align:center;padding:12px;border:2px solid #ffcc00;border-radius:14px;background:#111;margin-bottom:8px}
.big{font-size:26px;font-weight:bold;color:#00ff88}
.circle{width:100px;height:100px;border-radius:50%;border:3px solid #00ff88;display:inline-flex;align-items:center;justify-content:center;flex-direction:column;margin:5px}
.card{background:#151515;border:1px solid #333;border-radius:12px;padding:10px;margin-bottom:8px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:6px;border-bottom:1px solid #333;text-align:left}
.btn{padding:6px 10px;border-radius:8px;border:none;font-weight:bold}
.btn-g{background:#00ff88;color:#000}
</style></head><body>
<div class=header>
<b style=color:#ffcc00;font-size:20px>💰 MÁQUINA BOLA DE NIEVE 💰</b><br><br>
<div style=display:flex;justify-content:space-around;flex-wrap:wrap>
<div class=circle><small>BASE</small><b>$<span id=base>0</span></b></div>
<div class=circle style=border-color:#ffcc00><small>CAPITAL AHORA</small><b>$<span id=cap>0</span></b></div>
<div class=circle><small>HOY</small><b class=big>$<span id=hoy>0</span></b></div>
<div class=circle style=border-color:#ffcc00><small>BOLA</small><b>$<span id=bola>0</span></b></div>
</div>
<div style=margin-top:8px>Acum Total: $<span id=acum>0</span> | Promedio diario: <span id=avg>0</span>% | TP: <span id=tp>0</span>%</div>
</div>

<div class=card>
<b>📈 HISTORIAL DIARIO DIARIO (BOLA DE NIEVE)</b>
<table><thead><tr><th>Fecha</th><th>Gan Día</th><th>Capital</th><th>Bola Siguiente</th></tr></thead><tbody id=hist></tbody></table>
</div>

<div class=card>
<b>🚀 PROYECCIÓN 30 MESES COMPUESTO</b><br><small>Si sigue ganando <span id=pct>0</span>% diario promedio</small>
<table><thead><tr><th>Mes</th><th>Capital</th><th>Ganancia</th></tr></thead><tbody id=proy></tbody></table>
</div>

<div class=card>
<b>Posiciones Abiertas (no cuentan como pérdida)</b>
<table><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Gan%</th></tr></thead><tbody id=pos></tbody></table>
</div>

<script>
async function load(){
 let r=await fetch('/api/state'); let s=await r.json();
 document.getElementById('base').innerText=s.base.toFixed(2);
 document.getElementById('cap').innerText=s.capital_actual.toFixed(2);
 document.getElementById('acum').innerText=s.gan_acum.toFixed(2);
 document.getElementById('hoy').innerText=s.gan_hoy.toFixed(2);
 document.getElementById('bola').innerText=s.bola_actual.toFixed(2);
 document.getElementById('tp').innerText=s.tp;
 document.getElementById('avg').innerText=(s.avg_diario / s.capital_actual *100).toFixed(2);

 let h=''; for(let d of s.historial.reverse()){
  h+=`<tr><td>${d.fecha}</td><td style=color:#00ff88>+$${d.gan.toFixed(2)}</td><td>$${d.capital.toFixed(2)}</td><td>$${(d.capital / s.max_entradas).toFixed(2)}</td></tr>`;
 }
 document.getElementById('hist').innerHTML=h||'<tr><td colspan=4>Hoy es el primer día - se guarda a las 10pm</td></tr>';

 let p=''; for(let pos of s.pos){
  p+=`<tr><td>${pos.sym}</td><td>${pos.entry.toFixed(2)}</td><td>${pos.ahora.toFixed(2)}</td><td>${pos.gan_pct.toFixed(2)}% abierta</td></tr>`;
 }
 document.getElementById('pos').innerHTML=p||'<tr><td colspan=4>Sin posiciones - Esperando RSI<32</td></tr>';

 let r2=await fetch('/api/proyeccion'); let pr=await r2.json();
 document.getElementById('pct').innerText=pr.pct_diario;
 let hp='';
 for(let m of pr.proyeccion){
  if(m.mes==1 || m.mes==6 || m.mes==12 || m.mes==24 || m.mes==30){
   hp+=`<tr style=${m.mes==30?'background:#ffcc0022;font-weight:bold':''}><td>${m.mes} meses</td><td>$${m.capital.toLocaleString()}</td><td style=color:#00ff88>+$${m.ganancia.toLocaleString()}</td></tr>`;
  }
 }
 document.getElementById('proy').innerHTML=hp;
}
load(); setInterval(load,10000);
</script></body></html>"""

@app.route('/webhook', methods=['POST','GET'])
def webhook():
    if request.method=='GET': return "ok",200
    d=request.json or {}
    if "message" in d:
        c=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
        if c not in data["alert_users"]: data["alert_users"].append(c)
        if "DASHBOARD" in t:
            base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
            bola=data["capital_actual"]/data["max_entradas"]
            tg(c,f"BOLA DE NIEVE\nCapital: ${data['capital_actual']:.2f}\nHoy: ${data['gan_hoy']:.2f}\nBola ahora: ${bola:.2f}\n{base}/dashboard")
        save()
    return {"ok":True}

@app.route('/api/buy/<sym>', methods=['POST'])
def buy(sym):
    sym=sym.upper()
    bola=data["capital_actual"]/data["max_entradas"]
    price=P(sym)
    data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price})
    data["capital_actual"]-=bola # lo tienes en posicion
    data["entradas"]+=1; save(); return {"ok":True}

def auto_loop():
    time.sleep(5)
    while True:
        try:
            # BOLA DE NIEVE: la bola crece porque capital_actual crece
            bola = data["capital_actual"] / data["max_entradas"] if data["max_entradas"] else 0
            for sym in data["coins"]:
                if not data["coins_activas"].get(sym,True): continue
                closes=C(sym)
                if not closes: continue
                rsi=RSI(closes); price=closes[-1]; ema=EMA(closes)
                if rsi<32 and price>ema*0.995 and len(data["pos"])<data["max_entradas"] and not any(p['sym']==sym for p in data["pos"]) and data["auto"]:
                    data["pos"].append({"sym":sym,"monto":bola,"entry":price,"ahora":price}); data["entradas"]+=1; data["capital_actual"]-=bola; save()
                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        gan=(price-p["entry"])/p["entry"]*100
                        if gan>=data["tp_bruto"]:
                            ganancia_mxn = p["monto"]*gan/100
                            # AQUI ESTA LA BOLA DE NIEVE - lo ganado se suma al capital
                            data["capital_actual"] += p["monto"] + ganancia_mxn
                            data["gan_acum_total"] += ganancia_mxn
                            data["gan_hoy"] += ganancia_mxn
                            data["salidas"]+=1; data["ganadas"]+=1
                            data["pos"].remove(p); save()
                            for u in data["alert_users"]:
                                tg(u,f"💰 BOLA NIEVE {sym} +{gan:.2f}% = +${ganancia_mxn:.2f}\nCapital ahora: ${data['capital_actual']:.2f}\nBola siguiente: ${data['capital_actual']/data['max_entradas']:.2f}")
            # CIERRE DIARIO 10PM - guarda historial
            now=datetime.now()
            if now.hour==4 and now.minute==0: # 10pm MX = 4am UTC
                fecha=now.strftime("%Y-%m-%d")
                # si no existe hoy en historial, lo agrega
                if not any(h["fecha"]==fecha for h in data["historial_diario"]):
                    data["historial_diario"].append({"fecha":fecha,"gan":data["gan_hoy"],"capital":data["capital_actual"]})
                    if len(data["historial_diario"])>90: data["historial_diario"]=data["historial_diario"][-90:]
                    total=data["capital_actual"]
                    for u in data["alert_users"]:
                        tg(u,f"📊 CIERRE DIARIO BOLA NIEVE {fecha}\nHoy: ${data['gan_hoy']:.2f}\nCapital: ${total:.2f}\nBola mañana: ${total/data['max_entradas']:.2f}\nAcum: ${data['gan_acum_total']:.2f}")
                    data["gan_hoy"]=0; save()
                time.sleep(60)
            time.sleep(120)
        except Exception as e:
            print(e); time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
