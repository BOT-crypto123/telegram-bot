import os, json, time, threading, requests, math
from flask import Flask, request
from datetime import datetime
import pytz

app = Flask(__name__)
FILE = "bot_data.json"
TRADE = 50.0
MAX_POS = 5

# DATA ORIGINAL
data = {"b":5000.0,"pos":[],"gan_total":0.0,"gan_hoy":0.0,"trades_hoy":0,"historial_diario":{},"alert_users":[],"scoring":{"BTC":5,"ETH":4,"SOL":4,"XRP":3,"AVAX":3,"LINK":3}}

def load():
    global data
    if os.path.exists(FILE):
        try:
            with open(FILE,'r') as f:
                j=json.load(f)
                for k in data:
                    if k in j: data[k]=j[k]
        except: pass
def save():
    with open(FILE,'w') as f: json.dump(data,f,indent=2)
load()
if data['b']+sum(p['monto'] for p in data['pos'])<4900:
    data['b']=5000-sum(p['monto'] for p in data['pos'])
    save()

TOKEN=os.getenv("TELEGRAM_TOKEN","")
TG=f"https://api.telegram.org/bot{TOKEN}"
def tg(uid,txt):
    try: requests.post(f"{TG}/sendMessage",json={"chat_id":uid,"text":txt},timeout=10)
    except: pass

