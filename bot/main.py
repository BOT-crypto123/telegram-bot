import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v32-botones"

app = Flask(__name__)
@app.route('/')
def home(): return "V32 BOTONES OK"

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
    btc_p, eth_p, xrp_p, usdmxn = 64200.0, 1900.0, 1.03, 17.20
    try:
        def get_one(sym):
            t = yf.Ticker(sym)
            price = float(t.fast_info['last_price'])
            return price
        btc_p = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth_p = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp_p = float(yf.Ticker("XRP-USD
