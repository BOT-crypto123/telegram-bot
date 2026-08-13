# V38.8 8/10 FIX SYNTAX - B1 600 B2 850 RSI42 TP1.3%
import os, json, time, requests, threading, yfinance as yf
from flask import Flask, jsonify
from datetime import datetime
import pytz
NPOINT_ID="455c95667066c8b158d0"; NPOINT_URL=f"https://api.npoint.io/{NPOINT_ID}"
app=Flask(__name__)
B1=600; B2=850; RSI_BUY=42; TP=1.3; SL=18; MAX=6; RES=1500
MAP={"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
data={"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0,"com_total":0}
prices={}; rsis={"BTC":38,"ETH":42,"SOL":43,"XAUUSD":40,"NVDA":50,"TSLA":50}

def ny_open():
    try:
        ny=datetime.now(pytz.timezone('America/New_York'))
        if ny.weekday()>=5: return False
        return 7.5 <= ny.hour+ny.minute/60 <= 14.0
    except: return False

def puede(s):
    return True if s in ["BTC","ETH","SOL","XAUUSD"] else ny_open()

def get_price(sym):
    try:
        t=MAP.get(sym,sym)
        if sym=="XAUUSD":
            try:
                p=yf.Ticker("GC=F").fast_info.last_price
                if p and p>4000: return float(p)
            except: pass
            return 4369.0
        p=yf.Ticker(t).fast_info.last_price
        return float(p) if p else prices.get(sym,0)
    except: return prices.get(sym,0)

def load():
    global data
    try:
        r=requests.get(NPOINT_URL,timeout=8).json()
        if r.get("b",5000)<3000 and len(r.get("pos",[]))>=4:
            data={"b":5000,"pos":[],"alert_users":r.get("alert_users",[]),"auto":True,"gan_total":0,"com_total":0}; save(); return
        data={"b":r.get("b",5000),"pos":r.get("pos",[]),"alert_users":r.get("alert_users",[]),"auto":r.get("auto",True),"gan_total":r.get("gan_total",0),"com_total":r.get("com_total",0)}
        if data["b"]<3000 and len(data["pos"])==0: data["b"]=5000; save()
    except: pass

def save():
    try: requests.post(NPOINT_URL,json=data,timeout=8)
    except: pass

def trading_loop():
    while True:
        try:
            for s in ["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]:
                pr=get_price(s); prices[s]=pr
                if pr==0: continue
                for p in data["pos"][:]:
                    if p["sym"]!=s: continue
                    pct=(pr-p["entry"])/p["entry"]*100
                    if pct>=TP or pct<=-SL:
                        com=p["amt"]*0.006; gan=p["amt"]*pct/100; neto=gan-com
                        data["b"]+=p["amt"]+neto; data["gan_total"]+=neto; data["com_total"]+=com; data["pos"].remove(p); save()
                if not data["auto"]: continue
                if len(data["pos"])>=MAX: continue
                if len([x for x in data["pos"] if x["sym"]==s])>=2: continue
                if data["b"]-RES < (B1 if len([x for x in data["pos"] if x["sym"]==s])==0 else B2): continue
                if rsis.get(s,50)<RSI_BUY and puede(s):
                    amt=B1 if len([x for x in data["pos"] if x["sym"]==s])==0 else B2
                    nivel=1 if len([x for x in data["pos"] if x["sym"]==s])==0 else 2
                    data["pos"].append({"sym":s,"entry":pr,"price":pr,"amt":amt,"nivel":nivel,"flot":-3,"pct":0})
                    data["b"]-=amt; save()
            time.sleep(5)
        except: time.sleep(5)

@app.route("/")
def dashboard():
    html='<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}.card{background:#1a1a1a;border-radius:15px;padding:15px;margin-bottom:15px}.pos{border-left:4px solid #ff3b30;padding-left:10px;margin:10px 0}</style></head><body><div id="main" class="card">Cargando V38.8 8/10 FIX...</div><div id="pos"></div><div id="m"></div><script>async function refresh(){let r=await fetch("/api/estado");let d=await r.json();document.getElementById("main").innerHTML="<div style=text-align:center><div style=color:#ffcc00>MAQUINA V38.8 8/10 FIX</div><div style=color:#00ff88;font-size:11px>BTC/ETH/SOL/XAU 24/7 | B1 $600 B2 $850 RSI<"+d.rsi_buy+" TP "+d.tp+"%</div><div style=font-size:42px;font-weight:bold>$"+d.total.toFixed(2)+"</div><div>Saldo $"+d.b.toFixed(2)+" | Flot $"+d.flot.toFixed(2)+" | Pos "+d.pos.length+"/6</div><div>NY: "+(d.ny_open?"ABIERTO":"CERRADO")+" | AUTO "+(d.auto?"ON":"OFF")+"</div></div>";let h="";d.pos.forEach(p=>{h+="<div class=
