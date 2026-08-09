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
        return {"trades":[],"balance":1000.0,"hoy":0.0,"ganados":0,"perdidos":0,"chat_id":None,"auto_on":False,"coin":"BTC","signal":"ESPERA"}

def save(d):
    with open(CHAT_FILE,"w") as f:
        json.dump(d,f)

def send_msg(cid, txt):
    if not TOKEN or not cid:
        return
    kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
    payload = {"chat_id":cid,"text":txt,"reply_markup":json.dumps(kb)}
    try:
        requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage", json=payload, timeout=10)
    except:
        pass

def resumen_text():
    d = load()
    tz = pytz.timezone("America/Mexico_City")
    now = datetime.now(tz).strftime("%d/%m %H:%M")
    auto = "AUTO ON" if d.get("auto_on") else "AUTO OFF"
    bal = d.get("balance",0)
    coin = d.get("coin","BTC")
    sig = d.get("signal","ESPERA")
    trades = len(d.get("trades",[]))
    return "RESUMEN " + now + "\nBalance: $" + str(bal) + " PRACTICA\nCoin: " + coin + " | " + sig + "\nTrades: " + str(trades) + "\n" + auto

@app.route("/")
def home():
    if os.path.exists("bot/templates/index.html"):
        with open("bot/templates/index.html", encoding="utf-8") as f:
            return f.read()
    if os.path.exists("templates/index.html"):
        with open("templates/index.html", encoding="utf-8") as f:
            return f.read()
    return "<h1>BOT V508 LIVE</h1>"

@app.route("/api/status")
def api_status():
    d = load()
    return jsonify(d)

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
        send_msg(cid, "Moneda cambiada a " + txt + "\n" + resumen_text())
    elif txt == "AUTO":
        d["auto_on"]
