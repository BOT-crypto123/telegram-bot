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
def home(): return "V21 RECUADROS LIVE - OK"
@app.route('/health')
def hl(): return "OK"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

def get_prices():
    global CACHE
    if time.time() - CACHE["t"] < 60 and CACHE["data"]:
        return CACHE["data"]
    # Intento Binance
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]"
        r = requests.get(url, timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        data = {"btc": d['BTCUSDT'], "eth": d['ETHUSDT'], "xrp": d['XRPUSDT']}
        CACHE = {"t": time.time(), "data": data
