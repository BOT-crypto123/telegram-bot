import os, requests, threading, time, re, io, json
from flask import Flask, request
from datetime import datetime

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"
SL=2.0
TP2=2.2
ENTS={}
FILE="/tmp/bot79.json"
CONFIG={"AUTO":False,"LAST_CID":0}

def load():
    global ENTS, CONFIG
    try:
        if os.path.exists(FILE):
            with open(FILE,"r") as f:
                d=json.load(f)
                ENTS=d.get("ENTS",{})
                CONFIG=d.get("CONFIG",CONFIG)
    except:
        ENTS={}

def save():
    try:
        with open(FILE,"w") as f:
            json.dump({"ENTS":ENTS,"CONFIG":CONFIG},f)
    except:
        pass

load()

def price(s):
    try:
        r=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0

def get_candles(sym):
    try:
        url=f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=60"
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
        return sorted(r)[-50:]
    except:
        return []

def send_text(cid,txt):
    try:
        u=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"],["AUTO ON","AUTO OFF"]],"resize_keyboard":True}
        requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=15)
    except:
        pass

def send_graf(cid,sym,p):
    try:
        from PIL import Image, ImageDraw
        candles=get_candles(sym)
        W=900;H=520
        img=Image.new("RGB",(W,H),"#0b0e14")
        dr=ImageDraw.Draw(img)
        for i in range(1,6):
            dr.line([0,i*H//6,W,i*H//6],fill="#1a1f2e",width=1)
        if candles:
            lows=[c[1] for c in candles];highs=[c[2] for c in candles]
            mn=min(min(lows),p)*0.9995;mx=max(max(highs),p)*1.0005
        else:
            mn=p*0.995;mx=p*1.005
        if mx==mn:
            mx=mn*1.01
        def yf(v):
            return H-70-(v-mn)/(mx-mn)*(H-110)
        def xf(i):
            return 20+i*(W-40)//50
        closes=[c[4] for c in candles] if candles else []
        if closes:
            ema=[];k=2/(9+1);e=closes[0]
            for cl in closes:
                e=cl*k+e*(1-k);ema.append(e)
            for i in range(1,len(ema)):
                dr.line([xf(i-1),yf(ema[i-1]),xf(i),yf(ema[i])],fill="#00bfff",width=1)
        if candles:
            for i,c in enumerate(candles):
                x=xf(i);col="#00ff88" if c[4]>=c[3] else "#ff4444"
                dr.line([x+3,yf(c[1]),x+3,yf(c[2])],fill=col,width=1)
                dr.rectangle([x,yf(max(c[3],c[4])),x+6,yf(min(c[3],c[4]))],fill=col)
        ent=ENTS[sym]["entry"] if sym in ENTS else p
        ye=yf(ent)
        if 20<ye<H-20:
            dr.line([0,ye,W,ye],fill="#ffcc00",width=2)
        dr.text((10,10),f"V79 {sym} REAL 1m | AHORA {round(p,4)} ENT {round(ent,4)}",fill="white")
        pnl=(p/ent-1)*100 if ent else 0
        dr.text((10,30),f"PNL {round(pnl-0.2,2)}% | TP {round(ent*1.022,4)} NETO 2% SL {round(ent*0.98,4)}",fill="#ffcc00")
        bio=io.BytesIO();bio.name="graf.png";img.save(bio,"PNG");bio.seek(0)
        u=f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        requests.post(u,data={"chat_id":cid},files={"photo":bio},timeout=20)
    except:
        send_text(cid,f"{sym} {round(p,4)}")

def checker():
    while True:
        try:
            time.sleep(60)
            for sym in list(ENTS.keys()):
                p=price(sym)
                if p<1:
                    continue
                v=ENTS[sym]
                pnl=(p/v["entry"]-1)*100
                if pnl<=-SL:
                    send_text(v["chat"],f"🔴 ROJA VENDER {sym} {round(p,4)} {round(pnl,2)}% Perdi ${round(v['usd']*pnl/100,2)}")
                    del ENTS[sym];save()
                elif pnl>=TP2:
                    neto=pnl-0.2
                    send_text(v["chat"],f"🟢 VERDE VENDER {sym} {round(p,4)} {round(pnl,2)}% NETO {round(neto,2)}% Gane ${round(v['usd']*neto/100,2)}")
                    del ENTS[sym];save()
        except:
            time.sleep(10)

def keep_alive():
    while True:
        try:
            time.sleep(240)
            requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=5)
        except:
            pass

threading.Thread(target=checker,daemon=True).start()
threading.Thread(target=keep_alive,daemon=True).start()

@app.route("/")
def home():
    return "V79 FINAL ANTI-CAIDA OK",200

@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    d=request.get_json(force=True,silent=True)
    if not d or "message" not in d:
        return "ok",200
    cid=d["message"]["chat"]["id"]
    t=d["message"].get("text","").upper().strip()
    CONFIG["LAST_CID"]=cid;save()
    if "AUTO ON" in t:
        CONFIG["AUTO"]=True;save();send_text(cid,"🤖 V79 AUTO ON - Blindado no se cae");return "ok",200
    if "AUTO OFF" in t:
        CONFIG["AUTO"]=False;save();send_text(cid,"🤖 AUTO OFF");return "ok",200
    for s in ["BTC","ETH","SOL","XRP"]:
        if s in t:
            SEL=s
    if t in ["BTC","ETH","SOL","XRP"]:
        SEL=t
    p=price(SEL)
    if p<1 and SEL in ENTS:
        p=ENTS[SEL]["entry"]
    if "GRAF" in t:
        send_graf(cid,SEL,p);return "ok",200
    if "COMPRAR" in t:
        nums=re.findall(r"[\d\.]+",t);monto=float(nums[0]) if nums else 100.0
        ENTS[SEL]={"entry":p,"chat":cid,"usd":monto};save()
        send_text(cid,f"✅ V79 ABIERTA {SEL} {round(p,4)} ${monto}\nTP {round(p*1.022,4)} NETO 2% = ${round(monto*0.02,2)}\nSL {round(p*0.98,4)}");return "ok",200
    if "VENDER" in t:
        if SEL in ENTS:
            del ENTS[SEL];save()
        send_text(cid,f"CERRADA {SEL}");return "ok",200
    if "PRO" in t:
        if len(ENTS)==0:
            send_text(cid,"V79 Sin partidas - AUTO ON para cazar")
        else:
            out=""
            for k,v in ENTS.items():
                pp=price(k) or v["entry"];pnl=(pp/v["entry"]-1)*100;out+=f"{k} {round(pnl-0.2,2)}% ${round(v['usd']*(pnl-0.2)/100,2)} | "
            send_text(cid,out)
        return "ok",200
    send_text(cid,f"{SEL} {round(p,4)}")
    return "ok",200

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
