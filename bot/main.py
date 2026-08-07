import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app = Flask(__name__)
SEL = "BTC"
SL = 5.0
TP = 10.0

def price(s):
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except:
        return 0

def msg(cid, txt):
    try:
        u = "https://api.telegram.org/bot"+TOKEN+"/sendMessage"
        kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
        requests.post(u, json={"chat_id":cid,"text":txt,"reply_markup":kb}, timeout=8)
    except:
        pass

@app.route("/")
def home():
    return "V47 LIVE SL:"+str(SL)+" TP:"+str(TP), 200

@app.route("/webhook", methods=["POST"])
def wh():
    global SEL, SL, TP
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return "ok",200
        if "message" not in data:
            return "ok",200
        cid = data["message"]["chat"]["id"]
        txt = data["message"].get("text","").upper().strip()
        if txt.startswith("SL "):
            try:
                SL = float(txt.replace("SL","").replace("%","").strip())
            except:
                pass
            msg(cid, "SL -"+str(SL)+"% OK")
            return "ok",200
        if txt.startswith("TP "):
            try:
                TP = float(txt.replace("TP","").replace("%","").strip())
            except:
                pass
            msg(cid, "TP +"+str(TP)+"% OK")
            return "ok",200
        if txt in ["BTC","ETH","SOL","XRP"]:
            SEL = txt
        p = price(SEL)
        msg(cid, SEL+" "+str(round(p,2))+" SL:-"+str(SL)+"% TP:+"+str(TP)+"%")
        return "ok",200
