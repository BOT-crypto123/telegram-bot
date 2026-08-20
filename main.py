import os, time, requests
from flask import Flask, jsonify
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"

CONFIG = {
    "VERSION": "V76 FIX2 10K MXN",
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
    if time.time() - CONFIG["cache"] > 15:
        CONFIG["last_price"] = price
        CONFIG["cache"] = time.time()
    else:
        price = CONFIG["last_price"]
    costo = CONFIG["BALANCE"] / CONFIG["MAX"]
    rows = ""
    tb = 0
    tf = 0
    tn = 0
    for b in CONFIG["bolas"]:
        if b["id"] not in CONFIG["high"]:
            CONFIG["high"][b["id"]] = b["entry"]
        if price > CONFIG["high"][b["id"]]:
            CONFIG["high"][b["id"]] = price
        high = CONFIG["high"][b["id"]]
        dd = (high - price) / high * 100 if high > 0 else 0
        pct = (price - b["entry"]) / b["entry"] * 100
        bruto = costo * pct / 100
        fees = costo * CONFIG["FEES"] / 100 * 2
        neto = bruto - fees
        tb += bruto
        tf += fees
        tn += neto
        vender = pct >= CONFIG["RETAIL_PCT"] and dd >= CONFIG["TRAIL_PCT"]
        estado = "VENDER" if vender else str(round(dd, 2)) + "% DD"
        color = "lime" if neto > 0 else "red"
        rows += "<tr><td>" + str(b["id"]) + "</td><td>$" + str(int(b["entry"])) + "</td><td>" + str(round(pct, 3)) + "%</td><td>$" + str(round(bruto, 2)) + "</td><td>$" + str(round(fees, 2)) + "</td><td style='color:" + color + "'><b>$" + str(round(neto, 2)) + "</b></td><td>" + estado + "</td></tr>"
    return price, costo, rows, tb, tf, tn

@app.route("/")
def dash():
    price, costo, rows, tb, tf, tn = calc()
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

    html = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='15'></head>"
    html += "<body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:12px'>"
    html += "<h3 style='color:#0f0'>" + CONFIG["VERSION"] + " | " + str(len(CONFIG["bolas"])) + "/" + str(CONFIG["MAX"]) + " | FLOAT $" + str(round(tn,2)) + " MXN</h3>"
    html += "<div style='background:#1a1a1a;padding:12px;border-left:4px solid #0f0'>BTC $" + str(int(price)) + " MXN | Por bola $" + str(int(costo)) + " MXN<br><b>BRUTO $" + str(round(tb,2)) + " - FEES $" + str(round(tf,2)) + " = NETO $" + str(round(tn,2)) + " MXN</b></div>"
    html += "<div style='background:#111;padding:12px;margin:10px 0;text-align:center'><a href='/toggle_auto' style='padding:12px 24px;background:" + auto_bg + ";color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>AUTO: " + auto_txt + "</a></div>"
    html += "<div style='background:#111;padding:12px;margin:8px 0'><b>MAX ABIERTAS 2-6 (tu lo ajustas):</b><br><br>" + max_b + "</div>"
    html += "<div style='background:#111;padding:12px;margin:8px 0'><b>TRAIL % 0.1-0.6 (tu lo ajustas):</b><br><br>" + trail_b + " Actual " + str(CONFIG["TRAIL_PCT"]) + "%</div>"
    html += "<div style='background:#111;padding:12px;margin:8px 0;border:1px solid orange'><b>RETAIL % 0.1-0.6 (tu lo ajustas):</b><br><br>" + retail_b + " Actual " + str(CONFIG["RETAIL_PCT"]) + "% = $" + str(round(costo*CONFIG["RETAIL_PCT"]/100,2)) + " MXN</div>"
    html += "<table border=1 style='width:100%;border-collapse:collapse;background:#111' cellpadding=7><tr style='background:#222'><th>#</th><th>Entry</th><th>%</th><th>Bruto</th><th>Fees</th><th>Neto</th><th>Estado</th></tr>"
    if rows == "":
        html += "<tr><td colspan=7 style='text-align:center'>Sin bolas</td></tr>"
    else:
        html += rows
    html += "<tr style='background:#333'><td colspan=3><b>TOTAL FLOAT</b></td><td><b>$" + str(round(tb,2)) + "</b></td><td><b>$" + str(round(tf,2)) + "</b></td><td colspan=2 style='color:lime'><b>$" + str(round(tn,2)) + "</b></td></tr></table>"
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

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

@app.route("/<path:p>", methods=["POST"])
def catch(p):
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