# LOGICA ORIGINAL PRECIOS REALES
def P(sym):
    try:
        m={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","LINK":"LINKUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={m.get(sym,sym+'USDT')}",timeout=8).json()
        return float(r['price'])
    except: return 0

def C(sym):
    try:
        m={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","LINK":"LINKUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={m.get(sym,sym+'USDT')}&interval=1h&limit=80",timeout=8).json()
        closes=[float(x[4]) for x in r]
        return closes
    except: return []

def RSI(closes,period=14):
    if len(closes)<period+1: return 50
    gains=0; losses=0
    for i in range(1,period+1):
        d=closes[-i]-closes[-i-1]
        if d>0: gains+=d
        else: losses+=-d
    if losses==0: return 100
    rs=gains/losses
    return 100-(100/(1+rs))

def AN(sym):
    closes=C(sym)
    if not closes: return 50,0
    r=RSI(closes)
    # LOGICA ORIGINAL: rr < 32 compra
    return r, closes[-1]

def totals():
    val=0
    for p in data['pos']:
        price=P(p['sym'])
        if p.get('precio_entry',0)>0 and price>0:
            p['gan']=((price-p['precio_entry'])/p['precio_entry'])*100
        val+=p['monto']*(1+p.get('gan',0)/100)
    return data['b']+val, val

HTML="""
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#0e0e0e;color:#fff;font-family:Arial;padding:10px}
.card{background:#1c1c1c;padding:14px;border-radius:14px;margin:10px 0;border:1px solid #333}
.btn{background:#00ff88;color:#000;padding:9px 14px;border-radius:10px;text-decoration:none;font-weight:bold;margin:3px;display:inline-block}
.g{color:#00ff88}.r{color:#ff5555}
table{width:100%}td{padding:8px;border-bottom:1px solid #333}
</style></head><body>
<h2>🚀 V1002.15 MILLONARIO ORIGINAL LOGICA</h2>
<div class=card>
<h3>💰 Saldo: ${saldo:.2f} | Total: ${total:.2f} | Pos: {pos_len}/5</h3>
<p>Hoy: ${gan_hoy:.2f} | Trades: {trades} | Gan Total: ${gan_total:.2f}</p>
<a class=btn href=/dashboard>Refresh</a><a class=btn href=/public>Public VIP</a><a class=btn href=/reporte>Reporte</a>
</div>
<div class=card><h3>📈 Posiciones (RSI <32 compra / >70 venta)</h3><table>{rows}</table></div>
<div class=card><h3>🧠 Scoring Original</h3><p>{scoring}</p><p>Archivo: {file} ✅ Persistente</p><p>Lógica: Binance real + RSI 1h + 5 pos max $50</p></div>
</body></html>
"""

@app.route('/')
@app.route('/dashboard')
def dash():
    total,val=totals()
    rows=""
    for p in data['pos']:
        col="g" if p.get('gan',0)>=0 else "r"
        rows+=f"<tr><td><b>{p['sym']}</b></td><td>{P(p['sym']):.2f}</td><td class={col}>{p.get('gan',0):.2f}%</td><td>${p['monto']}</td><td>Entry ${p.get('precio_entry',0):.2f}</td></tr>"
    if not rows: rows="<tr><td colspan=5>Sin posiciones - manda BTC en Telegram o espera auto-compra RSI<32</td></tr>"
    return HTML.format(saldo=data['b'],total=total,pos_len=len(data['pos']),gan_hoy=data['gan_hoy'],trades=data['trades_hoy'],gan_total=data['gan_total'],rows=rows,scoring=str(data['scoring']),file=FILE)

@app.route('/public')
def public():
    total,val=totals()
    return f"<h2>Historial Publico Vicente - Plan Millonario</h2><p>Total: ${total:.2f} | Gan Total: ${data['gan_total']:.2f} | Objetivo 5-10% mensual</p><p>Posiciones: {len(data['pos'])}/5</p><p>Bot V1002.15 Logica Original</p>"

@app.route('/reporte')
def rep():
    total,val=totals()
    return f"Saldo ${data['b']:.2f} Total ${total:.2f} ValPos ${val:.2f} Pos {len(data['pos'])}/5".replace("\n","<br>")

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        txt=d["message"].get("text","").upper().strip()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if txt in data["scoring"]:
            if len(data["pos"])<MAX_POS:
                price=P(txt)
                data["pos"].append({"sym":txt,"monto":TRADE,"gan":0.0,"precio_entry":price})
                data["b"]-=TRADE
                data["trades_hoy"]+=1
                save(); tg(chat,f"✅ {txt} COMPRADO ${TRADE} a ${price:.2f} | Saldo ${data['b']:.2f} | RSI {AN(txt)[0]:.1f}")
            else: tg(chat,"❌ 5/5 lleno")
        if "/REPORTE" in txt:
            total,val=totals()
            pos_str="\n".join([f"{p['sym']} {p.get('gan',0):.2f}% Entry ${p.get('precio_entry',0):.2f}" for p in data['pos']]) or "Sin posiciones"
            tg(chat,f"📊 REPORTE V1002.15 ORIGINAL\nSaldo: ${data['b']:.2f}\nValor pos: ${val:.2f}\nTotal: ${total:.2f}\nPos: {len(data['pos'])}/5\n{pos_str}\nGuardado: {FILE}")
        if "/START" in txt: tg(chat,"V1002.15 ORIGINAL activo\nLogica: RSI<32 compra >70 venta\nComandos: BTC ETH SOL XRP AVAX LINK /reporte\nDashboard: /dashboard")
        save()
    return {"ok":True}

# AUTO LOOP ORIGINAL
def auto_loop():
    while True:
        try:
            for sym in list(data["scoring"].keys()):
                rsi,price=AN(sym)
                # AUTO COMPRA ORIGINAL
                if rsi<32 and len(data["pos"])<MAX_POS and not any(p['sym']==sym for p in data['pos']):
                    data["pos"].append({"sym":sym,"monto":TRADE,"gan":0.0,"precio_entry":price})
                    data["b"]-=TRADE
                    data["trades_hoy"]+=1
                    save()
                    for u in data["alert_users"]: tg(u,f"🤖 AUTO COMPRA {sym} RSI {rsi:.1f} ${price:.2f}")
                # AUTO VENTA
                for p in data["pos"][:]:
                    if p['sym']==sym:
                        if rsi>70 or p.get('gan',0)>=1.5 or p.get('gan',0)<=-3:
                            data["b"]+=p['monto']*(1+p.get('gan',0)/100)
                            data["gan_total"]+=p['monto']*p.get('gan',0)/100
                            data["gan_hoy"]+=p['monto']*p.get('gan',0)/100
                            data["pos"].remove(p)
                            save()
                            for u in data["alert_users"]: tg(u,f"💰 AUTO VENTA {sym} {p.get('gan',0):.2f}% RSI {rsi:.1f}")
            time.sleep(60)
        except Exception as e:
            print(e); time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
