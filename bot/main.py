import os, requests, threading, time, re
from flask import Flask, request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC"
SL=2.0
TP=2.2
ENTS={}
HIGHS={}
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
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["PRO"]],"resize_keyboard":True}
        requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
    except:
        pass
def checker():
    while True:
        time.sleep(180)
        try:
            for sym in ["BTC","ETH","SOL","XRP"]:
                p=price(sym)
                if p<1:
                    continue
                if sym not in HIGHS:
                    HIGHS[sym]=p
                if p>HIGHS[sym]:
                    HIGHS[sym]=p
                if sym in ENTS:
                    ent=ENTS[sym]["entry"]
                    usd=ENTS[sym]["usd"]
                    cid=ENTS[sym]["chat"]
                    pnl=(p/ent-1)*100
                    if pnl<=-SL:
                        send_text(cid,f"ROJA VENDER {sym} {round(p,4)} {round(pnl,2)}%")
                        del ENTS[sym]
                    if pnl>=TP and sym in ENTS:
                        neto=pnl-0.2
                        send_text(cid,f"VERDE VENDER {sym} {round(p,4)} Neto {round(neto,2)}% Gane ${round(usd*neto/100,2)}")
                        del ENTS[sym]
                LAST[sym]=p
        except:
            time.sleep(5)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
    return "V63 OK",200
@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    try:
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
        p=price(SEL)
        if p<1:
            p=LAST.get(SEL,0)
        if "COMPRAR" in t:
            nums=re.findall(r"[\d\.]+",t)
            monto=float(nums[0]) if nums else 100.0
            ENTS[SEL]={"entry":p,"chat":cid,"usd":monto}
            HIGHS[SEL]=p
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
                    out+=f"{k} {round(neto,2)}% | "
                send_text(cid,out)
            return "ok",200
        send_text(cid,f"{SEL} {round(p,4)}")
        return "ok",200
    except:
        return "ok",200
if __name__=="__main__":
    port=int(os.getenv("PORT","10000"))
    app.run(host="0.0.0.0",port=port)
