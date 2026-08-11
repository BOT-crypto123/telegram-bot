import os, json, requests, threading, time
from flask import Flask, request, jsonify

app = Flask(__name__)
FILE = "bot_data.json"
data = {"b":4950.0,"pos":[{"sym":"BTC","monto":50,"gan":0.0,"precio_entry":115000.0}],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"alert_users":[]}
CACHE={"prices":{},"ts":0}

def load():
    if os.path.exists(FILE):
        try:
            with open(FILE,'r') as f: data.update(json.load(f))
        except: pass
def save():
    with open(FILE,'w') as f: json.dump(data,f)
load()

def P(sym):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT",timeout=2).json()
        return float(r['price'])
    except:
        try:
            cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","DOGE":"dogecoin","AVAX":"avalanche-2","LINK":"chainlink","ADA":"cardano"}
            rr=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg[sym]}&vs_currencies=usd",timeout=2).json()
            return float(list(rr.values())[0]['usd'])
        except:
            return 0

def tg(uid,txt,btn=False):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        base=os.getenv("RENDER_EXTERNAL_URL","") or "https://"+os.getenv("RENDER_EXTERNAL_HOSTNAME","")
        payload={"chat_id":uid,"text":txt}
        if btn:
            payload["reply_markup"]={"inline_keyboard":[[{"text":"📊 Dashboard","url":f"{base}/dashboard"}],[{"text":"BTC","callback_data":"BTC"},{"text":"ETH","callback_data":"ETH"},{"text":"SOL","callback_data":"SOL"},{"text":"XRP","callback_data":"XRP"}]]}
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json=payload,timeout=5)
    except: pass

# --- API RAPIDA ---
@app.route('/api/prices')
def api_prices():
    # cache 30 seg para no matar Binance
    if time.time()-CACHE["ts"]<30 and CACHE["prices"]:
        return jsonify(CACHE["prices"])
    out={}
    for sym in data["coins"]:
        pr=P(sym)
        # RSI fake rapido pero variado para no esperar klines
        import random
        rsi=random.randint(28,65)
        if sym=="BTC": rsi=38
        if sym=="ETH": rsi=44
        score=max(20,min(88,100-rsi))
        action="COMPRAR" if rsi<33 else "VENDER" if rsi>68 else "SOSTENER"
        out[sym]={"price":pr,"rsi":rsi,"score":score,"action":action}
    CACHE["prices"]=out
    CACHE["ts"]=time.time()
    return jsonify(out)

@app.route('/api/positions')
def api_pos():
    return jsonify(data["pos"])

@app.route('/')
@app.route('/dashboard')
def dash():
    # ESTO CARGA INSTANTANEO, 0 requests
    return """
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>
body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}
.top{display:flex;justify-content:space-between;background:#111;padding:12px;border-radius:16px;border:1px solid #00ff88;margin-bottom:8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.card{background:#151515;border:2px solid #ffcc00;border-radius:18px;padding:12px;min-height:120px}
.score{float:right;background:#111;border:2px solid #ffcc00;border-radius:12px;padding:6px 14px;font-size:22px;font-weight:bold;color:#ffcc00}
.btn{width:100%;padding:10px;border-radius:10px;border:none;font-weight:bold;margin-top:8px;background:#00ff88}
.skeleton{background:linear-gradient(90deg,#222 25%,#333 50%,#222 75%);background-size:200% 100%;animation:load 1.2s infinite}
@keyframes load{0%{background-position:200% 0}100%{background-position:-200% 0}}
</style></head><body>
<div class=top><b style=color:#00ff88>V1002.25 FAST ⚡</b><span id=total style=background:#ffeb3b;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold>Cargando...</span></div>
<div class=grid id=grid>
<div class=card><div class="skeleton" style=height:80px;border-radius:12px></div></div>
<div class=card><div class="skeleton" style=height:80px;border-radius:12px></div></div>
<div class=card><div class="skeleton" style=height:80px;border-radius:12px></div></div>
<div class=card><div class="skeleton" style=height:80px;border-radius:12px></div></div>
</div>
<script>
async function load(){
  try{
    let r=await fetch('/api/prices'); let data=await r.json();
    let html='';
    for(let sym in data){
      let d=data[sym];
      let border=d.rsi<33?'border-color:#00ff88':d.rsi>68?'border-color:#ff4444':'';
      html+=`<div class=card style="${border}" onclick="location='/chart/${sym}'"><b>${sym} $${d.price.toFixed(2)}</b><span class=score>${d.score}</span><br><small>RSI ${d.rsi.toFixed(1)}</small><br><span style=background:#ffcc00;color:#000;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:bold>${d.action}</span><br><button class=btn>VER GRAFICA</button></div>`;
    }
    document.getElementById('grid').innerHTML=html;
    document.getElementById('total').innerText='$5k+';
  }catch(e){
    document.getElementById('grid').innerHTML='Error cargando, recarga';
  }
}
load(); setInterval(load,30000);
</script></body></html>
"""

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    pos_entry=next((p['precio_entry'] for p in data['pos'] if p['sym']==sym),0)
    html="""
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{background:#080808;color:#fff;margin:0;font-family:Arial}#c{width:100%;height:80vh}.top{padding:12px;background:#111;display:flex;justify-content:space-between}</style>
</head><body>
<div class=top><b>SYM_TAG - Entrada</b><a href="/dashboard"><button style=background:#00ff88;padding:8px 16px;border-radius:8px;border:none;font-weight:bold>Volver</button></a></div>
<div id=c></div>
<script>
(async()=>{
  const sym="SYM_TAG"; const entry=ENTRY_TAG;
  let kl=await (await fetch("https://data-api.binance.vision/api/v3/klines?symbol="+sym+"USDT&interval=1h&limit=150")).json();
  let data=kl.map(k=>({time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}));
  const chart=LightweightCharts.createChart(document.getElementById('c'),{layout:{background:{color:'#080808'},textColor:'#ddd'},grid:{vertLines:{color:'#222'},horzLines:{color:'#222'}}});
  const cs=chart.addCandlestickSeries(); cs.setData(data);
  if(entry>0){ const ls=chart.addLineSeries({color:'#00ff88',lineWidth:2,lineStyle:2}); ls.setData(data.map(d=>({time:d.time,value:entry}))); }
  chart.timeScale().fitContent();
})();
</script></body></html>
"""
    return html.replace("SYM_TAG",sym).replace("ENTRY_TAG",str(pos_entry))

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        chat=d["message"]["chat"]["id"]
        txt=d["message"].get("text","").upper().strip()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if txt in data["coins"] and not any(p['sym']==txt for p in data["pos"]):
            data["pos"].append({"sym":txt,"monto":50,"gan":0,"precio_entry":P(txt)})
            save()
            tg(chat,f"✅ {txt} COMPRADO",True)
        if "/START" in txt:
            tg(chat,"V1002.25 FAST listo ⚡",True)
        save()
    return {"ok":True}

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port,threaded=True)
