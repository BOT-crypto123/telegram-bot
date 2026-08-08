import os, requests, threading, time, re, io, json
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app = Flask(__name__)
SEL = "XRP"
SL = 2.0
TP = 2.2
ENTS = {}
FILE = "/tmp/bot68.json"

def load():
    global ENTS
    try:
        if os.path.exists(FILE):
            with open(FILE,"r") as f:
                ENTS = json.load(f)
    except:
        ENTS = {}

def save():
    try:
        with open(FILE,"w") as f:
            json.dump(ENTS,f)
    except:
        pass

load()

def price(s):
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0

def get_candles(sym):
    try:
        url = f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=60"
        h = {"User-Agent":"Mozilla/5.0"}
        r = requests.get(url,headers=h,timeout=10).json()
        r = sorted(r)
        return r[-30:]
    except:
        return []

def send_text(cid,txt):
    try:
        u = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
        requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=15)
    except:
        pass

def send_graf(cid,sym,p):
    from PIL import Image, ImageDraw
    candles = get_candles(sym)
    W=900
    H=520
    img=Image.new("RGB",(W,H),"#0b0e14")
    dr=ImageDraw.Draw(img)
    for i in range(1,6):
        dr.line([0,i*H//6,W,i*H//6],fill="#1a1f2e",width=1)
    if candles:
        lows=[c[1] for c in candles]
        highs=[c[2] for c in candles]
        mn=min(min(lows),p*0.998)
        mx=max(max(highs),p*1.002)
    else:
        mn=p*0.985
        mx=p*1.015
    ent = ENTS[sym]["entry"] if sym in ENTS else p
    mn=min(mn,ent*0.98)
    mx=max(mx,ent*1.025)
    if mx==mn:
        mx=mn*1.01
    def yf(v):
        return H-70-(v-mn)/(mx-mn)*(H-110)
    def xf(i):
        return 60+i*(W-80)//30
    if candles:
        for i,c in enumerate(candles):
            low=c[1]
            high=c[2]
            op=c[3]
            cl=c[4]
            x=xf(i)
            col="#00ff88" if cl>=op else "#ff4444"
            dr.line([x+5,yf(low),x+5,yf(high)],fill=col,width=1)
            dr.rectangle([x,yf(max(op,cl)),x+10,yf(min(op,cl))],fill=col)
    ye=yf(ent)
    ytp=yf(ent*1.022)
    ysl=yf(ent*0.98)
    yp=yf(p)
    dr.line([0,ye,W,ye],fill="#ffcc00",width=2)
    dr.line([0,ytp,W,ytp],fill="#00ff88",width=2)
    dr.line([0,ysl,W,ysl],fill="#ff4444",width=2)
    dr.line([0,yp,W,yp],fill="#ffffff",width=1)
    dr.text((10,10),f"{sym} REAL 1m | ENT {round(ent,4)} | AHORA {round(p,4)}",fill="white")
    dr.text((10,30),f"TP +2.2% {round(ent*1.022,4)} NETO 2% | SL -2% {round(ent*0.98,4)}",fill="#ffcc00")
    bio=io.BytesIO()
    bio.name="graf.png"
    img.save(bio,"PNG")
    bio.seek(0)
    u=f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(u,data={"chat_id":cid},files={"photo":bio},timeout=20)

def checker():
    while True:
        time.sleep(90)
        if len(ENTS)==0:
            continue
        for sym in list(ENTS.keys()):
            p=price(sym)
            if p<1:
                continue
            ent=ENTS[sym]["entry"]
            usd=ENTS[sym]["usd"]
            cid=ENTS[sym]["chat"]
            pnl=(p/ent-1)*100
            if pnl<=-SL:
                send_text(cid,f"🔴 ROJA VENDER {sym} {round(p,4)} {round(pnl,2)}% Perdi ${round(usd*pnl/100,2)}")
                if sym in ENTS:
                    del ENTS[sym]
                    save()
            if pnl>=TP:
                if sym in ENTS:
                    neto=pnl-0.2
                    send_text(cid,f"🟢 VERDE VENDER {sym} {round(p,4)} {round(pnl,2)}% NETO {round(neto,2)}% Gane ${round(usd*neto/100,2)}")
                    del ENTS[sym]
                    save()

threading.Thread(target=checker,daemon=True).start()

@app.route("/")
def home():
    return "V68 TODO EN UNO OK",200

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
    for s in ["BTC","ETH","SOL","XRP"]:
        if s in t:
            SEL=s
    if t in ["BTC","ETH","SOL","XRP"]:
        SEL=t
    p=price(SEL)
    if p<1 and SEL in ENTS:
        p=ENTS[SEL]["entry"]
    if "GRAF" in t:
        send_graf(cid,SEL,p)
        return "ok",200
    if "COMPRAR" in t:
        nums=re.findall(r"[\d\.]+",t)
        monto=float(nums[0]) if nums else 100.0
        ENTS[SEL]={"entry":p,"chat":cid,"usd":monto}
        save()
        send_text(cid,f"ABIERTA {SEL} {round(p,4)} ${monto} TP 2.2% neto 2%")
        return "ok",200
    if "VENDER" in t:
        if SEL in ENTS:
            del ENTS[SEL]
            save()
        send_text(cid,f"CERRADA {SEL}")
        return "ok",200
    if "PRO" in t:
        if len(ENTS)==0:
            send_text(cid,"Sin partidas")
        else:
            out=""
            for k,v in ENTS.items():
                pp=price(k)
                if pp<1:
                    pp=v["entry"]
                pnl=(pp/v["entry"]-1)*100
                neto=pnl-0.2
                out+=f"{k} {round(neto,2)}% ${round(v['usd']*neto/100,2)} | "
            send_text(cid,out)
        return "ok",200
    send_text(cid,f"{SEL} {round(p,4)}")
    return "ok",200

if __name__=="__main__":
    port=int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0",port=port)
