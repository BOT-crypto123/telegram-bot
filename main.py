import os, json, requests, threading, time
from flask import Flask, request

app = Flask(__name__)
FILE = "bot_data.json"
data = {"b":5000.0,"pos":[],"gan_total":0.0,"gan_hoy":0.0,"trades_hoy":0,"alert_users":[],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"scoring":{"BTC":5,"ETH":4,"SOL":4,"XRP":3,"AVAX":3,"LINK":3,"DOGE":3,"ADA":3}}

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

def P(sym):
    try:
        mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT","ADA":"ADAUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp.get(sym,sym+'USDT')}",timeout=3).json()
        price=float(r.get('price',0))
        if price>0: return price
    except: pass
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","AVAX":"avalanche-2","DOGE":"dogecoin","LINK":"chainlink","ADA":"cardano"}
        rr=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg.get(sym,'bitcoin')}&vs_currencies=usd",timeout=4).json()
        return float(list(rr.values())[0]['usd'])
    except:
        return {"BTC":115000,"ETH":3800,"SOL":175,"XRP":2.4,"DOGE":0.15,"AVAX":22,"LINK":18,"ADA":0.8}.get(sym,1)

def C(sym):
    try:
        mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT","ADA":"ADAUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={mp.get(sym,sym+'USDT')}&interval=1h&limit=80",timeout=5).json()
        return [float(x[4]) for x in r]
    except: return []

def RSI(closes,period=14):
    if len(closes)<period+1: return 50
    g=l=0
    for i in range(1,period+1):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 100
    return 100-(100/(1+g/l))

def AN(sym):
    closes=C(sym)
    if not closes: return 50,P(sym)
    return RSI(closes),closes[-1]

def totals():
    val=0
    for p in data['pos']:
        price=P(p['sym'])
        if p.get('precio_entry',0)>0 and price>0:
            p['gan']=((price-p['precio_entry'])/p['precio_entry'])*100
        val+=p['monto']*(1+p.get('gan',0)/100)
    return data['b']+val, val

def tg(uid,txt,btn=False):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        payload={"chat_id":uid,"text":txt}
        if btn:
            base=os.getenv("RENDER_EXTERNAL_URL","").rstrip("/") or "https://tu-bot.onrender.com"
            payload["reply_markup"]={
                "inline_keyboard":[
                    [{"text":"📊 Abrir Dashboard","url":f"{base}/dashboard"}],
                    [{"text":"🔍 CHECK AHORA","callback_data":"check"},{"text":"📈 REPORTE","callback_data":"reporte"}],
                    [{"text":"💰 BTC","callback_data":"BTC"},{"text":"💎 ETH","callback_data":"ETH"},{"text":"🚀 SOL","callback_data":"SOL"},{"text":"💧 XRP","callback_data":"XRP"}],
                    [{"text":"🐶 DOGE","callback_data":"DOGE"},{"text":"🏔 AVAX","callback_data":"AVAX"},{"text":"🔗 LINK","callback_data":"LINK"},{"text":"♠️ ADA","callback_data":"ADA"}]
                ]
            }
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json=payload,timeout=6)
    except: pass

@app.route('/')
@app.route('/dashboard')
def dash():
    total,val=totals()
    html=f"""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}}.top{{display:flex;justify-content:space-between;background:#111;padding:12px;border-radius:16px;border:1px solid #00ff88;margin-bottom:8px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.card{{background:#151515;border:2px solid #ffcc00;border-radius:18px;padding:10px}}.card.green{{border-color:#00ff88}}.card.red{{border-color:#ff4444}}.score{{float:right;background:#111;border:2px solid #ffcc00;border-radius:12px;padding:6px 14px;font-size:22px;font-weight:bold;color:#ffcc00}}.btn{{width:100%;padding:10px;border-radius:10px;border:none;font-weight:bold;margin-top:6px}}.btn.g{{background:#00ff88}}.btn.r{{background:#ff3344;color:#fff}}.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:bold}}.badge.y{{background:#ffcc00;color:#000}}.pos{{background:#111;border-radius:16px;padding:12px;margin-top:10px;border:1px solid #333}}</style></head><body>
<div class=top><b style=color:#00ff88>V1002.20 8 MONEDAS</b><div><span style=background:#ffeb3b;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold>${total:.0f}</span> <span style=background:#00ff88;color:#000;padding:6px 12px;border-radius:20px;font-weight:bold>ON</span></div></div>
<div style=background:#151515;padding:10px;border-radius:12px;margin-bottom:8px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px><div><small>Saldo</small><br><b>${data['b']:.0f}</b></div><div><small>Total</small><br><b>${total:.0f}</b> <small style=color:#00ff88>+${data['gan_total']:.2f}</small></div><div><small>Hoy</small><br><b>${data['gan_hoy']:.2f}</b> <small>{data['trades_hoy']} trades</small></div></div>
<div class=grid>"""
    for sym in data['coins']:
        rsi,price=AN(sym)
        score=int(100-rsi) if rsi<50 else int(rsi)
        if score>80: score=80
        if score<20: score=20
        holding=any(p['sym']==sym for p in data['pos'])
        border="green" if rsi<32 else "red" if rsi>70 else ""
        action="COMPRAR" if rsi<32 else "VENDER" if rsi>70 else "SOSTENER"
        badge="y"
        if rsi<32: badge="g"
        btn_c="g" if not holding else "r"
        btn_t="COMPRAR" if not holding else "VENDER"
        html+=f"""<div class="card {border}"><b>{sym} ${price:.2f}</b> <span class=score>{score}</span><br><small>SCORE {score} • RSI {rsi:.1f}</small><br><span class="badge {badge}">{action}</span><div style=height:40px;background:linear-gradient(0deg,#ffcc0033,transparent);margin:8px 0;border-radius:8px></div><a href="/buy/{sym}"><button class="btn {btn_c}">{btn_t}</button></a></div>"""
    pos_rows=""
    for p in data['pos']:
        price=P(p['sym'])
        col="#00ff88" if p.get('gan',0)>=0 else "#ff4444"
        pos_rows+=f"<div style=display:flex;justify-content:space-between;padding:6px;border-bottom:1px solid #222><span>{p['sym']} x1 <span style=color:{col}>{p.get('gan',0):.2f}%</span> Entry ${p.get('precio_entry',0):.2f}</span> <a href='/sell/{p['sym']}' style=background:#ff3344;color:#fff;padding:2px 8px;border-radius:6px;text-decoration:none;font-size:11px>VENDER</a></div>"
    if not pos_rows: pos_rows="Sin posiciones"
    html+=f"</div><div class=pos><b>Posiciones abiertas ({len(data['pos'])}/5) - 8 monedas</b><br><br>{pos_rows}<br><small>Archivo: {FILE} PERSISTENTE | 8 monedas BTC ETH SOL XRP DOGE AVAX LINK ADA</small></div></body></html>"
    return html

