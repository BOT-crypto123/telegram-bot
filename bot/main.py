import os, json, requests, threading, time, math
from flask import Flask
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v36-tp-simple"
app = Flask(__name__)
@app.route('/')
def home(): return "V36 TP OK"

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
    btc_p, eth_p, xrp_p, usdmxn = 64408.0, 1904.0, 1.04, 17.20
    br, er, xr = 46.4, 53.3, 32.6
    try:
        btc_p = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth_p = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp_p = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        def rsi(s):
            h=yf.Ticker(s).history(period="1mo")['Close']
            if len(h)<15: return 40.0
            d=h.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
            rs=g.iloc[-1]/l.iloc[-1] if l.iloc[-1]!=0 else 0
            r=100-(100/(1+rs)) if rs!=0 else 50.0
            return 40.
