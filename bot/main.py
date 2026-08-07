import os, requests, time, threading, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, request
from io import BytesIO

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V41.1 4 COINS"
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","XRP"]
ENTRIES = {}
CHAT_ID_SAVED = None
SELECTED = "BTC"

def get_price(sym="BTC"):
    sym=sym.upper()
    try:
        r=requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",timeout=5).json()
        return float(r["data"]["amount"])
    except: pass
    try:
        ids={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
        cid=ids.get(sym,"bitcoin")
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd",timeout=5).json()
        return float(r[cid]["usd"])
    except:
        return 0.0

def send_msg(chat_id,text):
    url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    kb={"keyboard":[[{"text":"BTC"},{"text":"ETH"}],[{"text":"SOL"},{"text":"XRP"}],[{"text":"COMPRAR"},{"text":"VENDER"}],[{"text":"GRAF"},{"text":"PRO"}]],"