@app.route('/buy/<sym>')
def buy_route(sym):
    sym=sym.upper()
    if len(data['pos'])<5 and not any(p['sym']==sym for p in data['pos']):
        price=P(sym)
        data['pos'].append({"sym":sym,"monto":50,"gan":0.0,"precio_entry":price})
        data['b']-=50
        data['trades_hoy']+=1
        save()
    return f"<script>window.location='/dashboard'</script>"

@app.route('/sell/<sym>')
def sell_route(sym):
    sym=sym.upper()
    for p in data['pos'][:]:
        if p['sym']==sym:
            price=P(sym)
            gan=((price-p['precio_entry'])/p['precio_entry'])*100 if p.get('precio_entry',0)>0 else 0
            data['b']+=50*(1+gan/100)
            data['gan_total']+=50*gan/100
            data['pos'].remove(p)
            save()
    return f"<script>window.location='/dashboard'</script>"

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        txt=d["message"].get("text","").upper().strip()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if txt in data['coins']:
            if len(data['pos'])<5 and not any(p['sym']==txt for p in data['pos']):
                price=P(txt)
                rsi,_=AN(txt)
                data["pos"].append({"sym":txt,"monto":50,"gan":0.0,"precio_entry":price})
                data["b"]-=50
                data["trades_hoy"]+=1
                save()
                tg(chat,f"✅ {txt} COMPRADO $50 a ${price:.2f} | RSI {rsi:.1f}\nSaldo ${data['b']:.2f}",btn=True)
            else:
                tg(chat,f"❌ 5/5 lleno",btn=True)
        if "/REPORTE" in txt or txt=="/START" or txt=="START":
            total,val=totals()
            tg(chat,f"📊 V1002.20 8 MONEDAS\nSaldo: ${data['b']:.2f}\nTotal: ${total:.2f}\nPos: {len(data['pos'])}/5\n\n8 monedas: BTC ETH SOL XRP DOGE AVAX LINK ADA\nRSI<32 compra >70 venta\nDashboard abajo:",btn=True)
        save()
    if "callback_query" in d:
        chat=d["callback_query"]["message"]["chat"]["id"]
        cq=d["callback_query"]["data"].upper()
        if cq in data['coins']:
            if len(data['pos'])<5 and not any(p['sym']==cq for p in data['pos']):
                price=P(cq)
                rsi,_=AN(cq)
                data["pos"].append({"sym":cq,"monto":50,"gan":0.0,"precio_entry":price})
                data["b"]-=50
                save()
                tg(chat,f"✅ {cq} COMPRADO $50 a ${price:.2f} RSI {rsi:.1f}",btn=True)
        if cq=="REPORTE":
            total,val=totals()
            tg(chat,f"📊 Total ${total:.2f} Saldo ${data['b']:.2f} Pos {len(data['pos'])}/5",btn=True)
        if cq=="CHECK":
            total,val=totals()
            txt="CHECK:\n"
            for s in data['coins']:
                rsi,pr=AN(s)
                txt+=f"{s} ${pr:.2f} RSI {rsi:.1f}\n"
            tg(chat,txt,btn=True)
    return {"ok":True}

def auto_loop():
    while True:
        try:
            for sym in data['coins']:
                rsi,price=AN(sym)
                if rsi<32 and len(data['pos'])<5 and not any(p['sym']==sym for p in data['pos']):
                    data["pos"].append({"sym":sym,"monto":50,"gan":0.0,"precio_entry":price})
                    data["b"]-=50
                    save()
                    for u in data["alert_users"]: tg(u,f"🤖 AUTO COMPRA {sym} RSI {rsi:.1f}",btn=True)
            time.sleep(180)
        except: time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
