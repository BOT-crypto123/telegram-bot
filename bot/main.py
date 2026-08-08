import os, requests, time
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
app = Flask(__name__)

SEL = "BTC"
SL = 5.0
TP = 10.0
ENTS = {}
last_p = {}

def price(sym):
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0.0

def send(cid, txt):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]], "resize_keyboard":True}
        requests.post(url, json={"chat_id":cid,"text":txt,"reply_markup":kb}, timeout=10)
    except:
        pass

@app.route("/")
def home():
    p = price(SEL)
    return f"V48 LIVE {SEL} {round(p,2)} SL:-{SL
