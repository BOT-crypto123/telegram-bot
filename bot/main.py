import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V39.7 LIVE FINAL"
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
    return VERSION + " ON - ENTRY " + e, 200

@app.route("/webhook", methods=["POST"])
def webhook():
    global CHAT_ID_SAVED, ENTRY
    try:
        data = request.get_json(force=True, silent=True)
        if not data: return "ok", 200
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            CHAT_ID_SAVED = chat_id
            txt = data["message"].get("text","").upper()
            btc = get_btc()
            if "/START" in txt or "ACT" in txt or "PRO" in txt:
                if ENTRY is None:
                    send_msg(chat_id, VERSION + "\nSin partida\nBTC: " + str(round(btc,2)) + "\nDale COMPRAR")
                else:
                    sl = ENTRY * 0.95
                    tp = ENTRY * 1.10
                    gan = (btc/ENTRY-1)*100
                    send_msg(chat_id, VERSION + "\nENTRY: " + str(round(ENTRY,2)) + "\nAHORA: " + str(round(btc,2)) + "\nSL: " + str(round(sl,2)) + "\nTP: " + str(round(tp,2)) + "\nGan: " + str(round(gan,2)) + "%")
            elif "COMPRAR" in txt:
                ENTRY = btc
                sl = ENTRY * 0.95
                tp = ENTRY * 1.10
                send_msg(chat_id, "PARTIDA INICIADA\nCompra: " + str(round(ENTRY,2)) + "\nSL: " + str(round(sl,2)) + "\nTP: " + str(round(tp,2)))
            elif "VENDER" in txt:
                if ENTRY is None:
                    send_msg(chat_id, "Sin partida")
                else:
                    gan = (btc/ENTRY-1)*100
                    send_msg(chat_id, "CERRADA\nCompra: " + str(round(ENTRY,2)) + "\nVenta: " + str(round(btc,2)) + "\nRes: " + str(round(gan,2)) + "%")
                    ENTRY = None
            elif "SL" in txt:
                send_msg(chat_id, "SL: " + str(round(ENTRY*0.95,2)) if ENTRY else "Sin partida")
            elif "TP" in txt:
                send_msg(chat_id, "TP: " + str(round(ENTRY*1.10,2)) if ENTRY else "Sin partida")
            elif "GRAF" in txt:
                send_msg(chat_id, "BTC: $" + str(round(btc,2)))
        return "ok", 200
    except:
        return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
