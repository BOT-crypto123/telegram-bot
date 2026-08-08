import os, requests, threading, time, re, io
from flask import Flask, request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"
SL=2.0
TP=2.2
ENTS={}
def price(s):
    try:
        r=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0
def get_candles(sym):
    try:
        # velas reales 1 min ultimos 30 de Coinbase Exchange
        url=f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=60"
        h={"User-Agent":"Mozilla/5.0"}
        r=requests.get(url,headers=h,timeout=10).json()
        # r = [[time,low,high,open,close,vol],...]
        r=sorted(r) # mas viejo primero
        return r[-30:] # ultimas 30
    except Exception as e:
        print("candle err",e)
        return []
def send_text(cid,txt):
    try:
        u=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
        requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
    except:
        pass
def send_graf(cid,sym,p):
    try:
        from PIL import Image, ImageDraw, ImageFont
        candles=get_candles(sym)
        W=900
        H=500
        img=Image.new("RGB",(W,H),"#0b0e14")
        dr=ImageDraw.Draw(img)
        # fondo grid
        for i in range(1,5):
            y=i*H//5
            dr.line([0,y,W,y],fill="#1a1f2e",width=1)
        if not candles:
            # fallback si no hay velas
            mn=p*0.985
            mx=p*1.015
        else:
            lows=[c[1] for c in candles]
            highs=[c[2] for c in candles]
            mn=min(min(lows),p*0.998)
            mx=max(max(highs),p*1.002)
            # expande si hay entrada
            if sym in ENTS:
                ent=ENTS[sym]["entry"]
                mn=min(mn,ent*0.98)
                mx=max(mx,ent*1.022)
        # evita division cero
        if mx==mn:
            mx=mn*1.01
        def yf(v):
            return H-60-(v-mn)/(mx-mn)*(H-100)
        def xf(i):
            return 60 + i*(W-80)//30
        # dibuja velas reales
        if candles:
            for i,c in enumerate(candles):
                t,low,high,op,cl,vol=c
                x=xf(i)
                col="#00ff88" if cl>=op else "#ff4444"
                # mecha
                dr.line([x+5,yf(low),x+5,yf(high)],fill=col,width=1)
                # cuerpo
                dr.rectangle([x,yf(max(op,cl)),x+10,yf(min(op,cl))],fill=col)
        # lineas estrategia
        entry=ENTS[sym]["entry"] if sym in ENTS else p
        ye=yf(entry)
        ytp=yf(entry*1.022)
        ysl=yf(entry*0.98)
        dr.line([0,ye,W,ye],fill="#ffcc00",width=2)
        dr.text((10,ye-16),f"ENT {round(entry,4)}",fill="#ffcc00")
        dr.line([0,ytp,W,ytp],fill="#00ff88",width=2)
        dr.text((10,ytp-16),f"TP +2.2% {round(entry*1.022,4)} NETO 2%",fill="#00ff88")
        dr.line([0,ysl,W,ysl],fill="#ff4444",width=2)
        dr.text((10,ysl-16),f"SL -2% {round(entry*0.98,4)}",fill="#ff4444")
        # precio actual
        yp=yf(p)
        dr.line([0,yp,W,yp],fill="white",width=1)
        dr.text((W-180,yp-16),f"AHORA {round(p,4)}",fill="white")
        # titulo
        dr.text((10,10),f"{sym} REAL 1m Coinbase - Estrategia 2% Limpio",fill="white")
        dr.text((10,28),f"Rango {round(mn,4)} - {round(mx,4)}",fill="#8899aa")
        bio=io.BytesIO()
        bio.name="graf.png"
        img.save(bio,"PNG")
        bio.seek(0)
        u=f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        requests.post(u,data={"chat_id":cid},files={"photo":bio},timeout=20)
    except Exception as e:
        print("graf err",e)
        send_text(cid,f"{sym} {round(p,4)} (graf error, intenta de nuevo)")
def checker():
    while True:
        time.sleep(120)
        try:
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
                    del ENTS[sym]
                elif pnl>=TP:
                    neto=pnl-0.2
                    send_text(cid,f"🟢 VERDE VENDER {sym} {round(p,4)} {round(pnl,2)}% NETO {round(neto,2)}% Gane ${round(usd*neto/100,2)}")
                    del ENTS[sym]
        except:
            time.sleep(2)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
    return "V67 REAL CANDLES 2% OK",200
@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    try:
        d=request.get_json(force=True,silent=True)
        if not d or "message" not in d:
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
