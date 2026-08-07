import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
VERSION = "V39.6.13 AUTO"
app = Flask(__name__)

LAST = {"BTC": 64657.49, "ETH": 2500.0, "XRP": 0.55}
ENTRY = None # Ahora se pone solo al dar COMPRAR
CHAT_ID_SAVED = None

def get_price_final(coin):
    sym = coin+"USDT"
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=3).json()
        if "price" in r:
            LAST[coin] = float(r["price"])
            return LAST[coin]
    except: pass
    try:
        mp = {"BTC":"bitcoin","ETH":"ethereum","XRP":"ripple"}
        cg = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={mp[coin]}&vs_currencies=usd", timeout=4).json()
        if mp[coin] in cg:
            LAST[coin] = float(cg[mp[coin]]["usd"])
            return LAST[coin]
    except: pass
    try:
        cb = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-USD/spot", timeout=3).json()
        LAST[coin] = float(cb["data"]["amount"])
        return LAST[coin]
    except: pass
    return LAST[coin]

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    kb = {"keyboard": [[{"text":"COMPRAR"},{"text":"VENDER"}],[{"text":"SL"},{"text":"TP"}],[{"text":"GRAF"},{"text":"PRO"}],[{"text":"Apagar"}],[{"text":"ACT"}]],"resize_keyboard": True}
    try: requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=5)
    except: pass

def monitor():
    while True:
        time.sleep(300)
        if CHAT_ID_SAVED is None or ENTRY is None: continue
        try:
            precio = get_price_final("BTC")
            if precio <= ENTRY * 0.95:
                send_msg(CHAT_ID_SAVED, f"🚨 ALERTA VENTA DEMO\nSL -5% TOCADO\nCompraste: {ENTRY:.2f}\nAhora: {precio:.2f}\nPerdida: -5%\n¿VENDER?")
            elif precio >= ENTRY * 1.10:
                send_msg(CHAT_ID_SAVED, f"💰 ALERTA GANANCIA DEMO\nTP +10% TOCADO\nCompraste: {ENTRY:.2f}\nAhora: {precio:.2f}\nGanancia: +10%\n¿VENDER?")
        except: pass

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
            btc = get_price_final("BTC")

            if "/START" in txt or "ACT" in txt:
                if ENTRY is None:
                    send_msg(chat_id, f"{VERSION}\nNo tienes partida abierta\nBTC AHORA: {btc:.2f}\nDale COMPRAR para iniciar")
                else:
                    send_msg(chat_id, f"{VERSION}\nENTRY: {ENTRY:.2f}\nAHORA: {btc:.2f}\nSL: {ENTRY*0.95:.2f}\nTP: {ENTRY*1.10:.2f}\nGanancia actual: {((btc/ENTRY-1)*100):+.2f}%")

            elif "COMPRAR" in txt:
                ENTRY = btc
                send_msg(chat_id, f"🟢 PARTIDA INICIADA\nCompraste DEMO en: {ENTRY:.2f}\nSL: {ENTRY*0.95:.2f}\nTP: {ENTRY*1.10:.2f}\nTe avisaré solo cuando vender")

            elif "VENDER" in txt:
                if ENTRY is None:
                    send_msg(chat_id, "No tienes partida abierta. Dale COMPRAR primero")
                else:
                    gan = (btc/ENTRY-1)*100
                    send_msg(chat_id, f"🔴 PARTIDA CERRADA\nCompraste: {ENTRY:.2f}\nVendiste: {btc:.2f}\nResultado DEMO: {gan:+.2f}%")
                    ENTRY = None

            elif "SL" in txt:
                if ENTRY: send_msg(chat_id, f"SL: {ENTRY*0.95:.2f} (-5%)")
                else: send_msg(chat_id, "Sin partida. Dale COMPRAR")
            elif "TP" in txt:
                if ENTRY: send_msg(chat_id, f"TP: {ENTRY*1.10:.2f} (+10%)")
                else: send_msg(chat_id, "Sin partida. Dale COMPRAR")
            elif "GRAF" in txt:
                send_msg(chat_id, f"BTC: ${btc:.2f}")
        return "ok", 200
    except: return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
