import os, json, requests, threading, time
from flask import Flask, request, jsonify
app = Flask(__name__)
FILE="bot_data.json"
data={"b":5000.0,"pos":[],"gan_total":0.0,"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"alert_users":[]}
CACHE={"prices":{},"ts":0}
def load():
    if os.path.exists(FILE):
        try: data.update(json.load(open(FILE)))
        except: pass
def save(): json.dump(data,open(FILE,'w'))
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
    return 100-(100/(1+g/l))

def AN(sym):
    closes=C(sym)
    if not closes: return 50, P(sym)
    return RSI(closes), closes[-1]

def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','')}"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 Dashboard","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/api/prices')
def api_prices():
    if time.time()-CACHE["ts"]<20 and CACHE["prices"]: return jsonify(CACHE["prices"])
    out={}
    for sym in data["coins"]:
        rsi,price=AN(sym)
        score=int(100-rsi) if rsi<50 else int(rsi)
        action="COMPRAR" if rsi<32 else "VENDER" if rsi>70 else "SOSTENER"
        out[sym]={"price":price,"rsi":round(rsi,1),"score":score,"action":action}
    CACHE["prices"]=out; CACHE["ts"]=time.time()
    return jsonify(out)

@app.route('/')
@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}.top{background:#111;padding:12px;border-radius:12px;border:1px solid #00ff88;display:flex;justify-content:space-between;margin-bottom:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.card{background:#151515;border:2px solid #ffcc00;border-radius:16px;padding:12px;min-height:90px}.card.buy{border-color:#00ff88}.card.sell{border-color:#ff4444}.score{float:right;border:2px solid #ffcc00;border-radius:10px;padding:4px 10px;color:#ffcc00;font-weight:bold}.skel{background:#222;height:70px;border-radius:10px;animation:pulse 1s infinite}@keyframes pulse{0%{opacity:.5}50%{opacity:1}}</style></head><body>
<div class=top><b style=color:#00ff88>V1002.26 MILLONARIO</b><span id=ld>⚡ Cargando RSI real...</span></div>
<div class=grid id=g><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div></div>
<script>
async function load(){
 try{
  let r=await fetch('/api/prices'); let d=await r.json();
  let h='';
  for(let s in d){
    let cls=d[s].rsi<32?'buy':d[s].rsi>70?'sell':'';
    h+=`<div class=card ${cls} onclick="location='/chart/${s}'"><b>${s} $${d[s].price.toFixed(2)}</b><span class=score>${d[s].score}</span><br><small>RSI ${d[s].rsi}</small><br><b style=color:#ffcc00>${d[s].action}</b><br><small>${d[s].rsi<32?'+2.5% / -2% lista':''}</small></div>`;
  }
  document.getElementById('g').innerHTML=h; document.getElementById('ld').innerText='✅ RSI Real Millonario';
 }catch(e){ document.getElementById('ld').innerText='Reintentando...'; }
}
load(); setInterval(load,30000);
</script></body></html>"""

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script><style>body{{background:#080808;color:#fff;margin:0}}#c{{width:100%;height:85vh}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between}}</style></head><body><div class=top><b>{sym}/USDT - RSI 32/70</b><a href="/dashboard"><button style=background:#00ff88;padding:8px 16px;border-radius:8px;border:none;font-weight:bold>Volver</button></a></div><div id=c></div><script>fetch("https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=150").then(r=>r.json()).then(kl=>{{let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));let ch=LightweightCharts.createChart(document.getElementById('c'),{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});let cs=ch.addCandlestickSeries();cs.setData(data);ch.timeScale().fitContent();}})</script></body></html>"""

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        c=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
        if c not in data["alert_users"]: data["alert_users"].append(c)
        if t in data["coins"] and len(data["pos"])<5 and not any(p['sym']==t for p in data["pos"]):
            rsi,price=AN(t); data["pos"].append({"sym":t,"monto":50,"gan":0,"precio_entry":price}); data["b"]-=50; save(); tg(c,f"✅ {t} COMPRADO ${price:.2f} RSI {rsi:.1f} | Logica +2.5%/-2%")
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(10)
    while True:
        try:
            for sym in data["coins"]:
                rsi,price=AN(sym)
                if rsi<32 and len(data["pos"])<5 and not any(p['sym']==sym for p in data["pos"]):
                    data["pos"].append({"sym":sym,"monto":50,"gan":0,"precio_entry":price}); data["b"]-=50; save()
                    for u in data["alert_users"]: tg(u,f"🤖 AUTO {sym} RSI {rsi:.1f} ${price:.2f} - Millonario")
                for p in data["pos"][:]:
                    if p["sym"]==sym:
                        gan=((price-p["precio_entry"])/p["precio_entry"])*100 if p.get("precio_entry") else 0
                        if gan>=2.5 or gan<=-2 or rsi>=72:
                            data["b"]+=50*(1+gan/100); data["gan_total"]+=50*gan/100; data["pos"].remove(p); save()
                            for u in data["alert_users"]: tg(u,f"💰 VENTA {sym} {gan:.2f}% RSI {rsi:.1f}")
            time.sleep(180)
        except: time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)),threaded=True)
