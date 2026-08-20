import os, time, requests, threading
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "VERSION": "V83 MAQUINA DINEROS",
    "COINS": ["BTC", "ETH", "SOL", "DOGE"],
    "ACTIVOS": ["SOL", "ETH", "DOGE"],
    "MAX": 3,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.4,
    "BALANCE": 10138.30,
    "BALANCE_INICIAL": 10000.0,
    "FEES_PCT": 0.1,
    "AUTO": True,
    "bolas": [],
    "prices": {"SOL": 1484.31, "DOGE": 1.39, "BTC": 1232606.83, "ETH": 39814.75},
    "high": {},
    "history": {"SOL": [], "DOGE": [], "BTC": [], "ETH": []},
    "trades_hoy": 8,
    "profit_hoy": 138.30,
    "profit_bruto": 158.20,
    "profit_fees": 19.90,
    "profit_por_moneda": {"BTC":0, "ETH":0, "SOL":0, "DOGE":0},
    "trades_log": [],
    "chat_id": 0
}

def get_all_prices():
    for coin in CONFIG["COINS"]:
        try:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-MXN/spot", timeout=4).json()
            CONFIG["prices"][coin] = float(r["data"]["amount"])
            CONFIG["history"][coin].append(CONFIG["prices"][coin])
            if len(CONFIG["history"][coin])>60: CONFIG["history"][coin].pop(0)
        except: pass

def send_tg(text):
    try:
        if CONFIG["chat_id"]==0: return
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CONFIG["chat_id"], "text": text}, timeout=5)
    except: pass

def check_auto():
    while True:
        try:
            get_all_prices()
            for coin in CONFIG["ACTIVOS"]:
                hist = CONFIG["history"][coin]
                if len(hist) < 5: continue
                price = CONFIG["prices"][coin]
                max_15 = max(hist[-15:]) if len(hist)>=15 else max(hist)
                dip = (price - max_15) / max_15 * 100
                if CONFIG["AUTO"] and dip <= -0.1 and len(CONFIG["bolas"]) < CONFIG["MAX"]:
                    costo = CONFIG["BALANCE"] / CONFIG["MAX"]
                    nid = int(time.time())%10000
                    CONFIG["bolas"].append({"id": nid, "coin": coin, "entry": price, "costo": costo, "time": time.strftime("%H:%M")})
                    CONFIG["high"][str(nid)] = price
                    CONFIG["trades_log"].insert(0, f"{time.strftime('%H:%M')} COMPRO {coin} ${price:.2f} - NO NOTIF (solo DASH)")
                for b in CONFIG["bolas"][:]:
                    if b["coin"]!= coin: continue
                    key=str(b["id"])
                    if key not in CONFIG["high"]: CONFIG["high"][key] = b["entry"]
                    if price > CONFIG["high"][key]: CONFIG["high"][key] = price
                    high = CONFIG["high"][key]
                    gain = (price - b["entry"])/b["entry"]*100
                    trail = (price - high)/high*100
                    if gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]:
                        bruto = b["costo"]*gain/100
                        fees = b["costo"]*CONFIG["FEES_PCT"]/100*2
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
                            send_tg(f"💰 VENDI {b['coin']} CON GANANCIA\nE ${b['entry']:.2f} -> ${price:.2f} ({gain:.2f}%)\nBRUTO ${bruto:.2f} - FEES ${fees:.2f} = NETO ${neto:.2f}\nBALANCE ${CONFIG['BALANCE']:.2f}\n{RENDER_URL}")
                        CONFIG["bolas"].remove(b)
            time.sleep(30)
        except: time.sleep(30)

threading.Thread(target=check_auto, daemon=True).start()

