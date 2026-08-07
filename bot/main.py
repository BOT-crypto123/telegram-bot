import os, json, requests, threading, time, math
from flask import Flask
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v36-1-final"
app = Flask(__name__)
@app.route('/')
def home(): return "V36.3 BLINDADO OK"

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

def calc_rsi(symbol):
    try:
        h = yf.Ticker(symbol).history(period="1mo")['Close']
        if len(h) < 15: return 40.0
        d = h.diff(); g = d.where(d>0,0).rolling(14).mean(); l = -d.where(d<0,0).rolling(14).mean()
        rs = g.iloc[-1]/l.iloc[-1] if l.iloc[-1]!=0 else 0
        rsi = 100-(100/(1+rs)) if rs!=0 else 50.0
        return round(float(rsi),1) if not math.isnan(rsi) else 40.0
    except: return 40.0

def get_market():
    try:
        btc = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        fx = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        return btc, eth, xrp, fx, calc_rsi("BTC-USD"), calc_rsi("ETH-USD"), calc_rsi("XRP-USD")
    except: return
