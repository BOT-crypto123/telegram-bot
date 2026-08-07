import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V39.6.14 FIX"
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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    kb = {"keyboard": [[{"text":"COMPRAR"},{"text":"VENDER"}],[{"text":"SL"},{"text":"TP"}],[{"text":"GRAF"},{"text":"PRO"}],[{"text":"Apagar"}],[{"text":"ACT"}]], "resize_keyboard": True}
    requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=10)

def monitor():
    while True:
        time.sleep(300)
        if CHAT_ID_SAVED and ENTRY:
            try:
                p = get_btc()
                if p <= ENTRY * 0.95:
                    send_msg(CHAT_ID_SAVED, f"🚨 ALERTA VENTA\nSL -5%\nCompra: {ENTRY:.2f}\nAhora: {p:.2f}")
                if p >= ENTRY * 1.10:
                    send_msg(CHAT_ID_SAVED, f"💰 ALERTA GANANCIA\nTP +10%\nCompra: {ENTRY:.2f}\nAhora: {p:.2f}")
            except:
                pass

threading.Thread(target=monitor, daemon=True).start()

@app.route("/")
def home():
    e = f"{ENTRY:.2f}" if ENTRY else "Sin partida"
    return f"{VERSION} ON - ENTRY {e}", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    global CHAT_ID_SAVED, ENTRY
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            CHAT_ID_SAVED = chat_id
            txt = data["message"].get("text","").upper()
            btc = get_btc()
            if "/START" in txt or "ACT" in txt or "PRO" in txt:
                if ENTRY is None:
                    send_msg(chat_id, f"{VERSION}\nSin partida\nBTC: {btc:.2f}\nDale COMPRAR")
                else:
                    send_msg(chat_id, f"{VERSION}\nENTRY: {ENTRY:.2f}\nAHORA: {btc:.2f}\nSL: {ENTRY*0.95:.2f}\nTP: {ENTRY*1.10:.2f}\nGan: {(btc/ENTRY-1)*100:+.2f}%")
            elif "COMPRAR" in txt:
                ENTRY = btc
                send_msg(chat_id, f"🟢 PARTIDA INICIADA\nCompra: {ENTRY:.2f}\nSL: {ENTRY*0.95:.2f}\nTP: {ENTRY*1.10:.2f}")
            elif "VENDER" in txt:
                if ENTRY is None:
                    send_msg(chat_id, "Sin partida")
                else:
                    send_msg(chat_id, f"🔴 CERRADA\nCompra: {ENTRY:.2f}\nVenta: {btc:.2f}\nRes: {(btc/ENTRY-1)*100:+.2f}%")
                    ENTRY = None
            elif "SL" in txt:
                send_msg(chat_id, f"SL: {ENTRY*0.95:.2f}" if ENTRY else "Sin partida")
            elif "TP" in txt:
                send_msg(chat_id, f"TP: {ENTRY*1.10:.2f}" if ENTRY else
