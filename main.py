import os, json, requests
from flask import Flask, request

app = Flask(__name__)
FILE = "bot_data.json"
data = {"b":5000.0,"pos":[],"gan_total":0.0,"gan_hoy":0.0,"trades_hoy":0,"alert_users":[],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"]}

def load():
    global data
    if os.path.exists(FILE):
        try:
            with open(FILE,'r') as f: data.update(json.load(f))
        except: pass
def save():
    with open(FILE,'w') as f: json.dump(data,f)
load()

def P(sym):
    try:
        mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT","ADA":"ADAUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp.get(sym,sym+'USDT')}",timeout=3).json()
        price=float(r.get('price',0))
        if price>0: return price
    except: pass
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","AVAX":"avalanche-2","DOGE":"dogecoin","LINK":"chainlink","ADA":"cardano"}
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg.get(sym,'bitcoin')}&vs_currencies=usd",timeout=4).json()
        return float(list(r.values())[0]['usd'])
    except:
        return {"BTC":115000,"ETH":3800,"SOL":175,"XRP":2.4,"DOGE":0.15,"AVAX":22,"LINK":18,"ADA":0.8}.get(sym,1)

def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt},timeout=6)
    except: pass

HTML_HEAD="""
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>
body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}
.top{display:flex;justify-content:space-between;background:#111;padding:12px;border-radius:16px;border:1px solid #00ff88;margin-bottom:8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.card{background:#151515;border:2px solid #ffcc00;border-radius:18px;padding:10px}
.card.green{border-color:#00ff88}
.card.red{border-color:#ff4444}
.score{float:right;background:#111;border:2px solid #ffcc00;border-radius:12px;padding:6px 14px;font-size:22px;font-weight:bold;color:#ffcc00}
.btn{width:100%;padding:10px;border-radius:10px;border:none;font-weight:bold;margin-top:6px}
.btn.g{background:#00ff88}.btn.r{background:#ff3344;color:#fff}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:bold}
.badge.y{background:#ffcc00;color:#000}.badge.g{background:#00ff88;color:#000}
.pos{background:#111;border-radius:16px;padding:12px;margin-top:10px;border:1px solid #333}
</style></head><body>
<div class=top><b style=color:#00ff88>V1002.18 VISUAL 24/7</b><div><span style=background:#ffeb3b;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold>${total:.0f}</span> <span style=background:#00ff88;color:#000;padding:6px 12px;border-radius:20px;font-weight:bold>ON</span></div></div>
<div class=grid>
"""

HTML_FOOT="""
</div>
<div class=pos><b>Posiciones abiertas ({pcount})</b><br><br>{pos_rows}
<p>Archivo: bot_data.json ✅ PERSISTENTE | Precio REAL FIX $0.00 | Plan Millonario FREE</p>
</div>
</body></html>
"""

def coin_card(sym):
    price=P(sym)
    # Simula score/rsi logica original
    import random
    score=70 if sym in ["SOL","BTC"] else 60 if sym in ["XRP","LINK"] else 50
    rsi=30 if score==70 else 20 if sym=="XRP" else 45
    holding=any(p['sym']==sym for p in data['pos'])
    border="green" if score>=70 else ""
    action="COMPRAR" if score>=70 and not holding else "SOSTENER" if score>=50 else "VENDER"
    btn_class="g" if (not holding and score>=60) or (holding and score<50) else "r"
    btn_text="COMPRAR" if not holding else "VENDER"
    if holding and score>=60: btn_text="VENDER"
    if not holding and score<50: btn_text="COMPRAR"

    return f"""
    <div class="card {border}">
    <b>{sym} ${price:.2f}</b> <span class=score>{score}</span><br>
    <small>SCORE {score} • RSI {rsi}</small><br>
    <span class="badge y">{action}</span>
    <div style=height:40px;background:linear-gradient(0deg,#ffcc0033,transparent);margin:8px 0;border-radius:8px></div>
    <button class="btn {btn_class}" onclick="fetch('/buy/{sym}')">{btn_text}</button>
    </div>
    """

@app.route('/')
@app.route('/dashboard')
def dash():
    total=data['b']+sum(p['monto'] for p in data['pos'])
    cards="".join([coin_card(s) for s in data['coins']])
    rows=""
    for p in data['pos']:
        rows+=f"{p['sym']} x1 {p.get('gan',0):.2f}% ${p['monto']} <span style=background:#ff3344;color:#fff;padding:2px 8px;border-radius:6px;font-size:11px>VENDER</span><br>"
    if not rows: rows="Sin posiciones - manda BTC en Telegram"
    return HTML_HEAD.replace("${total}",f"{total:.0f}") + cards + HTML_FOOT.format(pcount=len(data['pos']),pos_rows=rows)

@app.route('/buy/<sym>')
def buy_route(sym):
    sym=sym.upper()
    if len(data['pos'])<5 and not any(p['sym']==sym for p in data['pos']):
        data['pos'].append({"sym":sym,"monto":50,"gan":0.07})
        data['b']-=50
        save()
    total=data['b']+sum(p['monto'] for p in data['pos'])
    return f"Comprado {sym} Total {total}"

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        txt=d["message"].get("text","").upper().strip()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if txt in data['coins'] or txt in ["BTC","ETH","SOL","XRP"]:
            if len(data['pos'])<5 and not any(p['sym']==txt for p in data['pos']):
                price=P(txt)
                data["pos"].append({"sym":txt,"monto":50,"gan":0.0})
                data["b"]-=50
                save()
                tg(chat,f"✅ {txt} COMPRADO $50.0 a ${price:.2f} | Saldo ${data['b']:.2f}")
            else:
                tg(chat,f"❌ 5/5 lleno o ya tienes {txt}")
        if "/REPORTE" in txt:
            total=data['b']+sum(p['monto'] for p in data['pos'])
            tg(chat,f"📊 V1002.18 VISUAL\nSaldo: ${data['b']:.2f}\nTotal: ${total:.2f}\nPos: {len(data['pos'])}/5\nDashboard: /dashboard")
        save()
    return {"ok":True}

@app.route('/reporte')
def rep():
    total=data['b']+sum(p['monto'] for p in data['pos'])
    return f"Total {total}"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
