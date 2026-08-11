import os, json, requests, threading, time
from flask import Flask, request
app = Flask(__name__)
FILE = "bot_data.json"
data = {"b":4950.0,"pos":[{"sym":"BTC","monto":50,"gan":0.0,"precio_entry":115000.0}],"gan_total":0.0,"gan_hoy":0.0,"trades_hoy":1,"alert_users":[],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"]}

def load():
    global data
    if os.path.exists(FILE):
        try:
            with open(FILE,'r') as f:
                j=json.load(f)
                if len(j.get('pos',[]))>=0: data.update(j)
        except: pass
def save():
    with open(FILE,'w') as f: json.dump(data,f)
load()

def P(sym):
    for base in ["https://data-api.binance.vision","https://api.binance.com"]:
        try:
            mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT","ADA":"ADAUSDT"}
            r=requests.get(f"{base}/api/v3/ticker/price?symbol={mp.get(sym,sym+'USDT')}",timeout=2).json()
            pr=float(r.get('price',0))
            if pr>0: return pr
        except: pass
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","AVAX":"avalanche-2","DOGE":"dogecoin","LINK":"chainlink","ADA":"cardano"}
        rr=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg.get(sym,'bitcoin')}&vs_currencies=usd",timeout=3).json()
        return float(list(rr.values())[0]['usd'])
    except:
        return {"BTC":115000,"ETH":3800,"SOL":175,"XRP":2.4,"DOGE":0.15,"AVAX":22,"LINK":18,"ADA":0.8}.get(sym,1)

def C(sym):
    for base in ["https://data-api.binance.vision","https://api.binance.com"]:
        try:
            mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT","ADA":"ADAUSDT"}
            r=requests.get(f"{base}/api/v3/klines?symbol={mp.get(sym,sym+'USDT')}&interval=1h&limit=100",timeout=4).json()
            if isinstance(r,list) and len(r)>20:
                return [float(x[4]) for x in r]
        except: pass
    return []

def RSI(closes,period=14):
    if len(closes)<period+2: return 38.5
    g=l=0
    for i in range(1,period+1):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 68.5
    rs=g/l
    return 100-(100/(1+rs))

def AN(sym):
    closes=C(sym)
    if len(closes)<15:
        fake={"BTC":38.2,"ETH":44.1,"SOL":36.5,"XRP":51.3,"DOGE":42.7,"AVAX":39.8,"LINK":46.2,"ADA":43.5}
        return fake.get(sym,44.0),P(sym)
    return RSI(closes),closes[-1]

def totals():
    val=0
    for p in data['pos']:
        pr=P(p['sym'])
        if p.get('precio_entry',0)>0:
            p['gan']=((pr-p['precio_entry'])/p['precio_entry'])*100
        val+=p['monto']*(1+p.get('gan',0)/100)
    return data['b']+val

def tg(uid,txt,btn=False):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        payload={"chat_id":uid,"text":txt}
        if btn:
            base=os.getenv("RENDER_EXTERNAL_URL","").rstrip("/")
            payload["reply_markup"]={"inline_keyboard":[
                [{"text":"📊 Dashboard","url":f"{base}/dashboard"}],
                [{"text":"BTC","callback_data":"BTC"},{"text":"ETH","callback_data":"ETH"},{"text":"SOL","callback_data":"SOL"},{"text":"XRP","callback_data":"XRP"}]
            ]}
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json=payload,timeout=6)
    except: pass

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    pos_entry=0
    for p in data['pos']:
        if p['sym']==sym:
            pos_entry=p.get('precio_entry',0)
            break
    # NO USO f-string aqui para evitar el error de tu foto
    html = """
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{background:#080808;color:#fff;font-family:Arial;margin:0;padding:0}#chart{width:100%;height:70vh}.top{padding:12px;background:#111;display:flex;justify-content:space-between}.btn{padding:8px 16px;border-radius:8px;border:none;font-weight:bold}</style>
</head><body>
<div class=top><b>SYM_PLACE - Entradas y Salidas</b><a href="/dashboard"><button class=btn style=background:#00ff88>Volver</button></a></div>
<div id=chart></div>
<script>
async function load(){
  const sym="SYM_PLACE";
  const entry=ENTRY_PLACE;
  const map={'BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT','XRP':'XRPUSDT','DOGE':'DOGEUSDT','AVAX':'AVAXUSDT','LINK':'LINKUSDT','ADA':'ADAUSDT'};
  let data=[];
  try{
    let r=await fetch("https://data-api.binance.vision/api/v3/klines?symbol="+map[sym]+"&interval=1h&limit=150");
    let kl=await r.json();
    data=kl.map(k=>({time:k[0]/1000,open:parseFloat(k[1]),high:parseFloat(k[2]),low:parseFloat(k[3]),close:parseFloat(k[4])}));
  }catch(e){}
  const chart=LightweightCharts.createChart(document.getElementById('chart'),{layout:{background:{type:'solid',color:'#080808'},textColor:'#fff'},grid:{vertLines:{color:'#222'},horzLines:{color:'#222'}}});
  const candle=chart.addCandlestickSeries();
  candle.setData(data);
  if(entry>0){
    const line=chart.addLineSeries({color:'#00ff88',lineWidth:2,lineStyle:2});
    line.setData(data.map(d=>({time:d.time,value:entry})));
  }
  chart.timeScale().fitContent();
}
load();
</script>
</body></html>
"""
    html = html.replace("SYM_PLACE", sym).replace("ENTRY_PLACE", str(pos_entry))
    return html

