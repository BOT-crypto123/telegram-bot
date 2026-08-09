import os,requests,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or ""
print("V210 TOKEN",len(TOKEN),flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b210.json"

def load():
    if os.path.exists(FILE):
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))

load()
print("V210 LOADED",flush=True)

def price(s):
    u="https://api.coinbase.com/v2/prices/"
    u=u+s+"-USD/spot"
    r=requests.get(u,timeout=8).json()
    a=r.get("data",{}).get("amount","0")
    return float(a)

def candles(sym):
    u="https://api.exchange.coinbase.com/"
    u=u+"products/"+sym+"-USD/candles"
    u=u+"?granularity=60"
    h={"User-Agent":"M"}
    r=requests.get(u,headers=h,timeout=10).json()
    if isinstance(r,list):
        r=sorted(r)
        return r[-60:]
    return []

def ema(p,n):
    if len(p)<n:
        return []
    k=2/(n+1)
    m=sum(p[:n])/n
    o=[m]
    for x in p[n:]:
        o.append(x*k+o[-1]*(1-k))
    return o

def rsi(p):
    if len(p)<15:
        return 50
    g=0
    l=0
    for i in range(1,15):
        d=p[i]-p[i-1]
        if d>=0:
            g+=d
        else:
            l+=-d
    if l==0:
        return 88
    if g==0:
        return 12
    return 100-100/(1+g/l)

def send(c,t):
    u="https://api.telegram.org/bot"
    u=u+TOKEN+"/sendMessage"
    kb={"keyboard":[["BTC","ETH"],
    ["SOL","XRP"],
    ["COMPRAR","VENDER"],
    ["GRAF","PRO"]],
    "resize_keyboard":True}
    requests.post(u,json={"chat_id":c,
    "text":t,"reply_markup":kb},timeout=10)

@app.route("/")
def home():
    return "V210 LIVE",200

@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    d=request.get_json(force=True,silent=True)
    if not d:
        return "ok",200
    if "message" not in d:
        return "ok",200
    cid=d["message"]["chat"]["id"]
    txt=d["message"].get("text","")
    txt=txt.upper().strip()
    if "BTC" in txt:
        SEL="BTC"
    if "ETH" in txt:
        SEL="ETH"
    if "SOL" in txt:
        SEL="SOL"
    if "XRP" in txt:
        SEL="XRP"
    pn=price(SEL)
    if pn==0:
        if SEL in ENTS:
            pn=ENTS[SEL]["entry"]
    if "GRAF" in txt:
        from PIL import Image,ImageDraw
        cl=candles(SEL)
        if len(cl)==0:
            send(cid,"Sin datos")
            return "ok",200
        cs=[]
        for c in cl:
            cs.append(c[4])
        p=cs[-1]
        tp=price(SEL)
        if tp!=0:
            p=tp
        e9=ema(cs,9)
        e21=ema(cs,21)
        rr=rsi(cs)
        pr="N"
        se="E"
        sc=50
        if len(e9)>0:
            if len(e21)>0:
                a=e9[-1]
                b=e21[-1]
                if p>a:
                    if a>b:
                        pr="SUBE"
                        se="COMPRA"
                        sc=68
                if p<a:
                    if a<b:
                        pr="BAJA"
                        se="VENTA"
                        sc=66
                if rr<30:
                    pr="FUERTE"
                    se="COMPRA"
                    sc=92
                if rr>70:
                    pr="FUERTE
