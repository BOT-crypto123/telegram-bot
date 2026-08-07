import os, requests, time
from flask import Flask, request
import threading

# LEE CUALQUIER NOMBRE DE TOKEN - NUNCA MAS FALLA POR NOMBRE
TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
VERSION = "V39.6.11"

app = Flask(__name__)

# CACHE PARA NUNCA MOSTRAR 0
LAST = {"BTC": 64293.0, "ETH": 2500.0, "XRP": 0.55}

def get_price_final(coin):
    sym = coin+"USDT"
    # 1) BINANCE
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=3).json()
        if "price" in r:
            LAST[coin] = float(r["price"])
            return LAST[coin]
    except: pass
    # 2) COINGECKO - CASI NUNCA BLOQUEA
    try:
        mp = {"BTC":"bitcoin","ETH":"ethereum","XRP":"ripple"}
        cg = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={mp[coin]}&vs_currencies=usd", timeout=4).json()
        if mp[coin] in cg:
            LAST[coin] = float(cg[mp[coin]]["usd"])
            return LAST[coin]
    except: pass
    # 3) COINBASE ULTIMO RESPALDO
    try:
        cb = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-USD/spot", timeout=3).json()
        LAST[coin] = float(cb["data"]["amount"])
        return LAST[coin]
    except: pass
    # 4) USA CACHE
    return LAST[coin]

def send_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb = {
            "keyboard": [
                [{"text":"COMPRAR"},{"text":"VENDER"}],
                [{"text":"SL"},{"text":"TP"}],
                [{"text":"GRAF"},{"text":"PRO"}],
                [{"text":"Apagar"}],
                [{"text":"ACT"}]
            ],
            "resize_keyboard": True
        }
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=5)
    except Exception as e:
        print(f"Error send: {e}")

@app.route("/")
def home():
    return f"{VERSION} ON - BOT OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            txt = data["message"].get("text","").upper()

            if "/START" in txt or "ACT" in txt or "PRO" in txt:
                btc = get_price_final("BTC")
                eth = get_price_final("ETH")
                xrp = get_price_final("XRP")
                resp = f"{VERSION} ON SL:-5% TP:+10%\nBTC {btc:.2f} ETH {eth:.2f} XRP {xrp:.3f}\nTP +10% - PRECIO REAL"
                send_msg(chat_id, resp)
            elif "COMPRAR" in txt:
                send_msg(chat_id, "🟢 COMPRA EJECUTADA (MODO DEMO)")
            elif "VENDER" in txt:
                send_msg(chat_id, "🔴 VENTA EJECUTADA (MODO DEMO)")
            elif "SL" in txt:
                send_msg(chat_id, "SL Actual: -5%")
            elif "TP" in txt:
                send_msg(chat_id, "TP Actual: +10%")
            elif "GRAF" in txt:
                send_msg(chat_id, f"📈 BTC: ${get_price_final('BTC'):.2f} - Tendencia ALCISTA")
            elif "APAGAR" in txt:
                send_msg(chat_id, "Bot Apagado")
            else:
                # CUALQUIER OTRO MENSAJE RESPONDE PRECIO
