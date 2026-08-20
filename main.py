import os, time, requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V61 ANTI-BAN",
    "BALANCE_TOTAL": 10000,
    "AUTO": True,
    "SYMBOL": "BTC-USD",
    "bolas": [69500, 69800, 70000, 70200, 70500],
    "flot_retail": -68.66,
    "last_price": 0,
    "cache_analisis": "Iniciando...",
    "cache_time": 0
}

def get_price_binance(symbol="BTCUSDT"):
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=%s" % symbol, timeout=5).json()
        return float(r["price"])
    except:
        return 0

def get_analysis_cached(symbol="BTC-USD"):
    # Si tiene menos de 3 minutos, usa cache para no ser baneado
    if time.time() - CONFIG["cache_time"] < 180 and CONFIG["cache_analisis"] != "Iniciando...":
        return CONFIG["cache_analisis"]
    
    try:
        import yfinance as yf
        df = yf.download(symbol, period="1d", interval="30m", progress=False)
        close = df["Close"]
        ema200 = float(close.ewm(span=200).mean().iloc[-1])
        price = float(close.iloc[-1])
        CONFIG["last_price"] = price
        msg = "🟢 %s OK %.0f > EMA %.0f" % (symbol, price, ema200) if price > ema200 else "🔴 %s BLOQ %.0f < EMA %.0f" % (symbol, price, ema200)
        CONFIG["cache_analisis"] = msg
        CONFIG["cache_time"] = time.time()
        return msg
    except Exception as e:
        err = str(e)
        if "Rate" in err or "Too Many" in err:
            # Fallback a Binance cuando Yahoo banea
            bin_price = get_price_binance("BTCUSDT")
            if bin_price > 0:
                CONFIG["last_price"] = bin_price
                msg = "🟡 %s Binance %.0f (Yahoo baneado, usando cache)" % (symbol, bin_price)
                CONFIG["cache_analisis"] = msg
                CONFIG["cache_time"] = time.time()
                return msg
            return "⏳ Yahoo baneado, espera 5 min. Ultimo: %s" % CONFIG["cache_analisis"]
        return "Error: %s" % err[:80]

def send_telegram(chat_id, text):
    try:
        url = "https://api.telegram.org/bot%s/sendMessage" % BOT_TOKEN
        kb = {"keyboard": [["BTC","ETH","SOL"],["XAUUSD","NVDA","TSLA"],["AUTO ON","DASHBOARD"]], "resize_keyboard": True}
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("SEND ERR %s" % e)

@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"]
    html = "<h2>%s | MAX %d/%d | TRAIL %s%% | $%s | AUTO %s</h2>" % (CONFIG["VERSION"], len(CONFIG["bolas"]), CONFIG["MAX"], CONFIG["TRAIL_PCT"], CONFIG["flot_retail"], "ON" if CONFIG["AUTO"] else "OFF")
    html += "<p>Precio: %s | %s</p>" % (CONFIG["last_price"], CONFIG["cache_analisis"])
    html += "<p><a href='/set_max/5'>MAX 5</a> | <a href='/set_trail/0.1'>TRAIL 0.1</a> | <a href='/reset'>RESET</a> | <a href='/analisis'>ANALISIS</a></p>"
    html += "<pre>%s</pre>" % str(CONFIG)
    return html

@app.route("/set_max/<int:n>")
def set_max(n):
    CONFIG["MAX"] = n
    return jsonify(CONFIG)

@app.route("/set_trail/<float:p>")
def set_trail(p):
    CONFIG["TRAIL_PCT"] = p
    return jsonify(CONFIG)

@app.route("/analisis")
def analisis():
    return get_analysis_cached(CONFIG["SYMBOL"])

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
    try:
        data = request.get_json(force=True, silent=True) or {}
        msg = data.get("message", {})
        text = msg.get("text","").strip().upper()
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return jsonify({"ok": True})
        print("TG: %s" % text)
        
        if "DASHBOARD" in text:
            reply = "%s\nTRAIL %.1f%% MAX %s | %s/5\n%s" % (RENDER_URL, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]), CONFIG["cache_analisis"])
            send_telegram(chat_id, reply)
        elif "AUTO" in text:
            CONFIG["AUTO"] = not CONFIG["AUTO"]
            send_telegram(chat_id, "AUTO %s\n%s" % ("ON" if CONFIG["AUTO"] else "OFF", get_analysis_cached(CONFIG["SYMBOL"])))
        elif text in ["BTC","ETH","SOL"]:
            mp = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD"}
            CONFIG["SYMBOL"] = mp.get(text,"BTC-USD")
            send_telegram(chat_id, get_analysis_cached(CONFIG["SYMBOL"]))
        elif "/START" in text:
            send_telegram(chat_id, "✅ V61 Anti-Ban Live\n%s" % RENDER_URL)
        else:
            send_telegram(chat_id, "%s\n%s" % (RENDER_URL, CONFIG["cache_analisis"]))
        return jsonify({"ok": True})
    except Exception as e:
        print("ERR %s" % e)
        return jsonify({"ok": True})

@app.route("/<path:p>", methods=["POST"])
def catch_all(p):
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
