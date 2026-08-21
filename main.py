import os, time, requests, threading, json
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
RENDER_URL = "https://telegram-bot-cijp.onrender.com"
DATA_FILE = "data.json"

DEFAULT = {
    "VERSION": "V94 FINAL PERSISTENTE",
    "COINS": ["BTC", "ETH", "SOL", "DOGE"],
    "ACTIVOS": ["SOL", "ETH", "DOGE"],
    "MAX": 3,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.4,
    "BALANCE": 10310.00,
    "BALANCE_INICIAL": 10000.0,
    "DIA_ACTUAL": 2,
    "DIAS_TOTAL": 30,
    "FEES_PCT": 0.1,
    "AUTO": True,
    "bolas": [],
    "prices": {"SOL": 1484.31, "DOGE": 1.39, "BTC": 1232606.83, "ETH": 39814.75},
    "high": {},
    "history": {"SOL": [], "DOGE": [], "BTC": [], "ETH": []},
    "trades_hoy": 8,
    "profit_hoy": 310.00,
    "profit_bruto": 340.00,
    "profit_fees": 30.00,
    "profit_por_moneda": {"BTC": 0, "ETH": 120, "SOL": 150, "DOGE": 40},
    "trades_log": [],
    "chat_id": 0
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                d = json.load(f)
                for k, v in DEFAULT.items():
                    if k not in d:
                        d[k] = v
                return d
        except:
            pass
    return DEFAULT.copy()

def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(CONFIG, f)
    except:
        pass

CONFIG = load_data()

def get_all_prices():
    for coin in CONFIG["COINS"]:
        try:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-MXN/spot", timeout=4).json()
            CONFIG["prices"][coin] = float(r["data"]["amount"])
            CONFIG["history"][coin].append(CONFIG["prices"][coin])
            if len(CONFIG["history"][coin]) > 60:
                CONFIG["history"][coin].pop(0)
        except:
            pass

def send_tg(text):
    try:
        if CONFIG["chat_id"] == 0:
            return
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CONFIG["chat_id"], "text": text}, timeout=5)
    except:
        pass

def check_auto():
    while True:
        try:
            get_all_prices()
            for coin in CONFIG["ACTIVOS"]:
                hist = CONFIG["history"][coin]
                if len(hist) < 10:
                    continue
                price = CONFIG["prices"][coin]
                max_20 = max(hist[-20:])
                min_5 = min(hist[-5:])
                dip = (price - max_20) / max_20 * 100
                recuperacion = (price - min_5) / min_5 * 100
                entrada_inteligente = dip <= -0.4 and 0.05 <= recuperacion <= 0.3

                if CONFIG["AUTO"] and entrada_inteligente and len(CONFIG["bolas"]) < CONFIG["MAX"]:
                    costo = CONFIG["BALANCE"] / CONFIG["MAX"]
                    nid = int(time.time()) % 10000
                    CONFIG["bolas"].append({"id": nid, "coin": coin, "entry": price, "costo": costo, "time": time.strftime("%H:%M")})
                    CONFIG["high"][str(nid)] = price
                    CONFIG["trades_log"].insert(0, f"{time.strftime('%H:%M')} ROBOT COMPRO {coin} ${price:.2f} dip {dip:.2f}%")
                    save_data()

                for b in CONFIG["bolas"][:]:
                    if b["coin"]!= coin:
                        continue
                    key = str(b["id"])
                    if key not in CONFIG["high"]:
                        CONFIG["high"][key] = b["entry"]
                    if price > CONFIG["high"][key]:
                        CONFIG["high"][key] = price
                    high = CONFIG["high"][key]
                    gain = (price - b["entry"]) / b["entry"] * 100
                    trail = (price - high) / high * 100
                    if gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]:
                        bruto = b["costo"] * gain / 100
                        fees = b["costo"] * CONFIG["FEES_PCT"] / 100 * 2
                        neto = bruto - fees
                        CONFIG["BALANCE"] += neto
                        CONFIG["profit_hoy"] += neto
                        CONFIG["profit_bruto"] += bruto
                        CONFIG["profit_fees"] += fees
                        CONFIG["profit_por_moneda"][b["coin"]] += neto
                        CONFIG["trades_hoy"] += 1
                        log = f"{time.strftime('%H:%M')} VENDIO {b['coin']} E${b['entry']:.2f}->${price:.2f} BRUTO ${bruto:.2f} FEES ${fees:.2f} NETO ${neto:.2f}"
                        CONFIG["trades_log"].insert(0, log)
                        if neto > 0:
                            send_tg(f"💰 VENDI {b['coin']} CON GANANCIA\nE ${b['entry']:.2f} -> ${price:.2f} ({gain:.2f}%)\nNETO ${neto:.2f} BALANCE ${CONFIG['BALANCE']:.2f}\n{RENDER_URL}")
                        CONFIG["bolas"].remove(b)
                        save_data()
            time.sleep(30)
        except:
            time.sleep(30)

