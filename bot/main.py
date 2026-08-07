import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V41.7 GRAF OK"
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","XRP"]
ENTRIES = {}
CHAT_ID_SAVED = None
SELECTED = "BTC"

def get_price(sym):
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
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
        # grafica negra directa sin JSON complejo
        sym = symbol.lower()
        # usa imagen de tradingview generada
        url_chart = f"https://cryptocharts.example.com"
        # fallback: mandamos foto de coingecko sparkline en negro
        # Usamos quickchart con datos dummy ultra simple
        import urllib.parse
        data = requests.get(f"https://api.coingecko.com/api/v3
