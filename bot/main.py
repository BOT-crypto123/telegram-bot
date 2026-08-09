import os,requests,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or ""
print("V201 TOKEN",len(TOKEN),flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b201.json"

def load():
    if os.path.exists(FILE):
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))

load()
print("V201 LOADED",flush=True)

def price(s):
    u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
    r=requests.get(u,timeout=8).json()
    return float(r.get("data",{}).get("amount","0") or 0)

def candles(sym):
    u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
    h={"User-Agent":"Mozilla/5.0"}
    r=requests.get(u,headers=h,timeout=10).json()
    if isinstance(r,list):
        return sorted(r)[-60:]
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
            g+=d
        else:
            l+=-d
    if l==0:
        return 88
    if g==0:
        return 12
    return 100-100/(1+g/l)

def send(cid,txt):
    url="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
    kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
    requests.post(url,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=12)

@app.route("/")
def home():
    return "V201 LIVE",200

@app.route("/webhook",methods=["POST"])
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
    if p_now==0 and SEL in ENTS:
        p_now=ENTS[SEL]["entry"]
    if "GRAF" in t:
        from PIL import Image,ImageDraw
        cl=candles(SEL)
        if len(cl)==0:
            send(cid,"Sin datos "+SEL)
            return "ok",200
        closes=[c[4] for c in cl]
        p=closes[-1]
        tmp=price(SEL)
        if tmp!=0:
            p=tmp
        e9=ema(closes,9)
        e21=ema(closes,21)
        rr=rsi(closes)
        pred="NEUTRAL"
        sen="ESPERAR"
        sc=50
        if len(e9)>0 and len(e21)>0:
            a=e9[-1]
            b=e21[-1]
            if p>a and a>b:
                pred="SUBIDA"
                sen="COMPRA"
                sc=68
            if p<a and a<b:
                pred="BAJADA"
                sen="VENTA"
                sc=66
            if rr<30:
                pred="SUBIDA FUERTE"
                sen="COMPRA"
                sc=92
            if rr>70:
                pred="BAJADA FUERTE"
                sen="VENTA"
                sc=91
        mn=min(closes)
        mx=max(closes)
        if mn==mx:
            mn=mn*0.998
            mx=mx*1.002
        W=1000
        H=560
        img=Image.new("RGB",(W,H),(10,14,21))
        dr=ImageDraw.Draw(img)
        idx=0
        for c in cl:
            x=20+idx*13
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
            dr.line([x+3,y1,x+3,y2],fill=col,width=1)
            dr.rectangle([x,yt,x+6,yb],fill=col)
            idx+=1
        if SEL in ENTS:
            en=ENTS[SEL]["entry"]
            ye=H-70-(en-mn)/(mx-mn)*(H-100)
            dr.line([0,ye,W,ye],fill=(255,234,0),width=2)
        hora=(datetime.utcnow()-timedelta(hours=6)).strftime("%I:%M %p")
        e9s="--"
        e21s="--"
        if len(e9)>0:
            e9s=str(round(e9[-1],2))
        if len(e21)>0:
            e21s=str(round(e21[-1],2))
        dr.text((10,10),SEL+" V201 GOD",fill=(255,255,255))
        cap=SEL+" "+str(round(p,4))+" | "+hora+"\n"
        if SEL in ENTS:
            en=ENTS[SEL]["entry"]
            pnl=(p/en-1)*100
            cap+=str(round(pnl,2))+"% "
        cap+="EMA9:"+e9s+" EMA21:"+e21s+"\n"
        cap+="RS
