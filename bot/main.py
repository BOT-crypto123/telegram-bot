import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v31-eternal-final"

app = Flask(__name__)
@app.route('/')
def home(): return "V31 OK"

def load_data():
    try:
        if not URL or not REST_TOKEN: return {"users":{}}
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res = r.json().get("result")
        if res: return json.loads(res)
    except: pass
    return {"users":{}}

def save_data(data):
    try:
        j = json.dumps(data)
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, j], timeout=10)
    except: pass

def get_market():
    try:
        def get_one(sym):
            t = yf.Ticker(sym)
            price = float(t.fast_info['last_price'])
            hist = t.history(period="1mo")
            try:
                pct = float((hist['Close'].iloc[-1]/hist['Close'].iloc[-2]-1)*100)
            except:
                pct = 0.0
            try:
                delta = hist['Close'].diff()
                gain = delta.where(delta>0,0).rolling(window=14).mean()
                loss = -delta.where(delta<0,0).rolling(window=14).mean()
                rs = gain / loss
                rsi_val = 100 - (100 / (1 + rs.iloc[-1]))
                rsi = float(rsi_val)
                if rsi!= rsi: rsi = 40.0
            except:
                rsi = 40.0
            return price, pct, round(rsi,1)

        btc_p, btc_pct, btc_rsi = get_one("BTC-USD")
        eth_p, eth_pct, eth_rsi = get_one("ETH-USD")
        xrp_p, xrp_pct, xrp_rsi = get_one("XRP-USD")
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        return btc_p, eth_p, xrp_p, usdmxn, btc_pct, eth_pct, xrp_pct, btc_rsi, eth_rsi, xrp_rsi
    except:
        return 64286.86, 1901.13, 1.03, 17.20, -0.48, -0.28, -2.57, 36.9, 47.1, 34.9

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc_p, eth_p, xrp_p, usdmxn, _,_,_, _,_,_ = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/usdmxn)/btc_p,"eth":(333.33/usdmxn)/eth_p,"xrp":(333.33/usdmxn)/xrp_p,"inicial":1000.0}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr = get_market