@app.route("/")
def dash():
    get_all_prices()
    costo = CONFIG["BALANCE"]/CONFIG["MAX"]
    html = f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='10'></head><body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px'>"
    html += f"<h1 style='text-align:center;color:#FFD700;font-size:26px;text-shadow:0 0 12px #FFD700;margin:10px 0'>💵💸 MAQUINA DE HACER DINEROS 💰💵<br>💸💲💲💲💲💲💲💸</h1>"
    html += f"<h3 style='color:#0f0;text-align:center'>{CONFIG['VERSION']} | ${CONFIG['BALANCE']:.2f}</h3>"
    html += f"<div style='background:#1a1a1a;padding:10px;border-left:4px solid #FFD700;font-size:12px'>"
    for c in CONFIG["COINS"]:
        html += f"{c} ${CONFIG['prices'][c]:.2f}<br>"
    html += f"3/3 | RETAIL {CONFIG['RETAIL_PCT']}% TRAIL {CONFIG['TRAIL_PCT']}%<br>"
    html += f"BALANCE ${CONFIG['BALANCE']:.2f} (ini ${CONFIG['BALANCE_INICIAL']:.2f})<br>"
    html += f"HOY {CONFIG['trades_hoy']} trades | BRUTO ${CONFIG['profit_bruto']:.2f} - FEES ${CONFIG['profit_fees']:.2f} = <b style='color:#0f0'>NETO ${CONFIG['profit_hoy']:.2f}</b><br>"
    html += f"FLOAT CALC | BOLA ${costo:.2f} | NIEVE ON | AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</div>"
    html += "<div style='background:#111;padding:8px;margin:10px 0;border:1px solid #FFD700;font-size:11px'>"
    html += "<b>GANANCIA POR MONEDA (NETO)</b><br>"
    for c in CONFIG["COINS"]:
        html += f"{c}: ${CONFIG['profit_por_moneda'][c]:.2f}<br>"
    html += "</div>"
    html += "<div style='background:#151515;padding:8px;margin:10px 0;font-size:11px'>"
    html += "<b>BOLAS ACTIVAS - BRUTO / COMISION / NETO</b><br>"
    if not CONFIG["bolas"]:
        html += "Sin bolas - esperando caida -0.1%<br>"
    for b in CONFIG["bolas"]:
        cur = CONFIG["prices"][b["coin"]]
        gain = (cur-b["entry"])/b["entry"]*100
        bruto = b["costo"]*gain/100
        fees = b["costo"]*CONFIG["FEES_PCT"]/100*2
        neto = bruto - fees
        color = "#0f0" if neto>0 else "#f44"
        html += f"ID {b['id']} {b['coin']} | E ${b['entry']:.2f} -> ${cur:.2f} ({gain:.2f}%)<br>"
        html += f"BRUTO ${bruto:.2f} - FEES ${fees:.2f} = <b style='color:{color}'>NETO ${neto:.2f}</b> | {b['time']}<br><br>"
    html += "</div>"
    html += "<div style='background:#0a0a0a;padding:8px;font-size:10px'><b>ULTIMOS TRADES</b><br>"
    for log in CONFIG["trades_log"][:15]:
        html += f"{log}<br>"
    html += "</div>"
    html += f"<div style='background:#111;padding:10px;margin:8px 0'>"
    for c in CONFIG["COINS"]:
        bg = "#00c853" if c in CONFIG["ACTIVOS"] else "#333"
        label = f"{c} ON" if c in CONFIG["ACTIVOS"] else f"{c} OFF"
        html += f"<a href='/toggle/{c}' style='margin:2px;padding:8px 12px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block;font-size:11px'>{label}</a>"
    html += "</div>"
    html += f"<div style='text-align:center'><a href='/toggle_auto' style='padding:10px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#f00'};color:#fff;text-decoration:none;border-radius:8px'>AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</a></div>"
    html += "</body></html>"
    return html

@app.route("/toggle/<coin>")
def toggle_coin(coin):
    if coin in CONFIG["ACTIVOS"]:
        if len(CONFIG["ACTIVOS"])>1: CONFIG["ACTIVOS"].remove(coin)
    else: CONFIG["ACTIVOS"].append(coin)
    return dash()

@app.route("/toggle_auto")
def toggle_auto():
    CONFIG["AUTO"]=not CONFIG["AUTO"]
    return dash()

@app.route("/"+BOT_TOKEN, methods=["POST"])
def webhook():
    data=request.get_json()
    if not data or "message" not in data: return jsonify({"ok":True})
    CONFIG["chat_id"]=data["message"]["chat"]["id"]
    text = f"💸 MAQUINA DE HACER DINEROS ACTIVADA\nDASH {RENDER_URL}\nV83 ${CONFIG['BALANCE']:.2f} NETO ${CONFIG['profit_hoy']:.2f} BRUTO ${CONFIG['profit_bruto']:.2f} FEES ${CONFIG['profit_fees']:.2f}"
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CONFIG["chat_id"], "text": text}, timeout=5)
    except: pass
    return jsonify({"ok":True})

@app.route("/estado")
def estado(): return jsonify({"balance": CONFIG["BALANCE"], "profit": CONFIG["profit_hoy"]})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
