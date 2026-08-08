import os, requests, threading, time, re, io, json
from flask import Flask, request
from datetime import datetime

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"
SL=2.0
TP2=2.2
DROP_AUTO=1.0
ENTS={}
FILE="/tmp/bot80.json"
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

def get_candles(sym,gran=60,n=20):
    try:
        url=f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity={gran}"
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
        return sorted(r)[-n:]
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
        candles=get_candles(sym,60,50)
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
        if sym in ENTS and 10<ye<H-10:
            dr.line([0,ye,W,ye],fill="#ffcc00",width=2)
            dr.text((10,ye-15),f"ENT {round(ent,4)}",fill="#ffcc00")
        dr.text((10,10),f"V80 AUTO {sym} {round(p,4)}",fill="white")
        if sym in ENTS:
            pnl=(p/ENTS[sym]["entry"]-1)*100
            dr.text((10,28),f"PNL {round(pnl,2)}% NETO {round(pnl-0.2,2)}% TP {round(ent*1.022,4)} SL {round(ent*0.98,4)}",fill="#00ff88" if pnl>=0 else "#ff4444")
        bio=io.BytesIO();bio.name="graf.png";img.save(bio,"PNG");bio.seek(0)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",data={"chat_id":cid},files={"photo":bio},timeout=20)
    except:
        send_text(cid,f"{sym} {round(p,4)}")

def checker():
    while True:
        try:
            time.sleep(60)
            # 1. Revisar ventas de partidas abiertas
            for sym in list(ENTS.keys()):
                p=price(sym)
                if p<1:
                    continue
                v=ENTS[sym]
                pnl=(p/v["entry"]-1)*100
                if pnl<=-SL:
                    send_text(v["chat"],f"🔴 AUTO VENDER {sym} {round(p,4)} {round(pnl,2)}% Perdi ${round(v['usd']*pnl/100,2)}")
                    del ENTS[sym];save()
                elif pnl>=TP2:
                    neto=pnl-0.2
                    send_text(v["chat"],f"🟢 AUTO VENDER {sym} {round(p,4)} +{round(pnl,2)}% NETO {round(neto,2)}% Gane ${round(v['usd']*neto/100,2)}")
                    del ENTS[sym];save()
            # 2. Modo AUTO compra cuando baja
            if CONFIG.get("AUTO") and CONFIG.get("LAST_CID"):
                cid=CONFIG["LAST_CID"]
                for sym in ["BTC","ETH","SOL","XRP"]:
                    if sym in ENTS:
                        continue
                    candles=get_candles(sym,60,20)
                    if len(candles)<15:
                        continue
                    p_now=candles[-1][4]
                    p_old=candles[-10][4]
                    drop=(p_now/p_old-1)*100
                    if drop<=-DROP_AUTO:
                        ENTS[sym]={"entry":p_now,"chat":cid,"usd":100}
                        save()
                        send_text(cid,f"🤖 AUTO COMPRAR {sym} {round(p_now,4)} por caida {round(drop,2)}% en 10min\nTP {round(p_now*1.022,4)} = +$2\nSL {round(p_now*0.98,4)}")
        except:
            time.sleep(10)

threading.Thread(target=checker,daemon=True).start()

@app.route("/")
def home():
    return "V80 AUTO TRADER OK",200

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
        CONFIG["AUTO"]=True;save();send_text(cid,"🤖 V80 AUTO ON\nAhora te compro solo cuando baje -1% y te vendo solo cuando suba +2.2% neto 2%");return "ok",200
    if "AUTO OFF" in t:
        CONFIG["AUTO"]=False;save();send_text(cid,"🤖 AUTO OFF - Manual");return "ok",200
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
        send_text(cid,f"✅ COMPRADA {SEL} {round(p,4)} ${monto}");return "ok",200
    if "VENDER" in t:
        if SEL in ENTS:
            del ENTS[SEL];save()
        send_text(cid,f"CERRADA {SEL}");return "ok",200
    if "PRO" in t:
        if len(ENTS)==0:
            send_text(cid,"V80 Sin partidas - Pon AUTO ON y te compro cuando baje")
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
