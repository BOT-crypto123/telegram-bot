import os,requests,re,io,json,threading,time
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
print("V110 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/bot_110.json"
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

def price(s):
    try:
        u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
        r=requests.get(u,timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0.0

def get_candles(sym):
    try:
        u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
        r=requests.get(u,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
        return sorted(r)[-70:]
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

def send_text(cid,txt):
    try:
        url="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"],["AUTO ON","AUTO OFF"]],"resize_keyboard":True}
        requests.post(url,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=12)
    except:
        pass

def analyze(sym):
    candles=get_candles(sym)
    if len(candles).__eq__(0):
        return None
    closes=[]
    for c in candles:
        closes.append(c[4])
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
        score=67
    if p.__lt__(e9) and e9.__lt__(e21):
        pred="BAJADA"
        senial="VENTA"
        score=66
    if rsi.__lt__(35) and p.__gt__(e9):
        pred="SUBIDA FUERTE"
        senial="COMPRA FUERTE"
        score=89
    if rsi.__lt__(30):
        pred="SUBIDA FUERTE"
        senial="COMPRA FUERTE"
        score=93
    if rsi.__gt__(65) and p.__lt__(e9):
        pred="BAJADA FUERTE"
        senial="VENTA FUERTE"
        score=87
    if rsi.__gt__(70):
        pred="BAJADA FUERTE"
        senial="VENTA FUERTE"
        score=92
    return {"p":p,"candles":candles,"ema9":ema9,"ema21":ema21,"rsi":rsi,"pred":pred,"senial":senial,"score":score}

def auto_loop():
    print("V110 AUTO START",flush=True)
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
                    txt="ALERTA V110 "+sym+" "+info["senial"]+" Precio "+str(round(info["p"],2))+" RSI "+str(round(info["rsi"],1))
                    send_text(cid,txt)
                    time.sleep(2)
        except Exception as e:
            print("AUTO ERR",e,flush=True)
            time.sleep(30)

threading.Thread(target=auto_loop,daemon=True).start()

@app.route("/")
def home():
    return "V110 LIVE",200

@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    try:
        d=request.get_json(force=True,silent=True)
        if not d or "message" not in d:
            return "ok",200
        msg=d.get("message")
        cid=msg.get("chat").get("id")
        text_raw=msg.get("text","")
        t=text_raw.upper().strip()
        CONFIG["LAST_CID"]=cid
        save()
        if "AUTO ON" in t:
            CONFIG["AUTO"]=True
            save()
            send_text(cid,"V110 AUTO ON 2min")
            return "ok",200
        if "AUTO OFF" in t:
            CONFIG["AUTO"]=False
            save()
            send_text(cid,"V110 AUTO OFF")
            return "ok",200
        for s in ["BTC","ETH","SOL","XRP"]:
            if s in t:
                SEL=s
        p_now=price(SEL)
