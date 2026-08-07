import os, json, requests, threading, math, time
from flask import Flask
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v35-2-final-7porciento"

app = Flask(__name__)
@app.route('/')
def home(): return "V35.2 FINAL -7% OK"

def load_data():
    try:
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res = r.json().get("result")
        if res: return json.loads(res)
    except: pass
    return {"users":{}}

def save_data(data):
    try:
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, json.dumps(data)], timeout=10)
    except: pass

def get_market():
    btc_p, eth_p, xrp_p, usdmxn = 64254.34, 1901.30, 1.03, 17.20
    bp, ep, xp, br, er, xr = 0.0, 0.0, -2.5, 40.0, 40.0, 32.0
    try:
        btc_p = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth_p = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp_p = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        def pct(s):
            h=yf.Ticker(s).history(period="2d")['Close']
            return float((h.iloc[-1]/h.iloc[-2]-1)*100) if len(h)>=2 else 0.0
        bp, ep, xp = pct("BTC-USD"), pct("ETH-USD"), pct("XRP-USD")
        def rsi(s):
            h=yf.Ticker(s).history(period="1mo")['Close']
            if len(h)<15: return 40.0
            d=h.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
            rs=g.iloc[-1]/l.iloc[-1] if l.iloc[-1]!=0 else 0
            r=100-(100/(1+rs)) if rs!=0 else 50.0
            return 40.0 if math.isnan(r
