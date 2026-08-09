from flask import Flask
import os, json, requests, threading
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "trades.json"
app = Flask(__name__)

def load():
    try:
        with open(CHAT_FILE,"r") as f:
            return json.load(f)
    except:
        return {"trades":[],"balance":0,"chat_id":None}

def save(d):
    with open(CHAT_FILE,"w") as f:
        json.dump(d,f)

def resumen():
    d=load()
    return f"Balance: ${d.get('balance',0):.2f} Trades: {len(d.get('trades',[]))}"

def send_msg(cid, txt):
    if not TOKEN or not cid:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":cid,"text":txt})
    except:
        pass

@app.route("/")
def home():
    for path in ["bot/templates/index.html","templates/index.html","bot/templates/index.html".replace("bot/","")]:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    if os.path.exists("bot/templates/index.html"):
        with open("bot/templates/index.html", encoding="utf-8") as f:
            return f.read()
    return "<h1>BOT V506 LIVE</h1><p>Sube el archivo templates/index.html</p>"

@app.route("/api/balance")
def bal():
    d=load()
    return {"balance":d.get("balance",0),"trades":len(d.get("trades",[]))}

@app.route("/webhook", methods=["POST"])
def webhook():
    from flask import request
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{})
    cid=msg.get("chat",{}).get("id")
    txt=msg.get("text","")
    d=load()
    if cid:
        d["chat_id"]=cid
        save(d)
    if txt in ["/balance","/resumen"]:
        send_msg(cid, resumen())
    return "ok"

def loop_10pm():
    tz=pytz.timezone("America/Mexico_City")
    while True:
        now=datetime.now(tz)
        if now.hour==22 and now.minute==0:
            d=load()
            if d.get("chat_id"):
                send_msg(d.get("chat_id"), resumen())
            import time
            time.sleep(61)
        import time
        time.sleep(30)

threading.Thread(target=loop_10pm, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
