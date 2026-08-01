import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO VICENTE V6 - 1000 MXN ANTI-BLOQUEO", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                d=json.load(f)
                # si es vieja, resetea a 1000 MXN c/u
                if "btc" in d and "mxn" in d["btc"]:
                    return d
        except: pass
    return {"btc": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},"eth": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},"xrp": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0}}

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

CACHE_DOLAR = 18.6

def get_dolar_mxn():
    global CACHE_DOLAR
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        CACHE_DOLAR = r['rates']['MXN']
        return CACHE_DOLAR
    except:
        try:
            r = requests.get("https://api.frankfurter.app/latest?from=USD&to=MXN", timeout=5).json()
            CACHE_DOLAR = r['rates']['MXN']
            return CACHE_DOLAR
        except:
            return CACHE_DOLAR

def get_precios():
    headers = {"User-Agent": "Mozilla/5.0"}
    dolar = get_dolar_mxn()

    # 1. CoinGecko directo en MXN - el mejor, no necesita dolar
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=mxn,usd&include_24hr_change=true", headers=headers, timeout=12).json()
        return {
            "btc": (r['bitcoin']['mxn'], r['bitcoin']['usd_24h_change'], r['bitcoin']['usd']),
            "eth": (r['ethereum']['mxn'], r['ethereum']['usd_24h_change'], r['ethereum']['usd']),
            "xrp": (r['ripple']['mxn'], r['ripple']['usd_24h_change'], r['ripple']['usd']),
            "dolar": dolar
        }
    except Exception as e:
        print(f"fail coingecko: {e}", flush=True)

    # 2. CryptoCompare
    try:
        r = requests.get("https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,XRP&tsyms=USD", headers=headers, timeout=10).json()
        return {
            "btc": (r['RAW']['BTC']['USD']['PRICE']*dolar, r['RAW']['BTC']['USD']['CHANGEPCT24HOUR'], r['RAW']['BTC']['USD']['PRICE']),
            "eth": (r['RAW']['ETH']['USD']['PRICE']*dolar, r['RAW']['ETH']['USD']['CHANGEPCT24HOUR'], r['RAW']['ETH']['USD']['PRICE']),
            "xrp": (r['RAW']['XRP']['USD']['PRICE']*dolar, r['RAW']['XRP']['USD']['CHANGEPCT24HOUR'], r['RAW']['XRP']['USD']['PRICE']),
            "dolar": dolar
        }
    except Exception as e:
        print(f"fail CC: {e}", flush=True)

    # 3. Coinbase + dolar cache
    try:
        btc = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", headers=headers, timeout=8).json()['data']['amount'])
        eth = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", headers=headers, timeout=8).json()['data']['amount'])
        xrp = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", headers=headers, timeout=8).json()['data']['amount'])
        return {"btc":(btc*dolar,0,btc),"eth":(eth*dolar,0,eth),"xrp":(xrp*dolar,0,xrp),"dolar":dolar}
    except Exception as e:
        print(f"fail coinbase: {e}", flush=True)

    return None

def get_keyboard():
    m = types.InlineKeyboardMarkup()
    m.row(types.InlineKeyboardButton("🟢 BTC", callback_data="comprar_btc"), types.InlineKeyboardButton("🟢 ETH", callback_data="comprar_eth"), types.InlineKeyboardButton("🟢 XRP", callback_data="comprar_xrp"))
    m.row(types.InlineKeyboardButton("🔴 BTC", callback_data="vender_btc"), types.InlineKeyboardButton("🔴 ETH", callback_data="vender_eth"), types.InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp"))
    return m

@bot.message_handler(commands=['start','balance'])
def start(msg):
    p = get_precios()
    if not p:
        bot.send_message(msg.chat.id, "⏳ Reintentando precios... espera 15 seg y pon /start otra vez")
        return
    c = load_cartera()
    txt = f"⚡ *VICENTE - 3x $1,000 MXN (5min)*\nDolar: ${p['dolar']:.2f} MXN\n\n"
    total_global = 0
    for mon in ["btc","eth","xrp"]:
        precio_mxn, cambio, precio_usd = p[mon]
        mxn = c[mon]["mxn"]; coin = c[mon]["coin"]
        valor = coin * precio_mxn + mxn
        total_global += valor
        linea = f"*{mon.upper()}*: ${precio_mxn:,.2f} MXN (${precio_usd:,.2f} USD) ({cambio:+.2f}%)\n Saldo: ${mxn:.2f} MXN | {coin:.6f}\n TOTAL {mon.upper()}: ${valor:.2f} MXN"
        if coin>0 and c[mon]["buy"]>0:
            gan = (precio_mxn - c[mon]["buy"])/c[mon]["buy"]*100 - 1.56
            linea += f"\n Gan NETA: {gan:+.2f}%"
        txt += linea + "\n\n"
    txt += f"💰 *TOTAL GLOBAL: ${total_global:.2f} / $3000 MXN*"
    bot.send_message(msg.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda x: True)
def cbq(call):
    c = load_cartera(); pr = get_precios()
    if not pr: bot.answer_callback_query(call.id, "Reintenta en 5 seg"); return
    acc, mon = call.data.split("_")
    precio_mxn = pr[mon][0]
    if acc
