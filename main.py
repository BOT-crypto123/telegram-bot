import os
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V59 ANALISIS ON",
    "BALANCE_TOTAL": 10000,
    "bolas": [],
    "last_buy_time": 0,
    "flot_retail": -68.66,
    "analisis_log": "Esperando"
}

def get_analysis():
    try:
        import yfinance as yf
        df = yf.download("BTC-USD", period="2d", interval="5m", progress=False)
        if len(df) < 200:
            return False, "Sin datos"
        close = df["Close"]
        ema200 = close.ewm(span=200).mean().iloc[-1]
        price = float(close.iloc[-1])
        return price > ema200, f"Price {price:.0f} EMA {ema200:.0f}"
    except Exception as e:
        return False, str(e)[:80]

@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"]
    max_btns = ""
    for i in range(1,7):
        max_btns += '<a href="/set_max/%d">[%d]</a> ' % (i,i)
    trail_btns = ""
    for p in [0.1,0.2,0.3,0.4,0.6,0.8,1.0]:
        trail_btns += '<a href="/set_trail/%s">%s%%</a> ' % (p,p)
    
    html = "<html><body style='font-family:monospace;background:#111;color:#0f0;padding:15px'>"
    html += "<h2>%s | MAX %d/%d | TRAIL %s%% | FLOT $%s</h2>" % (CONFIG["VERSION"], len(CONFIG["bolas"]), CONFIG["MAX"], CONFIG["TRAIL_PCT"], CONFIG["flot_retail"])
    html += "<p>Costo bola: $%.2f | Balance: $%s</p>" % (costo, CONFIG["BALANCE_TOTAL"])
    html += "<p><b>MAX:</b> <a href='/set_max/%d'>-</a> %s <a href='/set_max/%d'>+</a></p>" % (max(1,CONFIG["MAX"]-1), max_btns, CONFIG["MAX"]+1)
    html += "<p><b>TRAIL:</b> %s <a href='/set_trail/%s'>+</a></p>" % (trail_btns, CONFIG["TRAIL_PCT"]+0.1)
    html += "<p>Analisis: %s</p>" % CONFIG["analisis_log"]
    html += "<p><a href='/analisis'>PROBAR ANALISIS</a> | <a href='/estado'>ESTADO</a> | <a href='/reset'>RESET</a></p>"
    html += "<pre>Bolas: %s</pre></body></html>" % str(CONFIG["bolas"])
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
def analisis():
    ok, msg = get_analysis()
    CONFIG["analisis_log"] = msg
    return jsonify({"pasa": ok, "msg": msg})

@app.route("/reset")
def reset():
    CONFIG["bolas"] = []
    CONFIG["flot_retail"] = 0
    return jsonify(CONFIG)

BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"

@app.route("/%s" % BOT_TOKEN, methods=["POST"])
def webhook_token():
    try:
        data = request.get_json(force=True, silent=True) or {}
        txt = ""
        if "message" in data:
            txt = data["message"].get("text","")
        print("TG WEBHOOK OK: %s" % txt)
        return jsonify({"ok": True})
    except Exception as e:
        print("TG ERROR %s" % e)
        return jsonify({"ok": True})

@app.route("/webhook", methods=["POST"])
def webhook_alias():
    return webhook_token()

@app.route("/<path:token_path>", methods=["POST"])
def catch_all(token_path):
    if len(token_path) > 20:
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
