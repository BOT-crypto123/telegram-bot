import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO VICENTE V7 - BINANCE 1000MXN", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"
PRECIO_FILE = "precio_cache.json"
DOLAR = 18.65

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                d=json.load(f)
                if "btc" in d and "mxn" in d["btc"]:
                    return d
        except: pass
    return {"btc": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},"eth": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},"xrp": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0}}

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def save_cache(p):
    try:
        with open(PRECIO_FILE, "w") as f:
            json.dump(p, f)
    except: pass

def load_cache():
    if os.path.exists(PRECIO_FILE):
        try:
            with open(PRECIO_FILE, "r") as f:
                return json.load(f)
        except: pass
    return None

def get_precios():
    headers = {"User-Agent": "Mozilla/5.0"}
    # 1. BINANCE - Nunca falla en Render
    try:
        def get_bin(symbol):
            d = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", headers=headers, timeout=8).json()
            return float(d['lastPrice']), float(d['priceChangePercent'])
        btc_u, btc_c = get_bin("BTCUSDT")
        eth_u, eth_c = get_bin("ETHUSDT")
        xrp_u, xrp_c = get_bin("XRPUSDT")
        res = {"btc": (btc_u*DOLAR, btc_c, btc_u), "eth": (eth_u*DOLAR, eth_c, eth_u), "xrp": (xrp_u*DOLAR, xrp_c, xrp_u), "dolar": DOLAR}
        save_cache(res)
        print(f"BINANCE OK BTC {btc_u}", flush=True)
        return res
    except Exception as e:
        print(f"fail binance: {
