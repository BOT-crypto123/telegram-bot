import os,requests,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or ""
print("V211 TOKEN",len(TOKEN),flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b211.json"

def load():
    if os.path.exists(FILE):
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))

load()
print("V211 LOADED",flush=True)

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
    return "V211 LIVE",200

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
            send(cid,"X")
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
                        pr="S"
                        se="C"
                        sc=68
                if p<a:
                    if a<b:
                        pr="B"
                        se="V"
                        sc=66
                if rr<30:
                    pr="F"
                    se="C"
                    sc=92
                if rr>70:
                    pr="F"
                    se="V"
                    sc=91
        mn=min(cs)
        mx=max(cs)
        if mn==mx:
            mn=mn*0.998
            mx=mx*1.002
        W=1000
        H=560
        im=Image.new("RGB",(W,H),(10,14,21))
        dr=ImageDraw.Draw(im)
        i=0
        for c in cl:
            x=20+i*13
            lo=c[1]
            hi=c[2]
            o=c[3]
            cc=c[4]
            y1=H-70-(lo-mn)/(mx-mn)*(H-100)
            y2=H-70-(hi-mn)/(mx-mn)*(H-100)
            yo=H-70-(o-mn)/(mx-mn)*(H-100)
            yc=H-70-(cc-mn)/(mx-mn)*(H-100)
            yt=min(yo,yc)
            yb=max(yo,yc)
            if yt==yb:
                yb=yt+2
            col=(0,230,118)
            if cc<o:
                col=(255,61,87)
            dr.line([x+3,y1,x+3,y2],fill=col)
            dr.rectangle([x,yt,x+6,yb],fill=col)
            i+=1
        if SEL in ENTS:
            en=ENTS[SEL]["entry"]
            ye=H-70-(en-mn)/(mx-mn)*(H-100)
            dr.line([0,ye,W,ye],fill=(255,234,0),width=2)
        hr=datetime.utcnow()-timedelta(hours=6)
        hr=hr.strftime("%H:%M")
        e9s="--"
        e21s="--"
        if len(e9)>0:
            e9s=str(round(e9[-1],1))
        if len(e21)>0:
            e21s=str(round(e21[-1],1))
        dr.text((10,10),SEL,fill=(255,255,255))
        cap=SEL+" "
        cap+=str(round(p,2))
        cap+=" "
        cap+=hr
        cap+="\n"
        cap+="E9:"
        cap+=e
