import os, time, requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V60",
    "BALANCE_TOTAL": 10000,
    "AUTO": False,
    "SYMBOL": "BTC-USD",
    "bolas": [69500, 69800, 70000, 70200, 70500],
    "flot_retail": -68.66,
    "analisis_log": "Esperando"
}

def send_telegram(chat_id, text):
    try:
        url = "https://api.telegram.org/bot%s/sendMessage" % BOT_TOKEN
        kb = {
            "keyboard": [["BTC","ETH","SOL"],["XAUUSD","NVDA","TSLA"],["AUTO ON","DASHBOARD"]],
            "resize_keyboard": True
        }
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("SEND ERR %s" % e)

def get_analysis(symbol="BTC-USD"):
    try:
        import yfinance as yf
        df = yf.download(symbol, period="1d", interval="15m", progress=False)
        close = df["Close"]
        ema200 = close.ewm(span=200).mean().iloc[-1]
        price = float(close.iloc[-1])
        if price > ema200:
            return "🟢 <b>%s COMPRA</b> | Price %.0f > EMA %.0f | TRAIL %.1f%% MAX %d | %d/5" % (symbol, price, ema200, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]))
        else:
            return "🔴 <b>%s BLOQUEADO EMA</b> | Price %.0f < EMA %.0f" % (symbol, price, ema200)
    except Exception as e:
        return "Error analisis: %s" % str(e)[:100]

@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"]
    max_btns = ""
    for i in range(1,7):
        max_btns += '<a href="/set_max/%d">[%d]</a> ' % (i,i)
    html = "<html><body style='font-family:monospace;background:#111;color:#0f0;padding:15px'>"
    html += "<h2>%s | MAX %d/%d | TRAIL %s%% | FLOT $%s | AUTO %s</h2>" % (CONFIG["VERSION"], len(CONFIG["bolas"]), CONFIG["MAX"], CONFIG["TRAIL_PCT"], CONFIG["flot_retail"], "ON" if CONFIG["AUTO"] else "OFF")
    html += "<p>Costo bola: $%.2f | Symbol: %s</p>" % (costo, CONFIG["SYMBOL"])
    html += "<p>MAX: %s</p>" % max_btns
    html += "<p>TRAIL: <a href='/set_trail/0.1'>0.1%%</a> <a href='/set_trail/0.3'>0.3%%</a> <a href='/set_trail/1.0'>1.0%%</a></p>"
    html += "<p><a href='/analisis'>ANALISIS</a> | <a href='/estado'>ESTADO</a> | <a href='/reset'>RESET</a></p>"
    html += "<pre>%s</pre></body></html>" % str(CONFIG)
    return html

@app.route("/set_max/<int:n>")
def set_max(n):
    CONFIG["MAX"] = max(1, min(20, n))
    return jsonify(CONFIG)

@app.route("/set_trail/<float:p>")
def set_trail(p):
    CONFIG["TRAIL_PCT"] = p
    return jsonify(CONFIG)

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

@app.route("/analisis")
def analisis_route():
    msg = get_analysis(CONFIG["SYMBOL"])
    CONFIG["analisis_log"] = msg
    return msg

@app.route("/reset")
def reset():
    CONFIG["bolas"] = []
    return jsonify(CONFIG)

# --- TELEGRAM WEBHOOK CON RESPUESTA ---
@app.route("/%s" % BOT_TOKEN, methods=["POST"])
@app.route("/webhook", methods=["POST"])
@app.route("/telegram", methods=["POST"])
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
            reply = "%s\nTRAIL %.1f%% MAX %s | %s/5\nFLOT $%s | AUTO %s" % (RENDER_URL, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"]), CONFIG["flot_retail"], "ON" if CONFIG["AUTO"] else "OFF")
            send_telegram(chat_id, reply)
        elif "AUTO ON" in text or "AUTO" == text:
            CONFIG["AUTO"] = not CONFIG["AUTO"]
            send_telegram(chat_id, "🤖 AUTO %s\n%s" % ("ON" if CONFIG["AUTO"] else "OFF", get_analysis(CONFIG["SYMBOL"])))
        elif text in ["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]:
            mapping = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
            CONFIG["SYMBOL"] = mapping.get(text, "BTC-USD")
            send_telegram(chat_id, get_analysis(CONFIG["SYMBOL"]))
        elif "/START" in text:
            send_telegram(chat_id, "✅ <b>BTC Vicente V60 Live</b>\n%s\n\nUsa los botones:" % RENDER_URL)
        else:
            send_telegram(chat_id, "📊 %s\nTRAIL %.1f%% MAX %d | %d/5" % (RENDER_URL, CONFIG["TRAIL_PCT"], CONFIG["MAX"], len(CONFIG["bolas"])))

        return jsonify({"ok": True})
    except Exception as e:
        print("WEBHOOK ERR %s" % e)
        return jsonify({"ok": True})

@app.route("/<path:p>", methods=["POST"])
def catch_all(p):
    if len(p) > 15:
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
