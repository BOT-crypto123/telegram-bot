import os,requests,re,io,json,sys
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
print("V112 TOKEN", len(TOKEN), flush=True)
sys.stdout.flush()

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b112.json"

def load():
    try:
        if os.path.exists(FILE):
            d=json.load(open(FILE))
            ENTS.update(d.get("ENTS",{}))
    except Exception as e:
        print("LOAD ERR",e,flush=True)

load()
print("V112 LOADED", flush=True)

def price(s):
    try:
        u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
        return float(requests.get(u,timeout=8).json()["data"]["amount"])
    except:
        return 0.0

def candles(sym):
    try:
        u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
        return sorted(requests.get(u,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json())[-60:]
    except Exception as e:
        print("CANDLE ERR",e,flush=True)
        return []

def send(cid,txt):
    try:
        url="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
        requests.post(url,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
    except Exception as e:
        print("SEND ERR",e,flush=True)

@app.route("/")
def home():
    return "V112 LIVE",200

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
        p=price(SEL)
        if p.__eq__(0) and SEL in ENTS:
            p=ENTS[SEL]
        if "GRAF" in t:
            from PIL import Image,ImageDraw
            cl=candles(SEL)
            if len(cl).__eq__(0):
                send(cid,"Sin datos "+SEL)
                return "ok",200
            closes=[c[4] for c in cl]
            mn=min(closes)
            mx=max(closes)
            if mn.__eq__(mx):
                mn=mn*0.998
                mx=mx*1.002
            W=900
            H=500
            img=Image.new("RGB",(W,H),(10,14,21))
            dr=ImageDraw.Draw(img)
            idx=0
            for c in cl:
                x=20+idx*14
                lo=c[1]
                hi=c[2]
                o=c[3]
                cc=c[4]
                y1=H-60-(lo-mn)/(mx-mn)*(H-100)
                y2=H-60-(hi-mn)/(mx-mn)*(H-100)
                yo=H-60-(o-mn)/(mx-mn)*(H-100)
                yc=H-60-(cc-mn)/(mx-mn)*(H-100)
                yt=min(yo,yc)
                yb=max(yo,yc)
                col=(0,230,118)
                if cc.__lt__(o):
                    col=(255,61,87)
                dr.line([x+3,y1,x+3,y2],fill=col,width=1)
                dr.rectangle([x,yt,x+6,yb+2],fill=col)
                idx+=1
            hora=(datetime.utcnow()-timedelta(hours=6)).strftime("%I:%M %p")
            head=SEL+" "+str(round(p,4))+" "+hora
            dr.text((10,10),head,fill=(255,255,255))
            bio=io.BytesIO()
            bio.name="g.png"
            img.save(bio,"PNG")
            bio.seek(0)
            requests.post("https://api.telegram.org/bot"+TOKEN+"/sendPhoto",data={"chat_id":cid,"caption":head+" V112"},files={"photo":bio},timeout=15)
            return "ok",200
        if "COMPRAR" in t:
            ENTS[SEL]=p
            open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
            send(cid,"COMPRADA "+SEL+" "+str(round(p,2))+" V112")
            return "ok",200
        if "VENDER" in t:
            if SEL in ENTS:
                e=ENTS[SEL]
                del ENTS[SEL]
                open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
                pnl=(p/e-1)*100
                send(cid,"CERRADA "+SEL+" "+str(round(pnl,2))+" pct V112")
            else:
                send(cid,"Sin partida "+SEL)
            return "ok",200
        if "PRO" in t:
            if len(ENTS).__eq__(0):
                send(cid,"Sin partidas V112")
            else:
                out="PORTA V112 "
                for k,v in ENTS.items():
                    pp=price(k)
                    if pp.__eq__(0):
                        pp=v
                    pnl=(pp/v-1)*100
                    out=out+k+" "+str(round(pnl,2))+" pct "
                send(cid,out)
            return "ok",200
        send(cid,SEL+" "+str(round(p,4))+" V112 LISTO")
        return "ok",200
    except Exception as e:
        print("WH ERR",e,flush=True)
        import traceback
        traceback.print_exc()
        return "ok",200

print("V112 STARTING", flush=True)
sys.stdout.flush()

if __name__=="__main__":
    try:
        port=int(os.getenv("PORT","10000"))
        print("V112 BIND",port,flush=True)
        app.run(host="0.0.0.0",port=port,debug=False,use_reloader=False,threaded=True)
    except Exception as e:
        print("BIND ERR",e,flush=True)
        import traceback
        traceback.print_exc()
        raise
