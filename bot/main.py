from flask import Flask, jsonify, request
import os, json, requests, threading, time
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "trades.json"
app = Flask(__name__)

def load():
    try:
        with open(CHAT_FILE,"r") as f:
            return json.load(f)
    except:
        return {
            "trades": [], "balance": 1000.0, "hoy": 0.0,
            "ganados": 0, "perdidos": 0, "chat_id": None,
            "auto_on": False, "coin": "BTC",
            "ema9": 0, "ema21": 0, "rsi": 0,
            "signal": "ESPERA", "pred": "V270"
        }

def save(d):
    with open(CHAT_FILE,"w") as f:
        json.dump(d, f)

def send_msg(cid, txt):
    if not TOKEN or not cid:
        return
    kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
    data = {"chat_id":cid,"text":txt,"parse_mode":"HTML","reply_markup":json.dumps(kb)}
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=data, timeout=10)
    except:
        pass

def resumen_text():
    d = load()
    tz = pytz.timezone("America/Mexico_City")
    now = datetime.now(tz).strftime("%d/%m/%Y - %I:%M %p")
    auto = "AUTO ON" if d.get("auto_on") else "AUTO OFF"
    return f"RESUMEN {now}\nBalance: ${d.get('balance',0):.2f} (PRACTICA)\nHoy: ${d.get('hoy',0):.2f}\nCoin: {d.get('coin')} | {d.get('signal')}\n{auto}"

@app.route("/")
def home():
    if os.path.exists("bot/templates/index.html"):
        with open("bot/templates/index.html", encoding="utf-8") as f:
            return f.read()
    if os.path.exists("templates/index.html"):
        with open("templates/index.html", encoding="utf-8") as f:
            return f.read()
    return "<h1>BOT V507 LIVE</h1>"

@app.route("/api/status")
def api_status():
    d = load()
    return jsonify({
        "balance": d.get("balance",1000),
        "hoy": d.get("hoy",0),
        "ganados": d.get("ganados",0),
        "perdidos": d.get("perdidos",0),
        "trades": len(d.get("trades",[])),
        "auto_on": d.get("auto_on",False),
        "coin": d.get("coin","BTC"),
        "ema9": d.get("ema9",0),
        "ema21": d.get("ema21",0),
        "rsi": d.get("rsi",0),
        "signal": d.get("signal","ESPERA"),
        "pred": d.get("pred","V270"),
        "price": d.get("price",0)
    })

@app.route("/api/set", methods=["POST"])
def api_set():
    d = load()
    j = request.get_json() or {}
    if "coin" in j:
        d["coin"] = j["coin"]
    if "auto_on" in j:
        d["auto_on"] = j["auto_on"]
    if "signal" in j:
        d["signal"] = j["signal"]
        d["trades"].append({"coin":d.get("coin"),"side":j["signal"],"time":str(datetime.now())})
    save(d)
    return jsonify({"ok":True})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    msg = data.get("message",{})
    cid = msg.get("chat",{}).get("id")
    txt = (msg.get("text","") or "").strip().upper()
    d = load()
    if cid:
        d["chat_id"] = cid
    if txt in ["BTC","ETH","SOL","XRP"]:
        d["coin"] = txt
        save(d)
        send_msg(cid, f"Moneda cambiada a {txt}\n{resumen_text()}")
    elif txt == "AUTO":
        d["auto_on"] = not d.get("auto_on",False)
        save(d)
        send_msg(cid, f"{
