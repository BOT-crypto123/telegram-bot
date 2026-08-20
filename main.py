import os, time, requests, threading
from flask import Flask, jsonify, request
from collections import deque
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "VERSION": "V79 SOL/DOGE NIEVE",
    "COINS": ["BTC", "ETH", "SOL", "DOGE"],
    "SELECTED": "SOL",
    "MAX": 3,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.4,
    "BALANCE": 10000.0,
    "BALANCE_INICIAL": 10000.0,
    "FEES": 0.1,
    "AUTO": True,
    "NIEVE": True,
    "bolas": [],
    "prices": {"SOL": 1483, "DOGE": 1.30, "BTC": 1216631, "ETH": 65000},
    "high": {},
    "history": {"SOL": deque(maxlen=60), "DOGE": deque(maxlen=60), "BTC": deque(maxlen=60), "ETH": deque(maxlen=60)},
    "trades_hoy": 0,
    "profit_hoy": 0.0
}

def get_all_prices():
    for coin in CONFIG["COINS"]:
        try:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-MXN/spot", timeout=4).json()
            CONFIG["prices"][coin] = float(r["data"]["amount"])
            CONFIG["history"][coin].append(CONFIG["prices"][coin])
        except: pass

def send_tg(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=5)
    except: pass

def check_auto():
    while True:
        try:
            get_all_prices()
            for coin in ["SOL", "DOGE"]:
                hist = list(CONFIG["history"][coin])
                if len(hist) < 5: continue
                price = CONFIG["prices"][coin]
                max_15 = max(hist[-15:]) if len(hist)>=15 else max(hist)
                dip = (price - max_15) / max_15 * 100
                # COMPRA RAPIDA -0.1% para que veas trades hoy
                if CONFIG["AUTO"] and dip <= -0.1 and len(CONFIG["bolas"]) < CONFIG["MAX"]:
                    costo = CONFIG["BALANCE"] / CONFIG["MAX"]
                    nid = len(CONFIG["bolas"])+1
                    CONFIG["bolas"].append({"id": nid, "coin": coin, "entry": price, "costo": costo})
                    CONFIG["high"][nid] = price
                for b in CONFIG["bolas"][:]:
                    if b["coin"]!= coin: continue
                    if b["id"] not in CONFIG["high"]: CONFIG["high"][b["id"]] = b["entry"]
                    if price > CONFIG["high"][b["id"]]: CONFIG["high"][b["id"]] = price
                    high = CONFIG["high"][b["id"]]
                    gain = (price - b["entry"])/b["entry"]*100
                    trail = (price - high)/high*100
                    if gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]:
                        bruto = b["costo"]*gain/100
                        fees = b["costo"]*CONFIG["FEES"]/100*2
                        neto = bruto - fees
                        CONFIG["BALANCE"] += neto
                        CONFIG["profit_hoy"] += neto
                        CONFIG["trades_hoy"] += 1
                        CONFIG["bolas"].remove(b)
            time.sleep(30)
        except: time.sleep(30)

threading.Thread(target=check_auto, daemon=True).start()

def get_dash_text():
    get_all_prices()
    tb=0
    for b in CONFIG["bolas"]:
        price = CONFIG["prices"][b["coin"]]
        tb += b["costo"]*(price-b["entry"])/b["entry"]/100
    txt = f"DASH {RENDER_URL}\n"
    txt += f"V79 {CONFIG['SELECTED']} NIEVE {CONFIG['BALANCE']:.2f} MXN\n"
    txt += f"{len(CONFIG['bolas'])}/{CONFIG['MAX']} | RETAIL {CONFIG['RETAIL_PCT']}% TRAIL {CONFIG['TRAIL_PCT']}%\n"
    txt += f"SOL ${CONFIG['prices']['SOL']:.2f} MXN\n"
    txt += f"DOGE ${CONFIG['prices']['DOGE']:.2f} MXN\n"
    txt += f"BTC ${CONFIG['prices']['BTC']:.0f} MXN\n"
    txt += f"BALANCE {CONFIG['BALANCE']:.2f} (ini {CONFIG['BALANCE_INICIAL']})\n"
    txt += f"HOY {CONFIG['trades_hoy']} trades +${CONFIG['profit_hoy']:.2f}\n"
    txt += f"FLOAT ${tb:.2f} | BOLA ${CONFIG['BALANCE']/CONFIG['MAX']:.2f} NIEVE ON"
    return txt

@app.route("/")
def dash():
    get_all_prices()
    costo = CONFIG["BALANCE"]/CONFIG["MAX"]
    tb=0
    for b in CONFIG["bolas"]:
        tb += b["costo"]*(CONFIG["prices"][b["coin"]]-b["entry"])/b["entry"]/100
    html = f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='10'></head><body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:12px'>"
    html += f"<h3 style='color:#0f0'>{CONFIG['VERSION']} | ${CONFIG['BALANCE']:.2f}</h3>"
    html += f"<div style='background:#1a1a1a;padding:12px;border-left:4px solid #0f0'>"
    html += f"SOL ${CONFIG['prices']['SOL']:.2f} | DOGE ${CONFIG['prices']['DOGE']:.2f}<br>"
    html += f"BOLAS {len(CONFIG['bolas'])}/{CONFIG['MAX']} | BOLA ${costo:.2f}<br>HOY {CONFIG['trades_hoy']} +${CONFIG['profit_hoy']:.2f} | FLOAT ${tb:.2f} | NIEVE ON</div>"
    html += f"<div style='background:#111;padding:10px;margin:8px 0'>"
    for c in CONFIG["COINS"]:
        bg = "#00c853" if c==CONFIG["SELECTED"] else "#333"
        html += f"<a href='/sel/{c}' style='margin:3px;padding:8px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px'>{c}</a>"
    html += "</div>"
    html += f"<div style='text-align:center'><a href='/toggle_auto' style='padding:10px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#f00'};color:#fff;text-decoration:none;border-radius:8px'>AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</a></div>"
    html += "</body></html>"
    return html

@app.route("/sel/<coin>")
def sel(coin):
    CONFIG["SELECTED"]=coin
    return dash()
@app.route("/toggle_auto")
def toggle():
    CONFIG["AUTO"]=not CONFIG["AUTO"]
    return dash()
@app.route("/"+BOT_TOKEN, methods=["POST"])
def webhook():
    data=request.get_json()
    if not data or "message" not in data: return jsonify({"ok":True})
    chat_id=data["message"]["chat"]["id"]
    send_tg(chat_id, get_dash_text())
    return jsonify({"ok":True})
@app.route("/estado")
def estado(): return jsonify(CONFIG)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
