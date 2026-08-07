import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V39.6.14.2 FIX"
app = Flask(__name__)

ENTRY = None
CHAT_ID_SAVED = None

def get_btc():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5).json()
        return float(r["price"])
    except:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5).json()
            return float(r["bitcoin"]["usd"])
        except:
            return 64747.0

def send_msg(chat_id, text):
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    kb = {"keyboard": [[{"text":"COMPRAR"},{"text":"VENDER"}],[{"text":"SL"},{"text":"TP"}],[{"text":"GRAF"},{"text":"PRO"}],[{"text":"Apagar"}],[{"text":"ACT"}]], "resize_keyboard": True}
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=10)
    except:
        pass

def monitor():
    while True:
        time.sleep(300)
        if CHAT_ID_SAVED and ENTRY:
            try:
                p = get_btc()
                if p <= ENTRY * 0.95:
                    send_msg(CHAT_ID_SAVED, "ALERTA VENTA SL -5% Compra " + str(round(ENTRY,2)) + " Ahora " + str(round(p,2)))
                if p >= ENTRY * 1.10:
                    send_msg(CHAT_ID_SAVED, "ALERTA GANANCIA TP +10% Compra " + str(round(ENTRY,2)) + " Ahora " + str(round(p,2)))
            except:
                pass

threading.Thread(target=monitor, daemon=True).start()

@app.route("/")
def home():
    if ENTRY is None:
        e = "Sin partida"
    else:
        e = str(round(ENTRY,2))
    return VERSION + " ON - ENTRY " + e
