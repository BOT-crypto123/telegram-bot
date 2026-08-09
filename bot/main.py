import os, json, time, threading, requests
from flask import Flask, request
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "trades.json"
app = Flask(__name__)

def load_trades():
    try:
        with open(CHAT_FILE,"r") as f:
            return json.load(f)
    except:
        return {"trades":[],"balance":0,"chat_id":None}

def save_trades(d):
    with open(CHAT_FILE,"w") as f:
        json.dump(d,f)

def resumen_texto():
    d=load_trades()
    bal=d.get("balance",0)
    trades=d.get("trades",[])
    gan=sum(1 for t in trades if t.get("pnl",0)>0)
    per=len(trades)-gan
    hoy=datetime.now(pytz.timezone("America/Mexico_City")).strftime("%d/%m/%Y")
    return f"RESUMEN {hoy} - 10PM Balance: ${bal:.2f} Trades: {len(trades)} Gan: {gan} Per: {per}"

def send_msg(chat_id,text):
    if not TOKEN or not chat_id:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":chat_id,"text":text})
    except:
        pass

HTML = """<!DOCTYPE html><html lang=es><head><meta charset=UTF-8><meta name=viewport content="width=device-width, initial-scale=1.0"><title>JOHAN V503</title><script src=https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js></script><style>body{background:#050508;color:#fff;margin:0;font-family:Arial}.header{padding:12px;background:#0e0e14;display:flex;justify-content:space-between}.prices{display:flex;justify-content:space-between;padding:16px;background:#0a0a0f}#chartWrap{height:45vh;margin:10px;background:#0e0e14;border-radius:16px;border:1px solid #222}#chart{width:100%;height:100%}.btns{display:flex;gap:10px;padding:14px}.b{flex:1;padding:18px;border-radius:14px;border:none;font-weight:900;font-size:18px}.up{background:#7ef7cc;color:#000}.down{background:#ff4d5a;color:#fff}.signal{margin:10px;padding:12px;text-align:center;border-radius:12px;background:#1a1a22}</style></head><body><div class=header><b>BTC 15min LIVE - JOHAN V503</b><span id=clock></span></div><div class=prices><div><small>Price to beat</small><div id=priceBeat style=font-size:26px;font-weight:900>$0.00</div></div><div style=text-align:right><small>Current <span id=diff></span></small><div id=priceCur style=font-size:26px;font-weight:900>$0.00</div></div></div><div id=chartWrap><div id=chart></div></div><div class=signal id=signal>ANALIZANDO...</div><div class=btns><button class=b up id=btnUp>Up</button><button class=b down id=btnDown>Down</button></div><script>
const chart=LightweightCharts.createChart(document.getElementById("chart"),{layout:{background:{color:"#0e0e14"},textColor:"#555"},grid:{vertLines:{color:"#15151e"},horzLines:{color:"#15151e"}},width:document.getElementById("chartWrap").clientWidth,height:document.getElementById("chartWrap").clientHeight});
const line=chart.addLineSeries({color:"#ffb020",lineWidth:2});
let priceBeat=0,lastPrice=0;
async function init(){let r=await fetch("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60");let j=(await r.json()).reverse();priceBeat=j[Math.floor(j.length/2)][4];document.getElementById("priceBeat").innerText="$"+priceBeat.toFixed(2);line.setData(j.map(c=>({time:c[0],value:c[4]})));}
init();
let ws=new WebSocket("wss://ws-feed.exchange.coinbase.com");ws.onopen=()=>ws.send(JSON.stringify({type:"subscribe",product_ids:["BTC-USD"],channels:["ticker"]}));ws.onmessage=e=>{let m=JSON.parse(e.data);if(!m.price)return;lastPrice=parseFloat(m.price);document.getElementById("priceCur").innerText="$"+lastPrice.toFixed(2);let d=lastPrice-priceBeat;document.getElementById("diff").innerText=(d>=0?"UP ":"DOWN ")+"$"+Math.abs(d).toFixed(2);line.update({time:Math.floor(Date.now()/1000),value:lastPrice});let up=Math.max(5,Math.min(95,50+d/10));document.getElementById("btnUp").innerText="Up "+up.toFixed(0)+"%";document.getElementById("btnDown").innerText="Down "+(100-up).toFixed(0)+"%";};
setInterval(()=>{document.getElementById("clock").innerText=new Date().toLocaleTimeString();},1000);
</script></body></html>"""

@app.route("/")
def home():
    return HTML

@app.route("/api/balance")
def api_bal():
    d=load_trades()
    return {"balance":d.get("balance",0),"trades":len(d.get("trades",[]))}

@app.route("/api/trade", methods=["POST"])
def api_trade():
    data=request.get_json(silent=True) or {}
    d=load_trades()
    price=float(data.get("price",0))
    last = d["trades"][-1] if d["trades"] and d["trades"][-1].get("open") else None
    if not last:
        d["trades"].append({"open":True,"entry":price,"dir":data.get("dir"),"time":str(datetime.now())})
    else:
        pnl = (price - last["entry"]) if last["dir"]=="UP" else (last["entry"]-price)
        last["closed"]=True
        last["exit"]=price
        last["pnl"]=pnl
        last["open"]=False
        d["balance"]+=pnl
        d["trades"][-1]=last
    save_trades(d)
    return {"ok":True}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data=request.get_json(silent=True) or {}
        msg=data.get("message",{})
        chat_id=msg.get("chat",{}).get("id")
        text=msg.get("text","")
        d=load_trades()
        if chat_id:
            d["chat_id"]=chat_id
            save_trades(d)
        if text in ["/balance","/ganancias","/resumen","/reporte"]:
            send_msg(chat_id,resumen_texto())
    except Exception as e:
        print(e)
    return "ok"

def loop_10pm():
    tz=pytz.timezone("America/Mexico_City")
    while True:
        now=datetime.now(tz)
        if now.hour==22 and now.minute==0:
            d=load_trades()
            if d
