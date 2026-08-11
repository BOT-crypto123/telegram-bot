import os, json, requests, time
from flask import Flask, request, jsonify
app = Flask(__name__)
FILE="bot_data.json"
data={"b":4950.0,"pos":[],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"alert_users":[]}
CACHE={"p":{},"ts":0}

def load():
    if os.path.exists(FILE):
        try: data.update(json.load(open(FILE)))
        except: pass
def save(): json.dump(data,open(FILE,'w'))
load()

def P(sym):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT",timeout=2).json()
        return float(r['price'])
    except: return {"BTC":114000,"ETH":3800,"SOL":170,"XRP":2.4,"DOGE":0.15,"AVAX":22,"LINK":18,"ADA":0.8}.get(sym,1)

def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','')}"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"📊 Dashboard","url":f"{base}/dashboard"}]]}},timeout=5)
    except: pass

@app.route('/api/prices')
def api_prices():
    if time.time()-CACHE["ts"]<25 and CACHE["p"]: return jsonify(CACHE["p"])
    out={}
    for s in data["coins"]:
        out[s]={"price":P(s),"rsi":35,"score":65,"action":"SOSTENER"}
    CACHE["p"]=out; CACHE["ts"]=time.time()
    return jsonify(out)

@app.route('/')
@app.route('/dashboard')
def dash():
    return """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}.top{background:#111;padding:12px;border-radius:12px;border:1px solid #00ff88;display:flex;justify-content:space-between;margin-bottom:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.card{background:#151515;border:2px solid #ffcc00;border-radius:16px;padding:12px;min-height:90px}.score{float:right;border:2px solid #ffcc00;border-radius:10px;padding:4px 10px;color:#ffcc00;font-weight:bold}.skel{background:#222;height:70px;border-radius:10px;animation:pulse 1s infinite}@keyframes pulse{0%{opacity:.5}100%{opacity:1}}</style></head><body>
<div class=top><b style=color:#00ff88>V1002.25 FAST</b><span id=ld>⚡ Cargando...</span></div>
<div class=grid id=g><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div></div>
<script>
async function load(){
 let r=await fetch('/api/prices'); let d=await r.json();
 let h=''; for(let s in d){ h+=`<div class=card onclick="location='/chart/${s}'"><b>${s} $${d[s].price.toFixed(2)}</b><span class=score>${d[s].score}</span><br><small>RSI ${d[s].rsi}</small><br><b style=color:#ffcc00>${d[s].action}</b></div>`}
 document.getElementById('g').innerHTML=h; document.getElementById('ld').innerText='✅ Listo';
}
load();
</script></body></html>"""

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script><style>body{{background:#080808;color:#fff;margin:0}}#c{{width:100%;height:80vh}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between}}</style></head><body><div class=top><b>{sym}/USDT</b><a href="/dashboard"><button style=background:#00ff88;padding:8px 16px;border-radius:8px;border:none;font-weight:bold>Volver</button></a></div><div id=c></div><script>fetch("https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=150").then(r=>r.json()).then(kl=>{{let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));let ch=LightweightCharts.createChart(document.getElementById('c'),{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});let cs=ch.addCandlestickSeries();cs.setData(data);ch.timeScale().fitContent();}})</script></body></html>"""

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        c=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
        if c not in data["alert_users"]: data["alert_users"].append(c)
        if t in data["coins"]: tg(c,f"✅ {t}")
        save()
    return {"ok":True}

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)),threaded=True)
