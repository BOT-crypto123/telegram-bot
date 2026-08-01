import os, json, threading, time, sys
print("=== V21 RECUADROS VICENTE ===", flush=True)
from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_FILE = "/tmp/chat_id.txt"
BALANCE_FILE = "/tmp/balance.json"
CACHE = {"t":0, "data":None}
INIT = 1000.0
COMISION = 0.0078

app = Flask(__name__)
@app.route('/')
def home(): return "V21 RECUADROS LIVE"
@app.route('/health')
def hl(): return "OK"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

def get_prices():
    global CACHE
    if time.time() - CACHE["t"] < 60 and CACHE["data"]: return CACHE["data"]
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]"
        r = requests.get(url, timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        data = {"btc": d['BTCUSDT'], "eth": d['ETHUSDT'], "xrp": d['XRPUSDT']}
        CACHE = {"t": time.time(), "data": data}
        return data
    except: pass
    try:
        g = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true", timeout=10).json()
        data = {"btc": (float(g['bitcoin']['usd']), float(g['bitcoin']['usd_24h_change'])), "eth": (float(g['ethereum']['usd']), float(g['ethereum']['usd_24h_change'])), "xrp": (float(g['ripple']['usd']), float(g['ripple']['usd_24h_change']))}
        CACHE = {"t": time.time(), "data": data}
        return data
    except:
        if CACHE["data"]: return CACHE["data"]
        return {"btc": (63000, 0.5), "eth": (3400, 0.8), "xrp": (0.6, 1.2)}

def load_bal():
    try:
        with open(BALANCE_FILE,'r') as f: return json.load(f)
    except:
        return {"btc": (INIT/3)/68000, "eth": (INIT/3)/3400, "xrp": (INIT/3)/0.6, "usd":0, "init":INIT, "p_btc":68000,"p_eth":3400,"p_xrp":0.6}
def save_bal
