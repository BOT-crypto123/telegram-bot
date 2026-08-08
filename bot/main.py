import os, requests, threading, time, re, io, random
from flask import Flask, request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"
SL=2.0
TP=2.2
ENTS={}
LAST={}
def price(s):
    try:
        r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0
def send_text(cid,txt):
    try:
        u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
        requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
    except:
        pass
def send_graf(cid,sym,p):
    try:
        from PIL import Image, ImageDraw
        W=800
        H=400
        img=Image.new("RGB",(W,H),"#0f0f0f")
        dr=ImageDraw.Draw(img)
        entry=ENTS[sym]["entry"] if sym in ENTS else p
        mn=min(p,entry)*0.985
        mx=max(p,entry)*1.015
        def yf(v):
            return H-50-(v-mn)/(mx-mn)*(H-80)
        base=p*0.995
        for i in range(25):
            x=i*32+10
            o=base*(1+random.uniform(-0.002,0.002))
            c=o*(1+random.uniform(-0.004,0.004))
            col="#00ff88" if c>=o else "#ff5555"
            dr.rectangle([x,yf(max(o,c)),x+18,yf(min(o,c))],fill=col)
            base=c
        ye=yf(entry)
        dr.line([0,ye,W,ye],fill="#ffcc00",width=2)
        dr.text((10,ye-14),f"ENT {round(entry,4)}",fill="#ffcc00")
        dr.line([0,yf(entry*1.022),W,yf(entry*1.022)],fill="#00ff88",width=2)
        dr.text((10,yf(entry*1.022)-14),f"TP +2.2% NETO 2%",fill="#00ff88")
        dr.line([0,yf(entry*0.98),W,yf(entry*0.98)],fill="#ff4444",width=2)
        dr.text((10,yf(entry*0.98)-14),f"SL -2%",fill="#ff4444")
        dr.text((10,10),f"{sym} {round(p,4)}",fill="white")
        bio=io.BytesIO()
        bio.name="graf.png"
        img.save(bio,"PNG")
        bio.seek(0)
        u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
        requests.post(u,data={"chat_id":cid},files={"photo":bio},timeout=20)
    except Exception as e:
        print("graf err",e)
        send_text(cid,f"{sym} {round(p,4)} graf no disponible")
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
                    send_text(cid,f"ROJA VENDER {sym} {round(p,4)} {round(pnl,2)}% Perdi ${round(usd*pnl/100,2)}")
                    del ENTS[sym]
                elif pnl>=TP:
                    neto=pnl-0.2
                    send_text(cid,f"VERDE VENDER {sym} {round(p,4)} {round(pnl,2)}% NETO {round(neto,2)}% Gane ${round(usd*neto/100,2)}")
                    del ENTS[sym]
        except:
            time.sleep(2)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
    return "V66 GRAF 2pct OK",200
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
        if p<1:
            p=ENTS[SEL]["entry"] if SEL in ENTS else 0
        if "GRAF" in t:
            if p==0:
                p=price(SEL)
            send_graf(cid,SEL,p)
            return "ok",200
        if "COMPRAR" in t:
            nums=re.findall(r"[\d\.]+",t)
            monto=float(nums[0]) if nums else 100.0
            ENTS[SEL]={"entry":p,"chat":cid,"usd":monto}
            send_text(cid,f"ABIERTA {SEL} {round(p,4)} ${monto} TP 2.2% neto 2%")
            return "ok",200
        if "VENDER" in t:
            if SEL in ENTS:
                del ENTS[SEL]
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
    except Exception as e:
        print(e)
        return "ok",200
if __name__=="__main__":
    port=int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0",port=port)
