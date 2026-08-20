import os, time, requests, threading
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "VERSION": "V81.1 FIX",
    "COINS": ["BTC", "ETH", "SOL", "DOGE"],
    "ACTIVOS": ["SOL", "ETH", "DOGE"],
    "MAX": 3,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.4,
    "BALANCE": 10099.21,
    "BALANCE_INICIAL": 10000.0,
    "FEES": 0.1,
    "AUTO": True,
    "bolas": [],
    "prices": {"SOL": 1483, "DOGE": 1.30, "BTC": 1216631, "ETH": 65000},
    "high": {},
    "history": {"SOL": [], "DOGE": [], "BTC": [], "ETH": []},
    "trades_hoy": 6,
    "profit_hoy": 99.21,
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
                    send_tg(f"COMPRE {coin} ${price:.2f} | BOLA ${costo:.2f}\nDASH {RENDER_URL}")
                    CONFIG["trades_log"].insert(0, f"{time.strftime('%H:%M')} COMPRO {coin} ${price:.2f}")
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
                        fees = b["costo"]*CONFIG["FEES"]/100*2
                        neto = bruto - fees
                        CONFIG["BALANCE"] += neto
                        CONFIG["profit_hoy"] += neto
                        CONFIG["profit_por_moneda"][b["coin"]] += neto
                        CONFIG["trades_hoy"] += 1
                        send_tg(f"VENDI {b['coin']} ${price:.2f} Entrada ${b['entry']:.2f} +${neto:.2f} NETO ({gain:.2f}%)\nBALANCE ${CONFIG['BALANCE']:.2f}")
                        CONFIG["trades_log"].insert(0, f"{time.strftime('%H:%M')} VENDIO {b['coin']} +${neto:.2f} ({gain:.2f}%)")
                        CONFIG["bolas"].remove(b)
            time.sleep(30)
        except Exception as e:
            print(e)
            time.sleep(30)

threading.Thread(target=check_auto, daemon=True).start()

@app.route("/")
def dash():
    get_all_prices()
    costo = CONFIG["BALANCE"]/CONFIG["MAX"]
    tb=0
    for b in CONFIG["bolas"]:
        tb += b["costo"]*(CONFIG["prices"][b["coin"]]-b["entry"])/b["entry"]/100
    html = f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='10'></head><body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:12px'>"
    html += f"<h3 style='color:#0f0'>{CONFIG['VERSION']} | ${CONFIG['BALANCE']:.2f} | +${CONFIG['profit_hoy']:.2f} HOY</h3>"
    html += f"<div style='background:#1a1a1a;padding:12px;border-left:4px solid #0f0'>"
    for c in CONFIG["COINS"]:
        html += f"{c} ${CONFIG['prices'][c]:.2f} | "
    html += f"<br>BOLAS {len(CONFIG['bolas'])}/{CONFIG['MAX']} | BOLA ${costo:.2f}<br>HOY {CONFIG['trades_hoy']} +${CONFIG['profit_hoy']:.2f} NETO | FLOAT ${tb:.2f}</div>"
    html += "<div style='background:#111;padding:10px;margin:10px 0;border:1px solid #0f0'><b>GANANCIA POR MONEDA</b><br>"
    for c in CONFIG["COINS"]:
        html += f"{c}: +${CONFIG['profit_por_moneda'][c]:.2f}<br>"
    html += "</div>"
    html += "<div style='background:#151515;padding:10px;margin:10px 0'><b>BOLAS ACTIVAS (ENTRADAS)</b><br>"
    if not CONFIG["bolas"]:
        html += "Sin bolas - esperando caida -0.1%<br>"
    for b in CONFIG["bolas"]:
        cur = CONFIG["prices"][b["coin"]]
        gain = (cur-b["entry"])/b["entry"]*100
        usd = b["costo"]*gain/100
        html += f"BOLA {b['id']} | {b['coin']} Entrada ${b['entry']:.2f} -> Ahora ${cur:.2f} | {gain:.2f}% (${usd:.2f}) | {b['time']}<br>"
    html += "</div>"
    html += "<div style='background:#0a0a0a;padding:10px;font-size:12px'><b>ULTIMOS TRADES</b><br>"
    for log in CONFIG["trades_log"][:15]:
        html += f"{log}<br>"
    html += "</div>"
    html += f"<div style='background:#111;padding:10px;margin:8px 0'>"
    for c in CONFIG["COINS"]:
        bg = "#00c853" if c in CONFIG["ACTIVOS"] else "#333"
        label = f"{c} ON" if c in CONFIG["ACTIVOS"] else f"{c} OFF"
        html += f"<a href='/toggle/{c}' style='margin:3px;padding:8px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{label}</a>"
    html += "</div>"
    html += f"<div style='text-align:center;margin-top:10px'><a href='/toggle_auto' style='padding:10px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#f00'};color:#fff;text-decoration:none;border-radius:8px'>AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</a></div>"
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
    text = f"DASH {RENDER_URL}\nV81 FIX {CONFIG['BALANCE']:.2f} +{CONFIG['profit_hoy']:.2f} HOY\n"
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CONFIG["chat_id"], "text": text}, timeout=5)
    except: pass
    return jsonify({"ok":True})

@app.route("/estado")
def estado():
    return jsonify({"balance": CONFIG["BALANCE"], "profit": CONFIG["profit_hoy"], "bolas": CONFIG["bolas"]})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
