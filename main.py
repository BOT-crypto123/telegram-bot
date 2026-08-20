import os, time, requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V62 BINANCE",
    "BALANCE_TOTAL": 10000,
    "AUTO": False,
    "SYMBOL": "BTCUSDT",
    "bolas": [69500, 69800, 70000, 70200, 70500],
    "flot_retail": -68.66,
    "last_price": 0,
    "cache_msg": "Iniciando...",
    "cache_time": 0
}

def get_binance_price(symbol="BTCUSDT"):
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=%s" % symbol
        r = requests.get(url, timeout=5).json()
        return float(r["price"])
    except Exception as e:
        print("BINANCE ERR %s" % e)
        return 0

def get_analysis():
    # Cache 2 min para no saturar
    if time.time() - CONFIG["cache_time"] < 120 and CONFIG["cache_msg"]!= "Iniciando...":
        return CONFIG["cache_msg"]

    try:
        # Klines para EMA 200
        url = "https://api.binance.com/api/v3/klines?symbol=%s&interval=15m&limit=210" % CONFIG["SYMBOL"]
        data = requests.get(url, timeout=8).json()
        if not isinstance(data, list) or len(data) < 200:
            raise Exception("Binance vacio")

        closes = [float(c[4]) for c in data]
        price = closes[-1]
        CONFIG["last_price"] = price

        # EMA 200 manual
        ema = sum(closes[-200:]) / 200
        # EMA mas precisa
        k = 2 / (200 + 1)
        for p in closes[-200:]:
            ema = p * k + ema * (1-k)

        if price > ema:
            msg = "🟢 <b>%s COMPRA</b>\nPrecio: $%.2f\nEMA200: $%.2f\nTRAIL %.1f%% MAX %d | %d/5 | FLOT $%.2f" % (CONFIG["SYMBOL"], price, ema, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]), CONFIG["flot_retail"])
        else:
            msg = "🔴 <b>%s VENTA / ESPERA</b>\nPrecio: $%.2f\nEMA200: $%.2f\nBLOQUEADO por EMA" % (CONFIG["SYMBOL"], price, ema)

        CONFIG["cache_msg"] = msg
        CONFIG["cache_time"] = time.time()
        return msg
    except Exception as e:
        print("ANALISIS ERR %s" % e)
        # Fallback solo precio
        p = get_binance_price(CONFIG["SYMBOL"])
        if p > 0:
            msg = "🟡 %s $%.2f (sin EMA, error api)" % (CONFIG["SYMBOL"], p)
            CONFIG["cache_msg"] = msg
            CONFIG["cache_time"] = time.time()
            return msg
        return "Error: %s" % str(e)[:80]

def send_telegram(chat_id, text):
    try:
        url = "https://api.telegram.org/bot%s/sendMessage" % BOT_TOKEN
        kb = {"keyboard": [["BTC","ETH","SOL"],["XAUUSD","NVDA","TSLA"],["AUTO ON","DASHBOARD"]], "resize_keyboard": True}
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("SEND ERR %s" % e)

@app.route("/")
def dashboard():
    html = "<h2>%s | MAX %d/%d | TRAIL %s%% | FLOT $%s | AUTO %s</h2>" % (CONFIG["VERSION"], len(CONFIG["bolas"]), CONFIG["MAX"], CONFIG["TRAIL_PCT"], CONFIG["flot_retail"], "ON" if CONFIG["AUTO"] else "OFF")
    html += "<p>Precio: %s | %s</p>" % (CONFIG["last_price"], CONFIG["cache_msg"])
    html += "<p><a href='/set_max/5'>MAX5</a> <a href='/set_trail/0.1'>TRAIL 0.1</a> <a href='/reset'>RESET</a> <a href='/analisis'>ANALISIS</a></p>"
    html += "<pre>%s</pre>" % str(CONFIG)
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
    return jsonify(CONFIG)

@app.route("/%s" % BOT_TOKEN, methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("message", {})
    text = msg.get("text","").strip().upper()
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return jsonify({"ok": True})
    print("TG: %s" % text)

    if "DASHBOARD" in text:
        send_telegram(chat_id, "%s\nTRAIL %.1f%% MAX %d | %d/5 | FLOT $%.2f\n%s" % (RENDER_URL, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]), CONFIG["flot_retail"], CONFIG["cache_msg"]))
    elif "AUTO" in text:
        CONFIG["AUTO"] = not CONFIG["AUTO"]
        send_telegram(chat_id, "AUTO %s\n%s" % ("ON" if CONFIG["AUTO"] else "OFF", get_analysis()))
    elif text == "BTC":
        CONFIG["SYMBOL"] = "BTCUSDT"
        send_telegram(chat_id, get_analysis())
    elif text == "ETH":
        CONFIG["SYMBOL"] = "ETHUSDT"
        send_telegram(chat_id, get_analysis())
    elif text == "SOL":
        CONFIG["SYMBOL"] = "SOLUSDT"
        send_telegram(chat_id, get_analysis())
    elif "/START" in text:
        send_telegram(chat_id, "✅ V62 Binance Live\n%s\n%s" % (RENDER_URL, get_analysis()))
    else:
        send_telegram(chat_id, "%s\n%s" % (RENDER_URL, get_analysis()))
    return jsonify({"ok": True})

@app.route("/<path:p>", methods=["POST"])
def catch_all(p):
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
