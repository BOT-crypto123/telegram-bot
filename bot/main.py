import os,requests,re,io,json,sys,threading,time
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
print("V113 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b113.json"
CONFIG={"AUTO":False,"LAST_CID":0,"LAST_ALERT":""}

def load():
    try:
        if os.path.exists(FILE):
            d=json.load(open(FILE))
            ENTS.update(d.get("ENTS",{}))
            CONFIG.update(d.get("CONFIG",{}))
    except:
        pass
def save():
    try:
        open(FILE,"w").write(json.dumps({"ENTS":ENTS,"CONFIG":CONFIG}))
    except:
        pass
load()
print("V113 LOADED",flush=True)

def price(s):
    try:
        u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
        return float(requests.get(u,timeout=8).json()["data"]["amount"])
    except:
        return 0.0

def candles(sym):
    try:
        u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
        return sorted(requests.get(u,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json())[-70:]
    except:
        return []

def ema_calc(prices,period):
    if len(prices).__lt__(period):
        return []
    k=2/(period+1)
    ema=[sum(prices[:period])/period]
    for p in prices[period:]:
        ema.append(p*k+ema[-1]*(1-k))
    return ema

def rsi_calc(prices):
    if len(prices).__lt__(15):
        return 50.0
    gains=0.0
    losses=0.0
    for i in range(1,15):
        d=prices[i]-prices[i-1]
        if d.__ge__(0):
            gains+=d
        else:
            losses-=d
    if losses.__eq__(0):
        return 88.0
    if gains.__eq__(0):
        return 12.0
    rs=gains/losses
    return 100-100/(1+rs)

def send(cid,txt):
    try:
        url="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"],["AUTO ON","AUTO OFF"]],"resize_keyboard":True}
        requests.post(url,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=12)
    except:
        pass

def analyze(sym):
    cl=candles(sym)
    if len(cl).__eq__(0):
        return None
    closes=[c[4] for c in cl]
    p=price(sym)
    if p.__eq__(0):
        p=closes[-1]
    ema9=ema_calc(closes,9)
    ema21=ema_calc(closes,21)
    rsi=rsi_calc(closes)
    if len(ema9).__eq__(0) or len(ema21).__eq__(0):
        return None
    e9=ema9[-1]
    e21=ema21[-1]
    pred="NEUTRAL"
    senial="ESPERAR"
    score=50
    if p.__gt__(e9) and e9.__gt__(e21):
        pred="SUBIDA"
        senial="COMPRA"
        score=68
    if p.__lt__(e9) and e9.__lt__(e21):
        pred="BAJADA"
        senial="VENTA"
        score=66
    if rsi.__lt__(30):
        pred="SUBIDA FUERTE"
        senial="COMPRA FUERTE"
        score=92
    if rsi.__gt__(70):
        pred="BAJADA FUERTE"
        senial="VENTA FUERTE"
        score=91
    return {"p":p,"cl":cl,"closes":closes,"ema9":ema9,"ema21":ema21,"rsi":rsi,"pred":pred,"senial":senial,"score":score}

def auto_loop():
    while True:
        try:
            time.sleep(120)
            if CONFIG.get("AUTO").__eq__(False):
                continue
            cid=CONFIG.get("LAST_CID")
            if cid.__eq__(0):
                continue
            for sym in ["BTC","ETH","SOL","XRP"]:
                info=analyze(sym)
                if info is None:
                    continue
                if "FUERTE" in info["senial"]:
                    key=sym+info["senial"]+str(int(info["p"]))
                    if CONFIG.get("LAST_ALERT").__eq__(key):
                        continue
                    CONFIG["LAST_ALERT"]=key
                    save()
                    txt="ALERTA V113 "+sym+" "+info["senial"]+" "+str(round(info["p"],4))+" RSI "+str(round(info["rsi"],1))
                    send(cid,txt)
                    time.sleep(2)
        except:
            time.sleep(30)

threading.Thread(target=auto_loop,daemon=True).start()

@app.route("/")
def home():
    return "V113 LIVE",200

