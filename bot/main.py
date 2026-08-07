import os, json, requests, threading, time
from flask import Flask, request
print("=== V39.6.9 FIX CRASH ===")
BOT=""
for k,v in os.environ.items():
    if not v: continue
    v=str(v).strip()
    if v.startswith("8805451290:"): BOT=v
    if "TELEGRAM_TOKEN" in k: BOT=str(v).strip()
    if "BOT_TOKEN" in k and len(str(v))>30: BOT=str(v).strip()
BOT=BOT.strip()
print(f"BOT: {BOT[:15]}... LEN:{len(BOT)}")

URL=os.environ.get("UPSTASH_REDIS_REST_URL","")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
for k,v in os.environ.items():
    if "UPSTASH" in k and "URL" in k and "https" in str(v): URL=str(v).strip()
    if "UPSTASH" in k and "TOKEN" in k and "REDIS" in k and "8805" not in str(v): TOK=str(v).strip()

KEY="btc-vicente-v36-1-final"
app=Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return f"V39.6.9 LIVE BOT {BOT[:6]} LEN {len(BOT)}"

def load():
    try:
        if not URL or not TOK: return {"users":{}}
        r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
        j=r.json().get("result")
        if j: return json.loads(j)
    except: pass
    return {"users":{}}
def save(d):
    try: requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(d)],timeout=10)
    except: pass
def send(cid,txt,btn=None):
    try:
        p={"chat_id":cid,"text":txt,"parse_mode":"Markdown"}
        if btn: p["reply_markup"]=json.dumps({"inline_keyboard":btn})
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",json=p,timeout=10)
    except Exception as e: print(f"SEND ERR {e}")
def gp(s):
    try: return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}",timeout=5).json()["price"])
    except: return 0

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    try:
        if request.method=="GET": return "V39.6.9 webhook OK"
        data=request.get_json(silent=True)
        if not data: return "ok"
        print(f"HIT {str(data)[:150]}")
        if "message" in data and "text" in data["message"]:
            cid=data["message"]["chat"]["id"]; txt=data["message"]["text"]
            if "/start" in txt:
                db=load(); uid=str(cid)
                if uid not in db.get("users",{}): db.setdefault("users",{})[uid]={"on":True,"sl":-5,"tp":10,"entry":0}
                u=db["users"][uid]; u["on"]=True
                btc,eth,xrp=gp("BTCUSDT") or 64293,gp("ETHUSDT") or 1903,gp("XRPUSDT") or 1.03
                f=f"V39.6.9 ON ✅\nBTC {btc} ETH {eth} XRP {xrp}\nSL:{u.get('sl')}% TP:+{u.get('tp')}%\nFIX CRASH OK"
                btn=[[{"text":"COMPRAR","callback_data":"COMPRAR"},{"text":"VENDER","callback_data":"VENDER"}],[{"text":"SL","callback_data":"SL"},{"text":"TP","callback_data":"TP"}],[{"text":"GRAF","callback_data":"GRAF"},{"text":"PRO","callback_data":"PRO"}],[{"text":"Apagar","callback_data":"APAGAR"}],[{"text":"ACT","callback_data":"ACT"}]]
                send(cid,f,btn); save(db); return "ok"
        if "callback_query" in data:
            cb=data["callback_query"]; cid=cb["message"]["chat"]["id"]; cmd=cb["data"]
            db=load(); uid=str(cid)
            if uid not in db.get("users",{}): db.setdefault("users",{})[uid]={"on":True,"sl":-5,"tp":10,"entry":0}
            u=db["users"][uid]; btc,eth,xrp=gp("BTCUSDT") or 0,gp("ETHUSDT") or 0,gp("XRPUSDT") or 0
            t=cmd
            if cmd=="SL":
                opts=[-3,-5,-7,-10]; cur=u.get("sl",-5); u["sl"]=opts[(opts.index(cur)+1)%4] if cur in opts else -5; t=f"SL {u['sl']}%"
            elif cmd=="TP":
                opts=[5,10,15,20]; cur=u.get("tp",10); u["tp"]=opts[(opts.index(cur)+1)%4] if cur in opts else 10; t=f"TP +{u['tp']}%"
            elif cmd=="APAGAR": u["on"]=False; t="APAGADO"
            elif cmd=="ACT": u["on"]=True; t="PRENDIDO"
            f=f"V39.6.9 {'ON' if u.get('on') else 'OFF'} SL:{u.get('sl')}% TP:+{u.get('tp')}%\nBTC {btc} ETH {eth} XRP {xrp}\n{t}"
            btn=[[{"text":"COMPRAR","callback_data":"COMPRAR"},{"text":"VENDER","callback_data":"VENDER"}],[{"text":"SL","callback_data":"SL"},{"text":"TP","callback_data":"TP"}],[{"text":"GRAF","callback_data":"GRAF"},{"text":"PRO","callback_data":"PRO"}],[{"text":"Apagar","callback_data":"APAGAR"}],[{"text":"ACT","callback_data":"ACT"}]]
            send(cid,f,btn); save(db)
    except Exception as e: print(f"ERR {e}")
    return "ok"

def sethook():
    time.sleep(3)
    try:
        base="https://telegram-bot-cijp.onrender.com"
        r=requests.get(f"https://api.telegram.org/bot{BOT}/setWebhook?url={base}/webhook",timeout=10)
        print(f"SETHOOK -> {r.text}")
    except Exception as e: print(e)

threading.Thread(target=sethook,daemon=True).start()

if __name__=="__main__":
    print("STARTING FLASK")
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
