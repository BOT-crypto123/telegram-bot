from flask import Flask, jsonify, request
import os, json, requests, threading, time
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "bot/trades.json"
if not os.path.exists("bot"):
    CHAT_FILE = "trades.json"

app = Flask(__name__)

def load():
    try:
        with open(CHAT_FILE,"r") as f:
            return json.load(f)
    except:
        return {"trades":[],"balance":1000.0,"hoy":0.0,"ganados":0,"perdidos":0,"chat_id":None,"auto_on":False,"coin":"BTC","ema9":64787.75,"ema21":64778.58,"rsi":33.2,"signal":"ESPERA","pred":"SUBIDA V270","price":64793.32}

def save(d):
    os.makedirs(os.path.dirname(CHAT_FILE) if "/" in CHAT_FILE else ".", exist_ok=True)
    with open(CHAT_FILE,"w") as f:
        json.dump(d,f, indent=2)

def send_msg(cid, txt):
    if not TOKEN or not cid:
        return
    keyboard = [["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]]
    data = {
        "chat_id": cid,
        "text": txt,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"keyboard":keyboard,"resize_keyboard":True})
    }
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=data, timeout=15)
    except:
        pass

def resumen_text():
    d=load()
    tz=pytz.timezone("America/Mexico_City")
    now=datetime.now(tz).strftime("%d/%m/%Y - %I:%M %p")
    auto = "🟢 AUTO ON" if d.get("auto_on") else "🔴 AUTO OFF"
    return f"""📊 <b>RESUMEN {now}</b>

💰 <b>Balance:</b> ${d.get('balance',0):.2f} (PRÁCTICA)
📈 <b>Hoy:</b> ${d.get('hoy',0):.2f}
✅ <b>Ganados:</b> {d.get('ganados',0)} | ❌ <b>Perdidos:</b> {d.get('perdidos',0)}
📦 <b>Trades:</b> {len(d.get('trades',[]))}
🪙 <b>Coin:</b> {d.get('coin')} | {d.get('signal')}
Bot V507 - {auto}
"""

@app.route("/")
def home():
    for p in ["bot/templates/index.html","templates/index.html"]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
    return "<h1>BOT V507 LIVE - Sube templates/index.html</h1>"

@app.route("/api/status")
def status():