@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    try:
        d=request.get_json(force=True,silent=True)
        if not d or "message" not in d:
            return "ok",200
        cid=d["message"]["chat"]["id"]
        t=d["message"].get("text","").upper().strip()
        CONFIG["LAST_CID"]=cid
        save()
        if "AUTO ON" in t:
            CONFIG["AUTO"]=True
            save()
            send(cid,"V113 AUTO ON 2min")
            return "ok",200
        if "AUTO OFF" in t:
            CONFIG["AUTO"]=False
            save()
            send(cid,"V113 AUTO OFF")
            return "ok",200
        for s in ["BTC","ETH","SOL","XRP"]:
            if s in t:
                SEL=s
        p_now=price(SEL)
        if p_now.__eq__(0) and SEL in ENTS:
            p_now=ENTS[SEL]["entry"]
        if "GRAF" in t:
            from PIL import Image,ImageDraw
            info=analyze(SEL)
            if info is None:
                send(cid,"Sin datos "+SEL)
                return "ok",200
            cl=info["cl"]
            p=info["p"]
            rsi=info["rsi"]
            pred=info["pred"]
            senial=info["senial"]
            score=info["score"]
            mn=min(info["closes"])
            mx=max(info["closes"])
            if mn.__eq__(mx):
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
                if yt.__eq__(yb):
                    yb=yt+2
                col=(0,230,118)
                if cc.__lt__(o):
                    col=(255,61,87)
                dr.line([x+3,y1,x+3,y2],fill=col,width=1)
                dr.rectangle([x,yt,x+6,yb],fill=col)
                idx+=1
            if SEL in ENTS:
                entry=ENTS[SEL]["entry"]
                ye=H-70-(entry-mn)/(mx-mn)*(H-100)
                dr.line([0,ye,W,ye],fill=(255,234,0),width=2)
            hora=(datetime.utcnow()-timedelta(hours=6)).strftime("%I:%M %p")
            e9v=round(info["ema9"][-1],4)
            e21v=round(info["ema21"][-1],4)
            txt_head=SEL+" "+str(round(p,4))+" | "+hora
            if SEL in ENTS:
                entry=ENTS[SEL]["entry"]
                pnl=(p/entry-1)*100
                sgn="+"
                if pnl.__lt__(0):
                    sgn=""
                txt_head=txt_head+" | "+sgn+str(round(pnl,2))+"%"
            dr.text((12,10),txt_head,fill=(255,255,255))
            cap=SEL+" "+str(round(p,4))+" | "+hora+" | "+str(round((p/ENTS[SEL]["entry"]-1)*100,2))+"% " if SEL in ENTS else SEL+" "+str(round(p,4))+" | "+hora
            cap=SEL+" "+str(round(p,4))+" | "+hora
            if SEL in ENTS:
                entry=ENTS[SEL]["entry"]
                pnl=(p/entry-1)*100
                sgn="+"
                if pnl.__lt__(0):
                    sgn=""
                cap=cap+" | "+sgn+str(round(pnl,2))+"%"
            cap=cap+"\nEMA9:"+str(e9v)+" EMA21:"+str(e21v)+"\nRSI:"+str(round(rsi,1))+" PRED:"+pred+" "+str(score)+"%\nSENAL:"+senial+" V113"
            bio=io.BytesIO()
            bio.name="g.png"
            img.save(bio,"PNG")
            bio.seek(0)
            requests.post("https://api.telegram.org/bot"+TOKEN+"/sendPhoto",data={"chat_id":cid,"caption":cap},files={"photo":bio},timeout=15)
            return "ok",200
        if "COMPRAR" in t:
            nums=re.findall(r"[\d\.]+",t)
            m=100.0
            try:
                m=float(nums[0])
            except:
                m=100.0
            ENTS[SEL]={"entry":p_now,"usd":m}
            save()
            send(cid,"COMPRADA "+SEL+" "+str(round(p_now,4))+" V113")
            return "ok",200
        if "VENDER" in t:
            if SEL in ENTS:
                e=ENTS[SEL]["entry"]
                usd=ENTS[SEL].get("usd",100)
                pnl=(p_now/e-1)*100
                profit=usd*(pnl/100)
                del ENTS[SEL]
                save()
                sgn="+"
                if pnl.__lt__(0):
                    sgn=""
                send(cid,"CERRADA "+SEL+" "+sgn+str(round(pnl,2))+"% "+sgn+str(round(profit,2))+" V113")
            else:
                send(cid,"Sin partida "+SEL)
            return "ok",200
        if "PRO" in t:
            if len(ENTS).__eq__(0):
                send(cid,"Sin partidas V113")
            else:
                out="PORTA V113 "
                total=0.0
                for k,v in ENTS.items():
                    pp=price(k)
                    if pp.__eq__(0):
                        pp=v["entry"]
                    pnl=(pp/v["entry"]-1)*100
                    profit=v.get("usd",100)*(pnl/100)
                    total+=profit
                    s
