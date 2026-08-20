import os, time, requests
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "VERSION": "V78 FINAL 10K MXN",
    "MAX": 6,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.2,
    "BALANCE": 10000,
    "FEES": 0.1,
    "AUTO": True,
    "bolas": [],
    "last_price": 2050000,
    "cache": 0,
    "high": {}
}

def get_price():
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/BTC-MXN/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except:
        return CONFIG["last_price"]

def calc():
    price = get_price()
    if time.time() - CONFIG["cache"] > 10:
        CONFIG["last_price"] = price
        CONFIG["cache"] = time.time()
    else:
        price = CONFIG["last_price"]
    costo = CONFIG["BALANCE"] / CONFIG["MAX"]
    tb = tf = tn = 0
    rows = ""
    for b in CONFIG["bolas"]:
        if b["id"] not in CONFIG["high"]:
            CONFIG["high"][b["id"]] = b["entry"]
        if price > CONFIG["high"][b["id"]]:
            CONFIG["high"][b["id"]] = price
        pct = (price - b["entry"]) / b["entry"] * 100
        bruto = costo * pct / 100
        fees = costo * CONFIG["FEES"] / 100 * 2
        neto = bruto - fees
        tb += bruto; tf += fees; tn += neto
        rows += str(b["id"]) + " "
    return price, costo, tb, tf, tn

def send_telegram(chat_id, text):
    try:
        url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
    except:
        pass

def get_dash_text():
    price, costo, tb, tf, tn = calc()
    auto_txt = "ON" if CONFIG["AUTO"] else "OFF solo alerta"
    txt = "DASH " + RENDER_URL + "\n"
    txt += str(len(CONFIG["bolas"])) + "/" + str(CONFIG["MAX"]) + " MAX | TRAIL " + str(CONFIG["TRAIL_PCT"]) + "% | RETAIL " + str(CONFIG["RETAIL_PCT"]) + "%\n"
    txt += "BTC $" + str(int(price)) + " MXN\n"
    txt += "BRUTO $" + str(round(tb,2)) + " - FEES $" + str(round(tf,2)) + " = NETO $" + str(round(tn,2)) + " MXN\n"
    txt += "FLOAT $" + str(round(tn,2)) + " MXN\n"
    txt += "AUTO: " + auto_txt + " | Bola $" + str(int(costo)) + " MXN"
    return txt

