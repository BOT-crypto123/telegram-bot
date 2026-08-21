import os, json, requests, threading, time
from flask import Flask, request, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)
FILE="bot_data.json"
MX_TZ = pytz.timezone('America/Mexico_City')

# === CONFIG - ESA MISMA QUE PEDISTE ===
DEMO = True
CAPITAL_DEMO = 87.83
CAPITAL_REAL = 10060.05 # tu base 500 USD de la foto
MONTO_BOLA = 1677.0 # tu entrada de la foto
FEE = 0.001
TP_NETO = 0.3

data={
    "b": CAPITAL_REAL,
    "pos": [],
    "gan_total": 310.05,
    "gan_hoy": 0.0,
    "trades_hoy": 0,
    "gan_acumulada_2d": 310.05,
    "historial_2d": [],
    "coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],
    "alert_users":[],
    "auto": True
}
CACHE={"prices":{}, "ts":0, "btc_change":0}

def load():
    if os.path.exists(FILE):
        try: data.update(json.load(open(FILE)))
        except: pass
def save():
    try: json.dump(data, open(FILE,'w'))
    except: pass
load()

def P(sym):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT",timeout=3).json()
        return float(r['price'])
    except: return 0
def C(sym):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=80",timeout=5).json()
        return [float(x[4]) for x in r]
    except: return []
def RSI(closes,p=14):
    if len(closes)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 100
    rs=g/l if l!=0 else 0
    return 100-(100/(1+rs))
def EMA(closes,p=20):
    if len(closes)<p: return closes[-1] if closes else 0
    k=2/(p+1); ema=closes[0]
    for c in closes[1:]: ema=c*k+ema*(1-k)
    return ema
def BTC_change_1h():
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT",timeout=3).json()
        return float(r['priceChangePercent'])
    except: return 0
def AN(sym):
    closes=C(sym)
    if not closes: return 50, P(sym), 0, 0
    rsi=RSI(closes); price=closes[-1]; ema=EMA(closes,20)
    return rsi, price, ema, CACHE.get("btc_change",0)
def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 Dashboard","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

# === FIX 404: RENDER PEGA A / con HEAD Y GET ===
@app.route('/', methods=['GET','HEAD','POST'])
def root():
    # Si es POST es Telegram que le pega a / en vez de /webhook
    if request.method=='POST':
        return webhook()
    return "V1002.32 MILLONARIO LIVE", 200

@app.route('/api/prices')
def api_prices():
    if time.time()-CACHE["ts"]<15 and CACHE["prices"]: return jsonify(CACHE["prices"])
    out={}; CACHE["btc_change"]=BTC_change_1h()
    for sym in data["coins"]:
        rsi,price,ema,btc_ch=AN(sym)
        score=int(100-rsi) if rsi<50 else int(rsi)
        bloqueado = (price < ema*0.995) or (CACHE["btc_change"] < -1.5)
        action="COMPRAR" if rsi<32 and not bloqueado else "VENDER" if rsi>70 else "SOSTENER"
        if bloqueado and rsi<32: action="BLOQUEADO"
        out[sym]={"price":price,"rsi":round(rsi,1),"ema":round(ema,2),"score":score,"action":action,"btc_ch":round(CACHE["btc_change"],2)}
    CACHE["prices"]=out; CACHE["ts"]=time.time()
    return jsonify(out)

