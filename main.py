import os, json, time, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify
import telebot
from PIL import Image, ImageDraw, ImageFont

# --- CONFIG ---
NPOINT_ID = os.getenv("NPOINT_ID", "455c95667066c8b158d0")
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "123456:TEST"
TWELVE_KEY = os.getenv("TWELVE_KEY", "")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

ALL_COINS = ["XAUUSD","BTC","NVDA","TSLA"]
SALDO_INICIAL = 5000

# --- PERSISTENCIA GRATIS NPOINT ---
def load_data():
    if NPOINT_ID:
        try:
            r = requests.get(f"https://api.npoint.io/{NPOINT_ID}", timeout=15)
            if r.status_code == 200:
                d = r.json()
                d.setdefault("coins", ALL_COINS)
                d.setdefault("b", SALDO_INICIAL)
                d.setdefault("pos", [])
                d.setdefault("gan_total", 0)
                d.setdefault("gan_hoy", 0)
                d.setdefault("trades_hoy", 0)
                d.setdefault("alert_users", [])
                d.setdefault("last_report_date", "")
                return d
        except: pass
    try:
        with open("data.json","r") as f: return json.load(f)
    except:
        return {"b":SALDO_INICIAL,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"alert_users":[],"last_report_date":""}

def save_data():
    try:
        with open("data.json","w") as f: json.dump(data,f)
    except: pass
    if NPOINT_ID:
        try: requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=data, timeout=15)
        except: pass

data = load_data()
def save(): save_data()

def P(sym):
    try:
        if sym == "XAUUSD":
            r=requests.get("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT",timeout=5).json()
            return float(r["price"])
        if sym == "BTC":
            r=requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",timeout=5).json()
            return float(r["price"])
        if TWELVE_KEY:
            r=requests.get(f"https://api.twelvedata.com/price?symbol={sym}&apikey={TWELVE_KEY}",timeout=8).json()
            return float(r["price"])
        return 150.0
    except: return 0

def totals():
    flot=0
    for p in data["pos"]:
        pr=P(p["sym"])
        if pr>0:
            if p["sym"]=="XAUUSD": flot+= (pr-p["precio_entry"])*(p["monto"]/p["precio_entry"])*0.9
            else: flot+= (pr-p["precio_entry"])/p["precio_entry"]*p["monto"]
            p["precio_now"]=pr
    return data["b"]+flot, flot

# --- DASHBOARD ESTETICA ---
@app.route("/")
def home():
    tot,flot=totals()
    pnl_c="#00ff88" if flot>=0 else "#ff4444"
    pos_html="".join([f"<div style='display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #222'><b>{p['sym']}</b><span>${p['monto']}</span><span style='color:{pnl_c}'>{p.get('gan',0):+.2f}$</span></div>" for p in data["pos"]]) or "<div style='opacity:.5;padding:20px 0;text-align:center'>Esperando apertura NY 9:30 AM...</div>"
    return f"<head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{{background:#070709;color:#fff;font-family:sans-serif;margin:0;padding:16px}} .card{{background:#111113;border:1px solid #232326;border-radius:20px;padding:20px;margin-bottom:14px}} .gold{{color:#ffcc00;letter-spacing:2px;font-weight:800;font-size:12px}} .big{{font-size:36px;font-weight:900;margin:8px 0}} .muted{{opacity:.6;font-size:13px}}</style></head><body><div class='card'><div class='gold'>V34 • 5K CONCENTRADO</div><div class='big'>${tot:.2f}</div><div class='muted'>Saldo ${data['b']:.2f} • Flot <span style='color:{pnl_c}'>{flot:+.2f}$</span> • Hoy {data.get('gan_hoy',0):+.2f}$</div></div><div class='card'><div class='gold'>POS {len(data['pos'])}/6</div>{pos_html}</div><div class='card muted'>NPOINT: {NPOINT_ID}</div></body>"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try: bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    except: pass
    return "ok"

@app.route("/api/data")
def api_data():
    tot,flot=totals()
    return jsonify({"total":tot,"flot":flot,"data":data})

@bot.message_handler(commands=['start','saldo'])
def start(m):
    if m.chat.id not in data["alert_users"]:
        data["alert_users"].append(m.chat.id); save()
    tot,flot=totals()
    bot.send_message(m.chat.id,f"V34 5K Activo ✅\nTotal: ${tot:.2f}\nSaldo: ${data['b']:.2f}\nPos: {len(data['pos'])}/6")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
