import os, json, requests, threading, time
from flask import Flask
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v36-1-final"
app = Flask(__name__)
@app.route('/')
def home(): return "V36.7 7 DIAS EXACTO OK"

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
    try:
        btc = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=8).json()['data']['amount'])
        eth = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=8).json()['data']['amount'])
        xrp = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", timeout=8).json()['data']['amount'])
        fx = 17.22
        try:
            fx = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()['rates']['MXN']
        except: pass
        return btc, eth, xrp, fx
    except:
        return 64338.0, 1900.0, 1.03, 17.22

def get_user(uid, data):
    uid = str(uid)
    if uid not in data["users"]:
        btc, eth, xrp, fx = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp}}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc, eth, xrp, fx = get_market()
    total = u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp
