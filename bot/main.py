import os, json, requests, threading, time, traceback
from flask import Flask, request

print("V39.6.5 FINAL FIX START + XRP")

BOT = os.environ.get("BOT_TOKEN")
if not BOT:
    for k, v in os.environ.items():
        if "TELE" in k and "TOKEN" in k:
            BOT = v

URL = os.environ.get("UPSTASH_REDIS_REST_URL")
TOK = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

for k, v in os.environ.items():
    if "UPSTASH" in k and "URL" in k:
        URL = v
    if "UPSTASH" in k and "TOKEN" in k:
        if "REDIS" in k and v!= BOT:
            TOK = v

KEY = "btc-vicente-v36-1-final"
app = Flask(__name__)

@app.route("/")
def home():
    return "V39.6.5 LIVE - FIX XRP"

def load():
    try:
        if not URL or not TOK:
            return {"users": {}}
        r = requests.post(URL, headers={"Authorization": f"Bearer {TOK}"}, json=["GET", KEY], timeout=10)
        j = r.json().get("result")
        if j:
            return json.loads(j)
    except Exception as e:
        print(f"load {e}")
    return {"users": {}}

def save(data):
    try:
        requests.post(URL, headers={"Authorization": f"Bearer {TOK}"}, json=["SET", KEY, json.dumps(data)], timeout=10)
    except:
        pass

def send_msg(chat_id, text, buttons=None):
    try:
        url = f"https://api.telegram.org/bot{BOT}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if buttons:
            payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(e)

def gp(sym):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=5).json()
        return float(r["price"])
    except:
        return 0

def get_prices():
    return gp("BTCUSDT") or 64293, gp("ETHUSDT") or 1903, gp("XRPUSDT") or 1.03

def get_rsi(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100", timeout=8).json()
        closes = [float(c[4]) for c in r]
        deltas = [closes[i]-closes[i-1] for i in range(1, len(closes))]
        gains = [d if d>0 else 0 for d in deltas]
        losses = [-d if d<0 else 0 for d in deltas]
        ag = sum(gains[-14:])/14
        al = sum(losses[-14:])/14
        if al == 0:
            return 70
        return round(100-(100/(1+ag/al)), 1)
    except:
        return 50

def get_user(chat_id):
    db = load()
    uid = str(chat_id)
    if uid not in db.get("users", {}):
        db.setdefault("users", {})[uid] = {"on": True, "sl": -5, "tp": 10, "entry": 0, "last_rsi_alert": {}}
        save(db)
    return db, uid

def check_loop():
    while True:
        try:
            time.sleep(300)
            db = load()
            if not db.get("users"):
                continue
            btc, eth, xrp = get_prices()
            rb = get_rsi("BTCUSDT")
            re = get_rsi("ETHUSDT")