@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}
.top{background:#111;padding:12px;border-radius:12px;border:1px solid #00ff88;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.circle{border:2px solid #00ff88;border-radius:50%;width:70px;height:70px;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#00ff88;font-weight:bold}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.card{background:#151515;border:2px solid #ffcc00;border-radius:16px;padding:12px;min-height:95px}
.card.buy{border-color:#00ff88}.card.sell{border-color:#ff4444}.card.block{border-color:#555}
.score{float:right;border:2px solid #ffcc00;border-radius:10px;padding:4px 10px;color:#ffcc00;font-weight:bold}
table{width:100%;background:#151515;border-radius:12px;margin-top:10px;border-collapse:collapse}
th,td{padding:8px;text-align:left;border-bottom:1px solid #333;font-size:13px}
.btn{background:#00ff88;color:#000;border:none;padding:6px 12px;border-radius:8px;font-weight:bold;cursor:pointer}
.btn-red{background:#ff4444;color:#fff;border:none;padding:6px 12px;border-radius:8px;font-weight:bold}
</style></head><body>
<div class=top>
<div><b style=color:#00ff88>V1002.32 MILLONARIO</b><br><small id=mode>BASE $10060.05</small></div>
<div class=circle><span id=acum>$0.00</span><small>ACUM 2D</small></div>
<div><small>Saldo: $<span id=saldo>0</span><br>Total: $<span id=total>0</span><br>Hoy: $<span id=hoy>0</span> (<span id=trades>0</span>)</small></div>
<div><button class=btn onclick="toggleAuto()" id=autoBtn>AUTO ON</button></div>
</div>
<div class=grid id=g></div>
<table id=posTable><thead><tr><th>Moneda</th><th>Entry</th><th>Ahora</th><th>Gan%</th><th>Max</th><th>Acción</th></tr></thead><tbody></tbody></table>
<script>
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json(); let h='';
 for(let s in d){
  let cls=d[s].action=='COMPRAR'?'buy':d[s].action=='VENDER'?'sell':d[s].action=='BLOQUEADO'?'block':'';
  h+=`<div class=card ${cls}><b>${s} $${d[s].price.toFixed(2)}</b><span class=score>${d[s].score}</span><br><small>RSI ${d[s].rsi} | EMA ${d[s].ema}</small><br><b style=color:${d[s].action=='COMPRAR'?'#00ff88':d[s].action=='BLOQUEADO'?'#888':'#ffcc00'}>${d[s].action}</b><br><small>BTC ${d[s].btc_ch}%</small><br><button class=btn onclick="buy('${s}')">COMPRAR $${1677}</button> <a href='/chart/${s}'><button class=btn>GRÁFICA</button></a></div>`;
 }
 document.getElementById('g').innerHTML=h;
 let r2=await fetch('/api/state'); let s2=await r2.json();
 document.getElementById('saldo').innerText=s2.b.toFixed(2);
 document.getElementById('total').innerText=s2.total.toFixed(2);
 document.getElementById('hoy').innerText=s2.gan_hoy.toFixed(2);
 document.getElementById('trades').innerText=s2.trades_hoy;
 document.getElementById('acum').innerText='$'+s2.gan_acumulada_2d.toFixed(2);
 document.getElementById('autoBtn').innerText=s2.auto?'AUTO ON':'AUTO OFF';
 document.getElementById('mode').innerText=`BASE $${s2.total.toFixed(2)} MXN`;
 let tbody=''; for(let p of s2.pos){ tbody+=`<tr><td>${p.sym}</td><td>$${p.precio_entry.toFixed(2)}</td><td>$${p.precio_now.toFixed(2)}</td><td style=color:${p.gan>=0?'#00ff88':'#ff4444'}>${p.gan.toFixed(2)}%</td><td>${p.max_gan.toFixed(2)}%</td><td><button class=btn-red onclick="sell('${p.sym}')">VENDER</button></td></tr>`; }
 document.querySelector('#posTable tbody').innerHTML=tbody||'<tr><td colspan=6 style=text-align:center;color:#888>Sin posiciones - Esperando RSI<32</td></tr>';
}
async function buy(sym){ await fetch('/api/buy/'+sym,{method:'POST'}); load(); }
async function sell(sym){ await fetch('/api/sell/'+sym,{method:'POST'}); load(); }
async function toggleAuto(){ await fetch('/api/toggle_auto',{method:'POST'}); load(); }
load(); setInterval(load,15000);
</script></body></html>"""

@app.route('/api/state')
def state():
    total=data["b"]+sum([p["monto"] for p in data["pos"]])+data["gan_total"]
    for p in data["pos"]:
        rsi,price,ema,_=AN(p["sym"]); p["precio_now"]=price
        gan=((price-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"] else 0
        p["gan"]=gan
        if gan>p.get("max_gan",0): p["max_gan"]=gan
    return jsonify({"b":data["b"],"total":total,"gan_total":data["gan_total"],"gan_hoy":data["gan_hoy"],"trades_hoy":data["trades_hoy"],"gan_acumulada_2d":data["gan_acumulada_2d"],"pos":data["pos"],"auto":data["auto"],"demo":DEMO})

@app.route('/api/buy/<sym>', methods=['POST'])
def api_buy(sym):
    sym=sym.upper()
    if len(data["pos"])>=5 or any(p['sym']==sym for p in data["pos"]): return {"ok":False}
    rsi,price,ema,_=AN(sym)
    data["pos"].append({"sym":sym,"monto":MONTO_BOLA,"precio_entry":price,"precio_now":price,"gan":0,"max_gan":0,"rsi_entry":rsi})
    data["b"]-=MONTO_BOLA; save(); return {"ok":True}

@app.route('/api/sell/<sym>', methods=['POST'])
def api_sell(sym):
    sym=sym.upper()
    for p in data["pos"][:]:
        if p["sym"]==sym:
            rsi,price,ema,_=AN(sym); gan=((price-p["precio_entry"])/p["precio_entry"]*100); neto=gan-(FEE*2*100)
            data["b"]+=p["monto"]*(1+gan/100); data["gan_total"]+=p["monto"]*gan/100; data["gan_hoy"]+=p["monto"]*gan/100; data["gan_acumulada_2d"]+=p["monto"]*gan/100; data["trades_hoy"]+=1
            data["pos"].remove(p); save()
            for u in data["alert_users"]: tg(u,f"💰 VENTA {sym} {gan:.2f}% Bruto | {neto:.2f}% Neto")
    return {"ok":True}

@app.route('/api/toggle_auto', methods=['POST'])
def toggle_auto():
    data["auto"]=not data["auto"]; save(); return {"auto":data["auto"]}

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script></head><body style=background:#080808;color:#fff;margin:0><div style=padding:12px;background:#111;display:flex;justify-content:space-between><b>{sym}/USDT RSI 32/70 EMA20 + BTC -1.5%</b><a href="/dashboard"><button style=background:#00ff88;padding:8px 16px;border-radius:8px;border:none;font-weight:bold>Volver</button></a></div><div id=c style=width:100%;height:85vh></div><script>fetch("https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=150").then(r=>r.json()).then(kl=>{{let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));let ch=LightweightCharts.createChart(document.getElementById('c'),{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});let cs=ch.addCandlestickSeries();cs.setData(data);ch.timeScale().fitContent();}})</script></body></html>"""

@app.route('/webhook', methods=['POST','GET'])
@app.route('/telegram', methods=['POST','GET'])
def webhook():
    if request.method=='GET': return "webhook ok", 200
    d=request.json or {}
    if "message" in d:
        c=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
        if c not in data["alert_users"]: data["alert_users"].append(c)
        # FIX: DASHBOARD como en tu captura 2:38 PM
        if "DASHBOARD" in t or "/START" in t or t=="START":
            total=data["b"]+data.get("gan_total",0)
            base=os.getenv("RENDER_EXTERNAL_URL","") or "https://telegram-bot-cijp.onrender.com"
            tg(c, f"BASE 500 USD ${total:.2f} MXN\n{base}/dashboard")
        elif t in data["coins"]:
            if len(data["pos"])<5 and not any(p['sym']==t for p in data["pos"]):
                rsi,price,ema,_=AN(t); data["pos"].append({"sym":t,"monto":MONTO_BOLA,"precio_entry":price,"precio_now":price,"gan":0,"max_gan":0,"rsi_entry":rsi}); data["b"]-=MONTO_BOLA; save(); tg(c,f"✅ {t} COMPRADO ${price:.2f} RSI {rsi:.1f} EMA {ema:.2f} | Bola ${MONTO_BOLA}")
        elif t.startswith("VENDER"):
            sym=t.split()[-1] if len(t.split())>1 else ""
            if sym in data["coins"]:
                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        rsi,price,_,_=AN(sym); gan=((price-p["precio_entry"])/p["precio_entry"]*100); data["b"]+=p["monto"]*(1+gan/100); data["gan_total"]+=p["monto"]*gan/100; data["gan_hoy"]+=p["monto"]*gan/100; data["gan_acumulada_2d"]+=p["monto"]*gan/100; data["trades_hoy"]+=1; data["pos"].remove(p); save(); tg(c,f"💰 VENTA {sym} {gan:.2f}%")
        elif "/REPORTE" in t or t=="REPORTE":
            total=data["b"]+sum([p["monto"] for p in data["pos"]])+data["gan_total"]
            txt=f"📊 REPORTE MILLONARIO\nTotal: ${total:.2f} MXN\nEntrada: ${MONTO_BOLA} MXN\nAcum: ${data['gan_acumulada_2d']:.2f} MXN\nFee 0.10%+0.10% descontado\nhttps://telegram-bot-cijp.onrender.com/dashboard"
            tg(c,txt)
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(10)
    while True:
        try:
            if not data["auto"]: time.sleep(10); continue
            for sym in data["coins"]:
                rsi,price,ema,btc_ch=AN(sym)
                if rsi<32 and price>ema*0.995 and CACHE["btc_change"]>-1.5 and len(data["pos"])<5 and not any(p['sym']==sym for p in data["pos"]):
                    data["pos"].append({"sym":sym,"monto":MONTO_BOLA,"precio_entry":price,"precio_now":price,"gan":0,"max_gan":0,"rsi_entry":rsi}); data["b"]-=MONTO_BOLA; save()
                    for u in data["alert_users"]: tg(u,f"🤖 AUTO {sym} RSI {rsi:.1f} ${price:.2f} EMA {ema:.2f} BTC {CACHE['btc_change']:.2f}%")
                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        gan=((price-p["precio_entry"])/p["precio_entry"]*100); neto=gan-(FEE*2*100); max_gan=p.get("max_gan",0)
                        sell=False
                        if neto>=TP_NETO: sell=True
                        if gan>=2.5 and rsi<60: sell=True
                        if gan>=3.5 and rsi>60: sell=True
                        if gan<=-2: sell=True
                        if rsi>=74: sell=True
                        if max_gan>=4 and gan<=max_gan-1: sell=True
                        if sell:
                            data["b"]+=p["monto"]*(1+gan/100); data["gan_total"]+=p["monto"]*gan/100; data["gan_hoy"]+=p["monto"]*gan/100; data["gan_acumulada_2d"]+=p["monto"]*gan/100; data["trades_hoy"]+=1; data["pos"].remove(p); save()
                            for u in data["alert_users"]: tg(u,f"💰 VENTA AUTO {sym} Bruto {gan:.2f}% Neto {neto:.2f}% RSI {rsi:.1f} Max {max_gan:.2f}%")
            now=datetime.now(MX_TZ)
            if now.hour==22 and now.minute==0:
                data["historial_2d"].append({"fecha":now.strftime("%Y-%m-%d"),"gan":data["gan_hoy"]})
                if len(data["historial_2d"])>2: data["historial_2d"]=data["historial_2d"][-2:]
                data["gan_acumulada_2d"]=sum([h["gan"] for h in data["historial_2d"]])
                total=data["b"]+sum([p["monto"] for p in data["pos"]])+data["gan_total"]
                for u in data["alert_users"]: tg(u,f"📊 REPORTE 10PM {now.strftime('%Y-%m-%d')}\nSaldo ${data['b']:.2f}\nTotal ${total:.2f}\nGan Hoy ${data['gan_hoy']:.2f}\nAcum 2D VERDE ${data['gan_acumulada_2d']:.2f}\nTrades {data['trades_hoy']}")
                data["gan_hoy"]=0; data["trades_hoy"]=0; save(); time.sleep(60)
            time.sleep(180)
        except Exception as e:
            print(e); time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)),threaded=True)
