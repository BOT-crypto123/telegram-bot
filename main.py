import os, json, requests, threading, time
from flask import Flask, request

app = Flask(__name__)
FILE = "bot_data.json"
data = {"b":5000.0,"pos":[],"gan_total":0.0,"gan_hoy":0.0,"trades_hoy":0,"alert_users":[],"scoring":{"BTC":5,"ETH":4,"SOL":4,"XRP":3,"AVAX":3,"LINK":3}}

def load():
    global data
    if os.path.exists(FILE):
        try:
            with open(FILE,'r') as f: data=json.load(f)
        except: pass
def save():
    try:
        with open(FILE,'w') as f: json.dump(data,f)
    except: pass
load()

def P(sym):
    try:
        mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp.get(sym,sym+'USDT')}",timeout=4).json()
        price=float(r.get('price',0))
        if price>0: return price
    except: pass
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","AVAX":"avalanche-2","DOGE":"dogecoin","LINK":"chainlink"}
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg.get(sym,'bitcoin')}&vs_currencies=usd",timeout=5).json()
        return float(list(r.values())[0]['usd'])
    except:
        return 115000.0 if sym=="BTC" else 3800.0 if sym=="ETH" else 175.0 if sym=="SOL" else 2.4 if sym=="XRP" else 22.0

def C(sym):
    try:
        mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={mp.get(sym,sym+'USDT')}&interval=1h&limit=80",timeout=6).json()
        return [float(x[4]) for x in r]
    except: return []

def RSI(closes,period=14):
    if len(closes)<period+1: return 28.0
    gains=0; losses=0
    for i in range(1,period+1):
        d=closes[-i]-closes[-i-1]
        if d>0: gains+=d
        else: losses+=-d
    if losses==0: return 70.0
    rs=gains/losses
    return 100-(100/(1+rs))

def totals():
    total=data['b']+sum(p['monto']*(1+p.get('gan',0)/100) for p in data['pos'])
    return total

def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt},timeout=8)
    except: pass

@app.route('/')
@app.route('/dashboard')
def dash():
    total=totals()
    rows=""
    for p in data['pos']:
        price=P(p['sym'])
        rows+=f"{p['sym']} ${price:.2f} Gan {p.get('gan',0):.2f}%<br>"
    if not rows: rows="Sin posiciones - manda BTC"
    return f"""
    <html><body style=background:#111;color:#fff;font-family:Arial;padding:20px>
    <h2>V1002.17 FIXED - ${total:.2f}</h2>
    <p>Saldo: ${data['b']:.2f} | Pos: {len(data['pos'])}/5</p>
    <p>Archivo: {FILE} PERSISTENTE</p>
    <p>{rows}</p>
    <p>Plan Millonario FREE activo</p>
    </body></html>
    """

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        txt=d["message"].get("text","").upper().strip()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if txt in data["scoring"]:
            if len(data["pos"])<5:
                price=P(txt)
                closes=C(txt)
                rsi=RSI(closes) if closes else 28.5
                data["pos"].append({"sym":txt,"monto":50.0,"gan":0.0,"precio_entry":price})
                data["b"]-=50
                data["trades_hoy"]+=1
                save()
                tg(chat,f"✅ {txt} COMPRADO $50.0 a ${price:.2f} | Saldo ${data['b']:.2f} | RSI {rsi:.1f}")
            else:
                tg(chat,f"❌ 5/5 lleno")
        if "/REPORTE" in txt:
            total=totals()
            tg(chat,f"📊 REPORTE V1002.17\nSaldo: ${data['b']:.2f}\nTotal: ${total:.2f}\nPos: {len(data['pos'])}/5\nArchivo: {FILE} FIX $0.00")
        if "/START" in txt:
            tg(chat,f"V1002.17 FIXED activo\nSaldo $5k\nComandos BTC ETH SOL XRP\nDashboard /dashboard")
        save()
    return {"ok":True}

@app.route('/reporte')
def rep():
    return f"OK {totals():.2f}"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
