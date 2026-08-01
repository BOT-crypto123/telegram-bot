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
        with open(CARTERA_FILE, "w") as f:
            json.dump(data, f)
        return data
    with open(CARTERA_FILE, "r") as f:
        return json.load(f)

def guardar_cartera(data):
    with open(CARTERA_FILE, "w") as f:
        json.dump(data, f)

def obtener_precios():
    precios = {}
    try:
        url = 'https://data-api.binance.vision/api/v3/ticker/24hr?symbols=["BTCUSDT","ETHUSDT","XRPUSDT"]'
        r = requests.get(url, timeout=10).json()
        for item in r:
            sym = item['symbol'].replace('USDT','')
            usd = float(item['lastPrice'])
            precios[sym] = {"usd": usd, "mxn": usd*DOLAR, "cambio": float(item['priceChangePercent'])}
        if len(precios)==3:
            return precios
    except:
        pass
    return {
        "BTC": {"usd": 62994, "mxn": 1170000, "cambio": -2.7},
        "ETH": {"usd": 1866, "mxn": 34800, "cambio": -2.6},
        "XRP": {"usd": 1.06, "mxn": 20, "cambio": -1.8}
    }

def enviar_balance_separado(update, context):
    precios = obtener_precios()
    cartera = cargar_cartera()
    total_general = 0
    for moneda in ['BTC','ETH','XRP']:
        p = precios[moneda]
        saldo_mxn = cartera[moneda]['mxn']
        cant = cartera[moneda]['cant']
        total_moneda = cant * p['mxn'] + saldo_mxn
        total_general += total_moneda
        texto = f"⚡ {moneda}: ${p['mxn']:,.0f} MXN (${p['usd']:,.2f}) ({p['cambio']:+.2f}%)\n"
        texto += f"Saldo: ${saldo_mxn:.0f} MXN | {cant:.6f}\n"
        if cant > 0:
            gan = ((p['mxn'] / cartera[moneda]['precio_compra']) - 1) * 100 - 1.56
            texto += f"TOTAL {moneda}: ${total_moneda:.0f} MXN Gan: {gan:+.1f}%"
        else:
            texto += f"TOTAL {moneda}: ${total_moneda:.0f} MXN"
        keyboard = [[
            InlineKeyboardButton(f"🟢 COMPRAR {moneda}", callback_data=f"comprar_{moneda}"),
            InlineKeyboardButton(f"🔴 VENDER {moneda}", callback_data=f"vender_{moneda}")
        ]]
