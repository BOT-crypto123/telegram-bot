import os, time, requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V63 FINAL",
    "BALANCE_TOTAL": 10000,
    "AUTO": False,
    "SYMBOL": "BTC-USD",
    "bolas": [69500, 69800, 70000, 70200, 70500],
    "flot_retail": -68.66,
    "last_price": 0,
    "cache_msg": "Iniciando...",
    "cache_time": 0
}

def get_price():
    # 3 fuentes, si una falla usa otra
    try:
        # 1. Coinbase - el mas estable en USA
        r = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5).json()
        price = float(r["data"]["amount"])
        if price > 0:
            return price
    except: pass
    try:
        # 2. CoinGecko
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5).json()
        return float(r["bitcoin"]["usd"])
    except: pass
    return 0

def get_analysis():
    if time.time() - CONFIG["cache_time"] < 90 and "Iniciando" not in CONFIG["cache_msg"]:
        return CONFIG["cache_msg"]
    try:
        # Candles de Coinbase para EMA
        url = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=900"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers, timeout=8).json()
        # data = [[time, low, high, open, close, volume],...] mas reciente primero
        if not isinstance(data, list) or len(data) < 200:
            raise Exception("Coinbase lista corta")

        data.reverse() # mas viejo a nuevo
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        CONFIG["last_price"] = price

        # EMA 200
        ema = sum(closes[-200:]) / 200
        k = 2 / (200 + 1)
        for p in closes[-200:]:
            ema = p * k + ema * (1-k)

        if price > ema:
            msg = "🟢 <b>BTC-USD COMPRA</b>\nPrecio: $%.2f\nEMA200: $%.2f\nTRAIL %.1f%% MAX %d | %d/5\nFLOT $%.2f" % (price, ema, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]), CONFIG["flot_retail"])
        else:
            msg = "🔴 <b>BTC-USD ESPERA</b>\nPrecio: $%.2f\nEMA200: $%.2f\nBLOQUEADO EMA" % (price, ema)

        CONFIG["cache_msg"] = msg
        CONFIG["cache_time"] = time.time()
        return msg
    except Exception as e:
        print("ANALISIS ERR: %s" % e)
        p = get_price()
        if p > 0:
            CONFIG["last_price"] = p
            msg = "🟡 BTC-USD $%.2f (precio live, EMA no disponible)" % p
            CONFIG["cache_msg"] = msg
            CONFIG["cache_time"] = time.time()
            return msg
        return "Error: %s" % str(e)[:100]

def send_telegram(chat_id, text):
    try:
        url = "https://api.telegram.org/bot%s/sendMessage" % BOT_TOKEN
        kb = {"keyboard": [["BTC","ETH","SOL"],["AUTO ON","DASHBOARD"]], "resize_keyboard": True}
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb, "parse_mode": "HTML"}, timeout=10)
    except: pass

@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"]
    html = "<h3>%s | MAX %d/%d | TRAIL %.1f%% | FLOT $%.2f | AUTO %s</h3>" % (CONFIG["VERSION"], len(CONFIG["bolas"]), CONFIG["MAX"], CONFIG["TRAIL_PCT"], CONFIG["flot_retail"], "ON" if CONFIG["AUTO"] else "OFF")
    html += "<p>Precio: %.2f | <a href='/analisis'>ANALISIS</a> | <a href='/estado'>ESTADO</a></p>" % (CONFIG["last_price"])
    html += "<p>Costo bola: $%.2f</p><p><a href='/set_max/5'>MAX 5</a> | <a href='/set_trail/0.1'>TRAIL 0.1%%</a> | <a href='/reset'>RESET</a></p>" % costo
    html += "<pre>%s</pre><pre>%s</pre>" % (CONFIG["cache_msg"], str(CONFIG))
    return html

@app.route("/analisis")
def analisis_route():
    return get_analysis().replace("<b>","").replace("</b>","")

@app.route("/set_max/<int:n>")
def set_max(n):
    CONFIG["MAX"] = n
    return jsonify(CONFIG)

@app.route("/set_trail/<float:p>")
def set_trail(p):
    CONFIG["TRAIL_PCT"] = p
    return jsonify(CONFIG)

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

@app.route("/reset")
def reset():
    CONFIG["bolas"] = []
    CONFIG["flot_retail"] = 0
    return jsonify(CONFIG)

@app.route("/%s" % BOT_TOKEN, methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True) or {}
        msg = data.get("message", {})
        text = msg.get("text","").strip().upper()
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id: return jsonify({"ok": True})
        print("TG: %s" % text)

        if "DASHBOARD" in text:
            send_telegram(chat_id, "%s\nTRAIL %.1f%% MAX %d | %d/5 | FLOT $%.2f\n%s" % (RENDER_URL, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]), CONFIG["flot_retail"], get_analysis()))
        elif "AUTO" in text:
            CONFIG["AUTO"] = not CONFIG["AUTO"]
            send_telegram(chat_id, "AUTO %s\n%s" % ("ON" if CONFIG["AUTO"] else "OFF", get_analysis()))
        elif "BTC" in text:
            CONFIG["SYMBOL"] = "BTC-USD"
            send_telegram(chat_id, get_analysis())
        elif "/START" in text:
            send_telegram(chat_id, "✅ V63 FINAL Live\n%s\n%s" % (RENDER_URL, get_analysis()))
        else:
            send_telegram(chat_id, get_analysis())
        return jsonify({"ok": True})
    except Exception as e:
        print(e)
        return jsonify({"ok": True})

@app.route("/<path:p>", methods=["POST"])
def catch_all(p):
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
