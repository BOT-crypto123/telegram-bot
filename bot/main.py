import json, os, requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

TOKEN = os.getenv("BOT_TOKEN")
DOLAR = 18.65
CARTERA_FILE = "cartera.json"

def cargar_cartera():
    if not os.path.exists(CARTERA_FILE):
        data = {
            "BTC": {"mxn": 1000, "cant": 0, "precio_compra": 0},
            "ETH": {"mxn": 1000, "cant": 0, "precio_compra": 0},
            "XRP": {"mxn": 1000, "cant": 0, "precio_compra": 0}
        }
        with open(CARTERA_FILE, "w") as f: json.dump(data, f)
        return data
    with open(CARTERA_FILE, "r") as f: return json.load(f)

def guardar_cartera(data):
    with open(CARTERA_FILE, "w") as f: json.dump(data, f)

def obtener_precios():
    precios = {}
    try:
        url = 'https://data-api.binance.vision/api/v3/ticker/24hr?symbols=["BTCUSDT","ETHUSDT","XRPUSDT"]'
        r = requests.get(url, timeout=10).json()
        for item in r:
            sym = item['symbol'].replace('USDT','')
            precios[sym] = {
                "usd": float(item['lastPrice']),
                "mxn": float(item['lastPrice']) * DOLAR,
                "cambio": float(item['priceChangePercent'])
            }
        if len(precios)==3: return precios
    except: pass
    try:
        for par, moneda in [("BTCUSD","BTC"),("ETHUSD","ETH"),("XRPUSD","XRP")]:
            r = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={par}", timeout=10).json()
            info = list(r['result'].values())[0]
            last = float(info['c'][0])
            cambio = float(info['p'][1])
            precios[moneda] = {"usd": last, "mxn": last*DOLAR, "cambio": cambio}
        return precios
    except: pass
    return {
        "BTC": {"usd": 62994, "mxn": 62994*DOLAR, "cambio": -2.7},
        "ETH": {"usd": 1866, "mxn":