@app.route("/")
def dash():
    price, costo, tb, tf, tn = calc()
    max_opts = [2,3,4,5,6]
    opts = [0.1,0.2,0.3,0.4,0.5,0.6]
    max_b = ""
    for i in max_opts:
        bg = "#00c853" if i == CONFIG["MAX"] else "#333"
        max_b += "<a href='/set_max/" + str(i) + "' style='margin:3px;padding:10px 16px;background:" + bg + ";color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>" + str(i) + "</a>"
    retail_b = ""
    for r in opts:
        bg = "#ff9800" if r == CONFIG["RETAIL_PCT"] else "#333"
        retail_b += "<a href='/set_retail/" + str(r) + "' style='margin:3px;padding:10px 12px;background:" + bg + ";color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>" + str(r) + "%</a>"
    trail_b = ""
    for p in opts:
        bg = "#00c853" if p == CONFIG["TRAIL_PCT"] else "#333"
        trail_b += "<a href='/set_trail/" + str(p) + "' style='margin:3px;padding:10px 12px;background:" + bg + ";color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>" + str(p) + "%</a>"
    auto_bg = "#00c853" if CONFIG["AUTO"] else "#ff3d00"
    auto_txt = "ON COMPRA SOLO" if CONFIG["AUTO"] else "OFF SOLO ALERTA ENTRADA"
    html = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='15'></head><body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:12px'>"
    html += "<h3 style='color:#0f0'>" + CONFIG["VERSION"] + " | " + str(len(CONFIG["bolas"])) + "/" + str(CONFIG["MAX"]) + " | FLOAT $" + str(round(tn,2)) + " MXN</h3>"
    html += "<div style='background:#1a1a1a;padding:12px;border-left:4px solid #0f0'>BTC $" + str(int(price)) + " MXN | Por bola $" + str(int(costo)) + " MXN<br><b>BRUTO $" + str(round(tb,2)) + " - FEES $" + str(round(tf,2)) + " = NETO $" + str(round(tn,2)) + " MXN</b></div>"
    html += "<div style='background:#111;padding:12px;margin:10px 0;text-align:center'><a href='/toggle_auto' style='padding:12px 24px;background:" + auto_bg + ";color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>AUTO: " + auto_txt + "</a></div>"
    html += "<div style='background:#111;padding:12px;margin:8px 0'><b>MAX 2-6:</b><br><br>" + max_b + "</div>"
    html += "<div style='background:#111;padding:12px;margin:8px 0'><b>TRAIL 0.1-0.6:</b><br><br>" + trail_b + " Actual " + str(CONFIG["TRAIL_PCT"]) + "%</div>"
    html += "<div style='background:#111;padding:12px;margin:8px 0;border:1px solid orange'><b>RETAIL 0.1-0.6:</b><br><br>" + retail_b + " Actual " + str(CONFIG["RETAIL_PCT"]) + "% = $" + str(round(costo*CONFIG["RETAIL_PCT"]/100,2)) + "</div>"
    html += "<p><a href='/comprar' style='background:#2196f3;padding:10px 16px;color:#fff;text-decoration:none;border-radius:6px'>COMPRAR</a> <a href='/reset' style='background:red;padding:10px 16px;color:#fff;text-decoration:none;border-radius:6px;margin-left:8px'>RESET</a></p>"
    html += "</body></html>"
    return html

@app.route("/set_max/<int:n>")
def set_max(n):
    CONFIG["MAX"] = max(2, min(6, n))
    return dash()
@app.route("/set_trail/<float:p>")
def set_trail(p):
    CONFIG["TRAIL_PCT"] = p
    return dash()
@app.route("/set_retail/<float:r>")
def set_retail(r):
    CONFIG["RETAIL_PCT"] = r
    return dash()
@app.route("/toggle_auto")
def toggle():
    CONFIG["AUTO"] = not CONFIG["AUTO"]
    return dash()
@app.route("/comprar")
def comprar():
    if len(CONFIG["bolas"]) < CONFIG["MAX"]:
        nid = len(CONFIG["bolas"]) + 1
        CONFIG["bolas"].append({"id": nid, "entry": CONFIG["last_price"]})
        CONFIG["high"][nid] = CONFIG["last_price"]
    return dash()
@app.route("/reset")
def reset():
    CONFIG["bolas"] = []
    CONFIG["high"] = {}
    return dash()

# TELEGRAM WEBHOOK - ESTO ES LO QUE TE FALTABA
@app.route("/" + BOT_TOKEN, methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"ok": True})
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").upper()

    if text in ["/START", "START", "BTC", "/BTC"]:
        send_telegram(chat_id, "Bot activo\n" + get_dash_text())
    elif "DASHBOARD" in text or text == "DASH":
        send_telegram(chat_id, get_dash_text())
    elif "AUTO ON" in text:
        CONFIG["AUTO"] = True
        send_telegram(chat_id, get_dash_text())
    elif "AUTO OFF" in text:
        CONFIG["AUTO"] = False
        send_telegram(chat_id, get_dash_text())
    elif text == "AUTO ON":
        CONFIG["AUTO"] = True
        send_telegram(chat_id, get_dash_text())
    elif "RESET" in text:
        CONFIG["bolas"] = []
        CONFIG["high"] = {}
        send_telegram(chat_id, "RESET OK\n" + get_dash_text())
    else:
        send_telegram(chat_id, get_dash_text())

    return jsonify({"ok": True})

@app.route("/webhook", methods=["POST"])
def webhook():
    return telegram_webhook()

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
