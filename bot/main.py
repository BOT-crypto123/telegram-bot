import os, requests, threading, time, re, io, json
from flask import Flask, request
from datetime import datetime
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"
SL=2.0
TP1=1.0
TP2=2.2
ENTS={}
FILE="/tmp/bot70.json"
CONFIG={"AUTO":False}
def load():
    global ENTS, CONFIG
    try:
        if os.path.exists(FILE):
            with open(FILE,"r") as f:
                d=json.load(f)
                ENTS=d.get("ENTS",{})
                CONFIG=d.get("CONFIG",{"AUTO":False})
    except:
        pass
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
def get_candles(sym,gran=60,lim=50):
    try:
        url=f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity={gran}"
        h={"User-Agent":"Mozilla/5.0"}
        r=requests.get(url,headers=h,timeout=10).json()
        r=sorted(r)
        return r[-lim:]
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
    from PIL import Image, ImageDraw
    candles=get_candles(sym,60,50)
    W=900
    H=520
    img=Image.new("RGB",(W,H),"#0b0e14")
    dr=ImageDraw.Draw(img)
    for i in range(1,6):
        dr.line([0,i*H//6,W,i*H//6],fill="#1a1f2e",width=1)
    if candles:
        lows=[c[1] for c in candles]
        highs=[c[2] for c in candles]
        mn=min(min(lows),p)*0.9995
        mx=max(max(highs),p)*1.0005
    else:
        mn=p*0.995
        mx=p*1.005
    if mx==mn:
        mx=mn*1.01
    def yf(v):
        return H-70-(v-mn)/(mx-mn)*(H-110)
    def xf(i):
        return 20+i*(W-40)//50
    # EMA 9
    closes=[c[4] for c in candles] if candles else []
    if closes:
        ema=[]
        k=2/(9+1)
        e=closes[0]
        for cl in closes:
            e=cl*k+e*(1-k)
            ema.append(e)
        for i in range(1,len(ema)):
            dr.line([xf(i-1),yf(ema[i-1]),xf(i),yf(ema[i])],fill="#00bfff",width=1)
    if candles:
        for i,c in enumerate(candles):
            low=c[1];high=c[2];op=c[3];cl=c[4]
            x=xf(i)
            col="#00ff88" if cl>=op else "#ff4444"
            dr.line([x+3,yf(low),x+3,yf(high)],fill=col,width=1)
            dr.rectangle([x,yf(max(op,cl)),x+6,yf(min(op,cl))],fill=col)
    ent=ENTS[sym]["entry"] if sym in ENTS else p
    ye=yf(ent)
    if 20<ye<H-20:
        dr.line([0,ye,W,ye],fill="#ffcc00",width=2)
    dr.text((10,10),f"{sym} 1m REAL | AHORA {round(p,4)} | ENT {round(ent,4)}",fill="white")
    pnl=(p/ent-1)*100 if ent else 0
    col="#00ff88" if pnl>=0 else "#ff4444"
    dr.text((10,32),f"PNL {round(pnl,2)}% NETO {round(pnl-0.2,2)}% | TP +2.2% {round(ent*1.022,4)} SL -2% {round(ent*0.98,4)}",fill=col)
    dr.text((10,H-20),f"EMA Azul 9 | {datetime.now().strftime('%H:%M')}",fill="#8899aa")
    bio=io.BytesIO();bio.name="graf.png";img.save(bio,"PNG");bio.seek(0)
    u=f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(u,data={"chat_id":cid},files={"photo":bio},timeout=20)

def checker():
    while True:
        time.sleep(60)
        for sym in list(ENTS.keys()):
            p=price(sym)
            if p<1:
                continue
            v=ENTS[sym]
            ent=v["entry"];usd=v["usd"];cid=v["chat"]
            pnl=(p/ent-1)*100
            # aviso -1%
            if -1.2<pnl<-0.8 and not v.get("av1"):
                send_text(cid,f"⚠️ {sym} -1% {round(p,4)} cuidado")
                v["av1"]=True;save()
            if pnl>=TP1 and not v.get("tp1"):
                send_text(cid,f"💰 {sym} +1% {round(p,4)} TP1 parcial Gane ${round(usd*0.8/100,2)}")
                v["tp1"]=True;save()
            if pnl<=-SL:
                send_text(cid,f"🔴 ROJA VENDER {sym} {round(p,4)} {round(pnl,2)}% Perdi ${round(usd*pnl/100,2)}")
                del ENTS[sym];save()
            elif pnl>=TP2:
                neto=pnl-0.2
                send_text(cid,f"🟢 VERDE VENDER {sym} {round(p,4)} {round(pnl,2)}% NETO {round(neto,2)}% Gane ${round(usd*neto/100,2)}")
                del ENTS[sym];save()
        # modo auto cazador
        if CONFIG.get("AUTO"):
            for sym in ["BTC","ETH","SOL","XRP"]:
                if sym in ENTS:
                    continue
                candles=get_candles(sym,60,20)
                if len(candles)<10:
                    continue
                # caida 1% en 15 min
                p_now=candles[-1][4]
                p_old=candles[-15][4] if len(candles)>=15 else candles[0][4]
                drop=(p_now/p_old-1)*100
                if drop<=-1.0:
                    # avisa a todos los que tienen auto
                    for k,v in ENTS.items():
                        pass
                    # busca el ultimo cid que uso auto
                    # guardamos ultimo cid
                    cid_auto=CONFIG.get("LAST_CID")
                    if cid_auto:
                        send_text(cid_auto,f"🤖 AUTO {sym} cayo {round(drop,2)}% en 15m {round(p_now,4)} -> Posible COMPRA")

threading.Thread(target=checker,daemon=True).start()

@app.route("/")
def home():
    return "V70 TITAN OK",200

@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    d=request.get_json(force=True,silent=True)
    if not d or "message" not in d:
        return "ok",200
    cid=d["message"]["chat"]["id"]
    t=d["message"].get("text","").upper().strip()
    CONFIG["LAST_CID"]=cid
    save()
    if "AUTO ON" in t:
        CONFIG["AUTO"]=True;save()
        send_text(cid,"🤖 AUTO ON Activo - Te aviso caidas -1%")
        return "ok",200
    if "AUTO OFF" in t:
        CONFIG["AUTO"]=False;save()
        send_text(cid,"🤖 AUTO OFF")
        return "ok",200
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
        ENTS[SEL]={"entry":p,"chat":cid,"usd":monto,"time":str(datetime.now()),"av1":False,"tp1":False}
        save()
        send_text(cid,f"✅ ABIERTA {SEL} {round(p,4)} ${monto}\nTP1 +1% = {round(p*1.01,4)}\nTP2 +2.2% = {round(p*1.022,4)} NETO 2% = ${round(monto*0.02,2)}\nSL -2% = {round(p*0.98,4)}")
        return "ok",200
    if "VENDER" in t:
        if SEL in ENTS:
            pp=price(SEL)
            ent=ENTS[SEL]["entry"]
            usd=ENTS[SEL]["usd"]
            pnl=(pp/ent-1)*100
            neto=pnl-0.2
            send_text(cid,f"CERRADA {SEL} {round(pp,4)} PNL {round(neto,2)}% ${round(usd*neto/100,2)}")
            del ENTS[SEL];save()
        else:
            send_text(cid,f"CERRADA {SEL}")
        return "ok",200
    if "PRO" in t:
        if len(ENTS)==0:
            send_text(cid,"Sin partidas - AUTO ON para cazar")
        else:
            out=""
            for k,v in ENTS.items():
                pp=price(k)
                if pp<1:
                    pp=v["entry"]
                pnl=(pp/v["entry"]-1)*100
                neto=pnl-0.2
                mins="?"
                try:
                    t0=datetime.fromisoformat(v["time"])
                    mins=int((datetime.now()-t0).total_seconds()//60)
                except:
                    pass
                out+=f"{k} {round(pp,4)} PNL {round(neto,2)}% ${round(v['usd']*neto/100,2)} {mins}m\n"
            send_text(cid,out)
        return "ok",200
    send_text(cid,f"{SEL} {round(p,4)}")
    return "ok",200

if __name__=="__main__":
    port=int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0",port=port)
