import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
VERSION = "V39.6.14 AUTO FIX"
app = Flask(__name__)

LAST = {"BTC": 64747.51, "ETH": 2500.0, "XRP": 0.55}
ENTRY = None
CHAT_ID_SAVED = None

def get_price_final(coin):
    sym = coin+"USDT"
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=3).json()
        if "price" in r:
            LAST[coin] = float(r["price"])
            return LAST[coin]
    except: pass
    try:
        mp
