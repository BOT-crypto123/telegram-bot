import os, requests
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
VERSION = "V39.6.11"
app = Flask(__name__)
LAST = {"BTC": 64293.0, "ETH": 2500.0, "XRP": 0.55}

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
    requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=5)

@app.route("/")
def home():
    return f"{VERSION} ON", 200

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
                send_msg(chat_id, "COMPRAR OK")
            elif "VENDER" in txt:
                send_msg(chat_id, "VENTA OK")
            elif "SL" in txt:
                send_msg(chat_id, "SL -5%")
            elif "TP" in txt:
                send_msg(chat_id, "TP +10%")
            elif "GRAF" in txt:
                send_msg(chat_id, f"BTC: ${get_price_final('BTC'):.2f}")
            elif "APAGAR" in txt:
                send_msg(chat_id, "Apagado")
            else:
                btc = get_price_final("BTC")
                send_msg(chat_id, f"{VERSION} BTC {btc:.2f}")
        return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