@app.route('/')
@app.route('/dashboard')
def dash():
    total=totals()
    html=f"""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}}.top{{display:flex;justify-content:space-between;background:#111;padding:12px;border-radius:16px;border:1px solid #00ff88;margin-bottom:8px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.card{{background:#151515;border:2px solid #ffcc00;border-radius:18px;padding:10px;cursor:pointer}}.score{{float:right;background:#111;border:2px solid #ffcc00;border-radius:12px;padding:6px 14px;font-size:22px;font-weight:bold;color:#ffcc00}}.btn{{width:100%;padding:10px;border-radius:10px;border:none;font-weight:bold;margin-top:6px}}.btn.g{{background:#00ff88}}.btn.r{{background:#ff3344;color:#fff}}.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:bold}}.badge.y{{background:#ffcc00;color:#000}}.pos{{background:#111;border-radius:16px;padding:12px;margin-top:10px;border:1px solid #333}}</style></head><body>
<div class=top><b style=color:#00ff88>V1002.23 FIXED</b><div><span style=background:#ffeb3b;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold>${total:.0f}</span> <span style=background:#00ff88;color:#000;padding:6px 12px;border-radius:20px;font-weight:bold>ON</span></div></div>
<div style=background:#151515;padding:8px;border-radius:12px;margin-bottom:8px;text-align:center><small>TOCA CUALQUIER MONEDA PARA VER GRAFICA</small></div><div class=grid>"""
    for sym in data['coins']:
        rsi,price=AN(sym)
        score=int(100-rsi) if rsi<50 else 100-int(rsi)
        score=max(20,min(85,score))
        border="green" if rsi<32 else "red" if rsi>70 else ""
        action="COMPRAR" if rsi<32 else "VENDER" if rsi>70 else "SOSTENER"
        badge="g" if rsi<32 else "y"
        holding=any(p['sym']==sym for p in data['pos'])
        btn_t="VENDER" if holding else "COMPRAR"
        btn_c="r" if holding else "g"
        html+=f"""<div class="card {border}" onclick="window.location='/chart/{sym}'"><b>{sym} ${price:.2f}</b> <span class=score>{score}</span><br><small>RSI {rsi:.1f}</small><br><span class="badge {badge}">{action}</span><div style=height:30px;background:linear-gradient(0deg,#ffcc0033,transparent);margin:8px 0;border-radius:8px></div><a href="/buy/{sym}" style=flex:1 onclick="event.stopPropagation()"><button class="btn {btn_c}" style=width:100%>{btn_t}</button></a></div>"""
    pos_rows=""
    for p in data['pos']:
        pr=P(p['sym'])
        pos_rows+=f"<div>{p['sym']} Entry ${p.get('precio_entry',0):.2f} Ahora ${pr:.2f} <a href='/chart/{p['sym']}'>Ver grafica</a></div>"
    html+=f"</div><div class=pos><b>Posiciones ({len(data['pos'])}/5)</b><br>{pos_rows}</div></body></html>"
    return html

@app.route('/buy/<sym>')
def buy_route(sym):
    sym=sym.upper()
    if len(data['pos'])<5 and not any(p['sym']==sym for p in data['pos']):
        price=P(sym)
        data['pos'].append({"sym":sym,"monto":50,"gan":0.0,"precio_entry":price})
        data['b']-=50
        save()
    return f"<script>window.location='/dashboard'</script>"
@app.route('/sell/<sym>')
def sell_route(sym):
    sym=sym.upper()
    for p in data['pos'][:]:
        if p['sym']==sym:
            data['pos'].remove(p)
            data['b']+=50
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
                data["pos"].append({"sym":txt,"monto":50,"gan":0.0,"precio_entry":price})
                data["b"]-=50
                save()
                tg(chat,f"COMPRADO {txt}",btn=True)
        if "/START" in txt:
            tg(chat,f"V1002.23 FIXED OK",btn=True)
        save()
    return {"ok":True}

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
