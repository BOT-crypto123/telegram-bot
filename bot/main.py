import os, time, threading, json, requests
from flask import Flask, request
import redis

TOKEN = os.getenv("TELE_TOKEN") or "8805451290:AAFiI1Oa2bYh3Gp4tJ9kLmN8pQrStUvWxYzAbC" # TU TOKEN COMPLETO AQUI
REDIS_URL = os.getenv("REDIS_URL")
WEBHOOK_URL = "https://telegram-bot-cijp.onrender.com/webhook"
VERSION = "V39.6.10"

app = Flask(__name__)

# Redis
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("Redis OK")
except:
    r = None
    print("Redis FAIL")

def get_cfg():
    if r:
        d = r.get("cfg")
        if d: return json.loads(d)
    return {"sl": -5, "tp": 10, "on": True}

def save_cfg(c):
    if r: r.set("cfg", json.dumps(c))

def gp(s):
    # V39.6.10 - 3 FUENTES
    try:
        # 1. Binance
        j = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}",timeout=4).json()
        p = float(j["price"])
        if p > 0: return p
    except: pass
    try:
        # 2. Bybit respaldo
        j = requests.get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={s}",timeout=4).json()
        p = float(j["result"]["list"][0]["lastPrice"])
        if p > 0: return p
    except: pass
    try:
        # 3. CoinGecko respaldo
        m={"BTCUSDT":"bitcoin","ETHUSDT":"ethereum","XRPUSDT":"ripple"}
        cid=m.get(s,"bitcoin")
        j = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd",timeout=5).json()
        p = float(j[cid]["usd"])
        if p > 0: return p
    except: pass
    return 0

def send_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb = {
            "keyboard":[
                [{"text":"COMPRAR"},{"text":"VENDER"}],
                [{"text":"SL"},{"text":"TP"}],
                [{"text":"GRAF"},{"text":"PRO"}],
                [{"text":"Apagar"}],
                [{"text":"ACT"}]
            ],
            "resize_keyboard":True
        }
        data = {"chat_id":chat_id,"text":text,"reply_markup":json.dumps(kb)}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

@app.route("/")
def home():
    btc = gp("BTCUSDT")
    return f"{VERSION} LIVE BOT 880545 LEN 46 BTC {btc}"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        if "message" not in update: return "ok"
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text","")

        cfg = get_cfg()
        sl = cfg.get("sl",-5)
        tp = cfg.get("tp",10)
        on = cfg.get("on",True)

        btc = gp("BTCUSDT")
        eth = gp("ETHUSDT")
        xrp = gp("XRPUSDT")

        if text == "/start" or text == "ACT":
            resp = f"{VERSION} {'ON' if on else 'OFF'} SL:{sl}% TP:+{tp}%\nBTC {btc} ETH {eth} XRP {xrp}\nTP +{tp}%"
            send_msg(chat_id, resp)
        elif text == "SL":
            sl = -7 if sl==-5 else -10 if sl==-7 else -15 if sl==-10 else -5
            cfg["sl"]=sl
            save_cfg(cfg)
            send_msg(chat_id, f"{VERSION} ON SL:{sl}% TP:+{tp}%\nBTC {btc} ETH {eth} XRP {xrp}\nSL {sl}%")
        elif text == "TP":
            tp = 15 if tp==10 else 20 if tp==15 else 30 if tp==20 else 10
            cfg["tp"]=tp
            save_cfg(cfg)
            send_msg(chat_id, f"{VERSION} ON SL:{sl}% TP:+{tp}%\nBTC {btc} ETH {eth} XRP {xrp}\nTP +{tp}%")
        elif text == "COMPRAR":
            send_msg(chat_id, f"COMPRA SIMULADA\nBTC {btc} SL {sl}% TP {tp}%")
