from flask import Flask, jsonify, request
import os, json, requests, threading, time
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "bot/trades.json"
if not os.path.exists("bot"): CHAT_FILE = "trades.json"

app = Flask(__name__, template_folder="bot/templates")

def load():
    try:
        with open(CHAT_FILE,"r") as f: return json.load(f)
    except:
        return {"trades":[],"balance":0,"hoy":0,"ganados":0,"perdidos":0,"chat_id":None,"auto_on":False,"coin":"BTC","ema9":0,"ema21":0,"rsi":0,"signal":"ESPERA","pred":"SUBIDA V270"}

def save(d):
    with open(CHAT_FILE,"w") as f: json.dump(f,f) if False else json.dump(d,f)

def send_msg(cid, txt, keyboard=None):
    if not TOKEN or not cid: return
    data = {"chat_id":cid,"text":txt,"parse_mode":"HTML"}
    if keyboard:
        data["reply_markup"] = json.dumps({"keyboard":keyboard,"resize_keyboard":True})
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=data, timeout=10)
    except: pass

def resumen_text():
    d=load()
    tz=pytz.timezone("America/Mexico_City")
    now=datetime.now(tz).strftime("%d/%m/%Y - %I:%M %p")
    auto = "AUTO ON" if d.get("auto_on") else "AUTO OFF"
    return f"""📊 RESUMEN {now}
_______________
💰 Balance: ${d.get('balance',0):.2f}
📈 Hoy: ${d.get('hoy',0):.2f}
✅ Ganados: {d.get('ganados',0)} | ❌ Perdidos: {d.get('perdidos',0)}
📦 Trades: {len(d.get('trades',[]))}
Bot V270 - {auto}
Coin: {d.get('coin')} | {d.get('signal')}"""

KEYBOARD = [["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]]

@app.route("/")
def home():
    for p in ["bot/templates/index.html","templates/index.html","index.html"]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f: return f.read()
    return "<h1>BOT V506 LIVE</h1>"

@app.route("/api/status")
def status():
    d=load()
    # simula datos live si no hay
    return jsonify({
        "balance": d.get("balance",0),
        "hoy": d.get("hoy",0),
        "ganados": d.get("ganados",0),
        "perdidos": d.get("perdidos",0),
        "trades": len(d.get("trades",[])),
        "auto_on": d.get("auto_on",False),
        "coin": d.get("coin","BTC"),
        "ema9": d.get("ema9",64787.75),
        "ema21": d.get("ema21",64778.58),
        "rsi": d.get("rsi",33.2),
        "signal": d.get("signal","ESPERA"),
        "pred": d.get("pred","SUBIDA V270"),
        "price": d.get("price",64793.32)
    })

@app.route("/api/set", methods=["POST"])
def api_set():
    d=load()
    j=request.get_json()
    if "coin" in j: d["coin"]=j["coin"]
    if "auto_on" in j: d["auto_on"]=j["auto_on"]
    if "signal" in j: d["signal"]=j["signal"]
    save(d)
    if d.get("chat_id"):
        send_msg(d["chat_id"], f"Dashboard cambio: {j}")
    return jsonify({"ok":True})

@app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{})
    cid=msg.get("chat",{}).get("id")
    txt=(msg.get("text","") or "").strip().upper()
    d=load()
    if cid: d["chat_id"]=cid

    if txt in ["BTC","ETH","SOL","XRP"]:
        d["coin"]=txt
        save(d)
        send_msg(cid, f"✅ Moneda cambiada a {txt}\n{resumen_text()}", KEYBOARD)
    elif txt=="AUTO":
        d["auto_on"]= not d.get("auto_on",False)
        save(d)
        send_msg(cid, f"{'🟢 AUTO ON' if d['auto_on'] else '🔴 AUTO OFF'}", KEYBOARD)
    elif txt in ["/BALANCE","/RESUMEN","BALANCE","RESUMEN"]:
        send_msg(cid, resumen_text(), KEYBOARD)
    elif txt in ["/START","START"]:
        send_msg(cid, f"🤖 JOHAN V505 LISTO\n{resumen_text()}", KEYBOARD)
    elif txt in ["COMPRAR","VENDER"]:
        d["signal"]=txt
        d["trades"].append({"coin":d.get("coin"),"side":txt,"time":str(datetime.now())})
        save(d)
        send_msg(cid, f"📥 Orden {txt} {d.get('coin')} registrada", KEYBOARD)
    else:
        if txt.startswith("/"):
            send_msg(cid, resumen_text(), KEYBOARD)
    save(d)
    return "ok"

def loop_10pm():
    tz=pytz.timezone("America/Mexico_City")
    while True:
        try:
            now=datetime.now(tz)
            if now.hour==22 and now.minute==0:
                d=load()
                if d.get("chat_id"): send_msg(d["chat_id"], resumen_text(), KEYBOARD)
                time.sleep(61)
        except: pass
        time.sleep(30)

threading.Thread(target=loop_10pm, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