def keep_alive():
    while True:
        try:
            time.sleep(600)
            requests.get(RENDER_URL, timeout=5)
            print("SELF PING ANTI-SLEEP OK")
        except:
            pass

threading.Thread(target=check_auto, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/")
def dash():
    get_all_prices()
    costo = CONFIG["BALANCE"] / CONFIG["MAX"]
    acumulado = CONFIG["BALANCE"] - CONFIG["BALANCE_INICIAL"]
    dia = CONFIG["DIA_ACTUAL"]
    total = CONFIG["DIAS_TOTAL"]
    pct_circle = (dia / total) * 100
    circ = 283
    offset = circ - (pct_circle / 100 * circ)

    html = f"""<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='15'><title>MAQUINA DINEROS</title></head>
<body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px;text-align:center'>
<style>
.circle-wrap {{ position:relative; width:220px; height:220px; margin:20px auto; }}
.circle-wrap svg {{ transform: rotate(-90deg); width:220px; height:220px; }}
.circle-bg {{ fill:none; stroke:#222; stroke-width:12; }}
.circle-fill {{ fill:none; stroke:#FFD700; stroke-width:12; stroke-linecap:round; filter: drop-shadow(0 0 8px #FFD700); }}
.circle-text {{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); text-align:center; }}
</style>
<h1 style='color:#FFD700;font-size:18px;margin:5px'>💵 MAQUINA DE HACER DINEROS 💵</h1>
<div class="circle-wrap">
  <svg><circle class="circle-bg" cx="110" cy="110" r="90"></circle>
  <circle class="circle-fill" cx="110" cy="110" r="90" stroke-dasharray="{circ}" stroke-dashoffset="{offset}"></circle></svg>
  <div class="circle-text">
    <div style='font-size:10px;color:#aaa'>BASE</div>
    <div style='font-size:16px;color:#fff'>${CONFIG['BALANCE_INICIAL']:.0f}</div>
    <div style='font-size:11px;color:#aaa;margin-top:6px'>ACUMULADO</div>
    <div style='font-size:32px;color:#00ff66;font-weight:bold;text-shadow:0 0 10px #00ff66'>+${acumulado:.0f}</div>
    <div style='font-size:12px;color:#FFD700;margin-top:4px'>DIA {dia} / {total}</div>
  </div>
</div>
<div style='background:#1a1a1a;padding:10px;border-left:4px solid #00ff66;font-size:12px;text-align:left'>
PERSISTENCIA: {"ON ✅" if os.path.exists(DATA_FILE) else "OFF"} | ANTI-SLEEP: ON ✅ | BALANCE ${CONFIG['BALANCE']:.2f} | NETO ${CONFIG['profit_hoy']:.2f}<br>
PROGRESO {pct_circle:.1f}% | AUTO {'ON' if CONFIG['AUTO'] else 'OFF'} - ROBOT BUSCA FONDO SOLO
</div>
"""
    html += f"<div style='background:#222;padding:10px;margin:10px 0;border:1px solid #00c853;text-align:left'>"
    html += f"<b style='color:#00c853'>🎯 VENTA RETAIL Actual: {CONFIG['RETAIL_PCT']}%</b><br><br>"
    for v in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
        bg = "#00c853" if CONFIG["RETAIL_PCT"] == v else "#333"
        html += f"<a href='/set_retail/{v}' style='margin:2px;padding:8px 12px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{v}%</a>"
    html += "<br><span style='font-size:10px;color:#aaa'>Entrada: Robot detecta fondo -0.4% + rebote</span></div>"

    html += "<div style='background:#111;padding:10px;margin:10px 0;border:1px solid #2962ff;text-align:left'>"
    html += "<b style='color:#2962ff'>🪙 MONEDAS ACTIVAS PARA ROBOT</b><br><br>"
    for c in CONFIG["COINS"]:
        bg = "#00c853" if c in CONFIG["ACTIVOS"] else "#333"
        label = f"{c} ON" if c in CONFIG["ACTIVOS"] else f"{c} OFF"
        html += f"<a href='/toggle/{c}' style='margin:2px;padding:10px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block;font-weight:bold'>{label}</a>"
    html += "</div>"

    html += "<div style='background:#111;padding:8px;margin:10px 0;border:1px solid #FFD700;font-size:11px;text-align:left'>"
    html += "<b>GANANCIA POR MONEDA (NETO)</b><br>"
    for c in CONFIG["COINS"]:
        html += f"{c}: ${CONFIG['profit_por_moneda'][c]:.2f}<br>"
    html += "</div>"

    html += "<div style='background:#151515;padding:8px;margin:10px 0;font-size:11px;text-align:left'>"
    html += "<b>BOLAS ACTIVAS - BRUTO / COMISION / NETO</b><br>"
    if not CONFIG["bolas"]:
        html += "Robot esperando fondo para comprar...<br>"
    for b in CONFIG["bolas"]:
        cur = CONFIG["prices"][b["coin"]]
        gain = (cur - b["entry"]) / b["entry"] * 100
        bruto = b["costo"] * gain / 100
        fees = b["costo"] * CONFIG["FEES_PCT"] / 100 * 2
        neto = bruto - fees
        color = "#0f0" if neto > 0 else "#f44"
        html += f"ID {b['id']} {b['coin']} | E ${b['entry']:.2f} -> ${cur:.2f} ({gain:.2f}%)<br>"
        html += f"BRUTO ${bruto:.2f} - FEES ${fees:.2f} = <b style='color:{color}'>NETO ${neto:.2f}</b> <a href='/vender/{b['id']}' style='color:#FFD700'>[VENDER]</a><br><br>"
    html += "</div>"

    html += "<div style='background:#0a0a0a;padding:8px;font-size:10px;text-align:left'><b>ULTIMOS TRADES</b><br>"
    for log in CONFIG["trades_log"][:20]:
        html += f"{log}<br>"
    html += "</div>"

    html += f"<div style='text-align:center;margin-top:10px'><a href='/toggle_auto' style='padding:10px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#f00'};color:#fff;text-decoration:none;border-radius:8px'>AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</a> <a href='/set_dia/{dia+1}' style='padding:10px 20px;background:#2962ff;color:#fff;text-decoration:none;border-radius:8px;margin-left:5px'>DIA+1</a> <a href='/reset_bolas' style='padding:10px 20px;background:#333;color:#fff;text-decoration:none;border-radius:8px;margin-left:5px'>RESET BOLAS</a></div>"
    html += "</body></html>"
    return html

@app.route("/set_retail/<float:val>")
def set_retail(val):
    CONFIG["RETAIL_PCT"] = val
    save_data()
    return dash()

@app.route("/set_dia/<int:d>")
def set_dia(d):
    CONFIG["DIA_ACTUAL"] = min(d, 30)
    save_data()
    return dash()

@app.route("/toggle/<coin>")
def toggle_coin(coin):
    if coin in CONFIG["ACTIVOS"]:
        if len(CONFIG["ACTIVOS"]) > 1:
            CONFIG["ACTIVOS"].remove(coin)
    else:
        CONFIG["ACTIVOS"].append(coin)
    save_data()
    return dash()

@app.route("/toggle_auto")
def toggle_auto():
    CONFIG["AUTO"] = not CONFIG["AUTO"]
    save_data()
    return dash()

@app.route("/vender/<int:bid>")
def vender(bid):
    for b in CONFIG["bolas"][:]:
        if b["id"] == bid:
            cur = CONFIG["prices"][b["coin"]]
            gain = (cur - b["entry"]) / b["entry"] * 100
            bruto = b["costo"] * gain / 100
            fees = b["costo"] * CONFIG["FEES_PCT"] / 100 * 2
            neto = bruto - fees
            CONFIG["BALANCE"] += neto
            CONFIG["profit_hoy"] += neto
            CONFIG["bolas"].remove(b)
            CONFIG["trades_log"].insert(0, f"VENTA MANUAL ID {bid} NETO ${neto:.2f}")
            if neto > 0:
                send_tg(f"💰 VENTA MANUAL {b['coin']} NETO ${neto:.2f}")
            save_data()
    return dash()

@app.route("/reset_bolas")
def reset_bolas():
    CONFIG["bolas"] = []
    save_data()
    return dash()

@app.route("/" + BOT_TOKEN, methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"ok": True})
    CONFIG["chat_id"] = data["message"]["chat"]["id"]
    save_data()
    text = f"💸 V94 FINAL PERSISTENTE\n{RENDER_URL}\nBASE ${CONFIG['BALANCE_INICIAL']:.0f} ACUM +${CONFIG['BALANCE']-CONFIG['BALANCE_INICIAL']:.0f} DIA {CONFIG['DIA_ACTUAL']}/30\nRETAIL {CONFIG['RETAIL_PCT']}% BAL ${CONFIG['BALANCE']:.2f}\nPERSISTENTE + ANTI-SLEEP ON"
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CONFIG["chat_id"], "text": text}, timeout=5)
    except:
        pass
    return jsonify({"ok": True})

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
