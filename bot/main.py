import os, requests, time, threading, urllib.parse, json
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V41.5 GRAF NEGRA FIX"
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","XRP"]
ENTRIES = {}
CHAT_ID_SAVED = None
SELECTED = "BTC"

def get_price(sym):
    sym = sym.upper()
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except:
        try:
            ids = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
            cid = ids.get(sym,"bitcoin")
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd", timeout=5).json()
            return float(r[cid]["usd"])
        except:
            return 0.0

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    kb = {"keyboard": [["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]], "resize_keyboard": True}
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=10)
    except:
        pass

def send_chart(chat_id, symbol):
    try:
        ids = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
        cid = ids.get(symbol,"bitcoin")
        data = requests.get(f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=1", timeout=10).json()
        prices = [p[1] for p in data["prices"]][-60:]
        cfg = {"type":"line","data":{"labels":[""]*len(prices),"datasets":[{"data":prices,"borderColor":"#00ff88","backgroundColor":"rgba(0,255,136,0.2)","fill":True,"pointRadius":0,"borderWidth":2}]},"options":{"legend":{"display":False},"title":{"display":True,"text":f"{symbol} {round
