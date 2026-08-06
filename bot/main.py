import os, json, requests, threading, time
from flask import Flask
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Soporta BOT_TOKEN o TELEGRAM_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v29-final"

app = Flask(__name__)
@app.route('/')
def home(): return "V29 ETERNO-UPSTASH OK"

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

def get_prices():
    try:
        btc_t = yf.Ticker("BTC-USD")
        eth_t = yf.Ticker("ETH-USD")
        xrp_t = yf.Ticker("XRP-USD")
        mxn_t = yf.Ticker("USDMXN=X")
        btc = float(btc_t.fast_info['last_price'])
        eth = float(eth_t.fast_info['last_price'])
        xrp = float(xrp_t.fast_info['last_price'])
        usdmxn = float(mxn_t.fast_info['last_price'])
        # % cambio 24h
        def pct(t):
            try: return float(t.history(period="2d")['Close'].pct_change().iloc[-1]*100)
            except: return 0.0
        def rsi(ticker):
            try:
                hist = yf.Ticker(ticker).history(period="14d")['Close']
                delta = hist.diff()
                gain = delta.where(delta>0,0).rolling(14).mean()
                loss = -delta.where(delta<0,0).rolling(14).mean()
                rs = gain/loss
                return round(100-(100/(1+rs.iloc[-1])),1)
            except: return 35.0
        return btc, eth, xrp, usdmxn, pct(btc_t), pct(eth_t), pct(xrp_t), rsi("BTC-USD"), rsi("ETH-USD"), rsi("XRP-USD")
    except:
        return 64157, 1898, 1.03, 17.23, -0.66, -0.49, -2.77, 34.4, 44.5, 32.8

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc_p, eth_p, xrp_p, usdmxn, _,_,_, _,_,_ = get_prices()
        data["users"][uid] = {
            "efectivo": 0.0,
            "btc": (333.33/usdmxn)/btc_p,
            "eth": (333.33/usdmxn)/eth_p,
            "xrp": (333.33/usdmxn)/xrp_p,
            "inicial": 1000.0
        }
        save_data(data)
    return data["users"][uid]

def texto_portfolio(u):
    btc_p, eth_p, xrp_p, usdmxn, pb, pe
