import os,requests,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or ""
print("V117 TOKEN",len(TOKEN),flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b117.json"

def load():
    if os.path.exists(FILE):
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))

load()
print("V117 LOADED",flush=True)

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
    h={"User-Agent":"Mozilla/5.0"}
    r=requests.get(u,headers=h,timeout=10).json()
    if isinstance(r,list):
        r=sorted(r)
        return r[-60:]
    return []

def ema(prices,n):
    if len(prices)<n:
        return []
    k=2/(n+1)
    m=sum(prices[:n])/n
    out=[m]
    for p in prices[n:]:
        out.append(p*k+out[-1]*(1-k))
    return out

def rsi(prices):
    if len(prices)<15:
        return 50
    g=0
    l=0
    for i in range(1,15):
        d=prices[i]-prices[i-1]
        if d>=0:
            g=g+d
        else:
            l=l-d
    if l==0:
        return 88
    if g==0:
        return 12
    rs=g/l
    return 100-100/(1+rs)

def send(cid,txt):
    url="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
    kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
    requests.post(url,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=12)

@app.get("/")
def home():
    return "V117 LIVE",200

@app.post("/webhook")
def wh():
    global SEL
    d=request.get_json(force=True,silent=True)
    if not d:
        return "ok",200
    if "message" not in d:
        return "ok",200
    cid=d["message"]["chat"]["id"]
    t=d["message"].get("text","").upper().strip()
    if "BTC" in t:
        SEL="BTC"
    if "ETH" in t:
        SEL="ETH"
    if "SOL" in t:
        SEL="SOL"
    if "XRP" in t:
        SEL="XRP"
    p_now=price(SEL)
    if p_now==0:
        if SEL in ENTS:
            p_now=ENTS[SEL]["entry"]
    if "GRAF" in t:
        from PIL import Image,ImageDraw
        cl=candles(SEL)
        if len(cl)==0:
            send(cid,"Sin datos "+SEL)
            return "ok",200
        closes=[]
        for c in cl:
            closes.append(c[4])
        p=closes[-1]
        tmp=price(SEL)
        if tmp!=0:
            p=tmp
        e9=ema(closes,9)
        e21=ema(closes,21)
        r=rsi(closes)
        pred="NEUTRAL"
        sen="ESPERAR"
        score=50
        if len(e9)>0 and len(e21)>0:
            a=e9[-1]
            b=e21[-1]
            if p>a and a>b:
                pred="SUBIDA"
                sen="COMPRA"
                score=68
            if p<a and a<b:
                pred="
