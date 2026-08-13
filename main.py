import os, json, requests, threading, time
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["XAUUSD","BTC","NVDA","TSLA"]
SALDO_INICIAL = 5000
MONTO = 750
MAX_POS = 6

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10)
        if r.status_code==200:
            d=r.json()
            d.setdefault("b",SALDO_INICIAL); d.setdefault("pos",[]); d.setdefault("alert_users",[]); d.setdefault("auto",True); d.setdefault("gan_hoy",0); d.setdefault("gan_total",0); d.setdefault("trades_hoy",0)
            return d
    except: pass
    return {"b":SALDO_INICIAL,"pos":[],"alert_users":[],"auto":True,"gan_hoy":0,"gan_total":0,"trades_hoy":0}

data=load()
def save():
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass

# --- LOGICA DE PRECIOS REALES ---
def P(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT"}
        if sym in mp:
            r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=3).json()
            return float(r["price"])
        # TSLA y NVDA precio mock si no hay Twelve Key
        return {"NVDA":183.5,"TSLA":248.2}.get(sym,100)
    except: return 0

def C(sym):
    try:
        mp={"BTC":"BTCUSDT","XAUUSD":"PAXGUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={mp.get(sym,'BTCUSDT')}&interval=1h&limit=80",timeout=5).json()
        return [float(x[4]) for x in r]
    except: return []

def RSI(closes):
    if len(closes)<15: return 40
    g=l=0
    for i in range(1,15):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 70
    return 100-(100/(1+g/l))

def totals():
    flot=0
    for p in data["pos"]:
        pr=P(p["sym"])
        if pr>0 and p.get("precio_entry",0)>0:
            p["gan"]=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
            flot+=p["gan"]
    return data["b"]+flot, flot

@app.route("/")
def dash():
    tot,flot=totals()
    col="#00ff88" if flot>=0 else "#ff4444"
    pos_html=""
    for p in data["pos"]:
        pos_html+=f"<div style='display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid #222'><b>{p['sym']}</b><span style='color:{col}'>{p.get('gan',0):+.2f}$</span></div>"
    return f"""<meta name=viewport content="width=device-width,initial-scale=1"><style>body{{background:#080808;color:#fff;font-family:Arial;padding:12px}}.card{{background:#111;border-radius:16px;padding:16px;margin-bottom:10px;border:1px solid #222}}.gold{{color:#ffcc00;font-weight:bold}}.big{{font-size:34px;font-weight:900}}</style>
    <div class=card><div class=gold>V34 CONCENTRADO 5K</div><div class=big>${tot:.2f}</div>Saldo ${data['b']:.2f} <span style='color:{col}'>Flot {flot:+.2f}$</span> Pos {len(data['pos'])}/{MAX_POS} Auto {'ON' if data.get('auto') else 'OFF'}</div>
    <div class=card>{pos_html or 'Sin posiciones - esperando RSI<32'}</div>"""

# FIX WEBHOOK - SOPORTA LAS 2 RUTAS PARA QUE NO TE DEJE EN VISTO
@app.route(f"/{TOKEN}", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode("utf-8"))])
    return "ok"

# --- BOT CON TODA LA LOGICA DE TUS BOTONES ---
@bot.message_handler(func=lambda m: True)
def handler(m):
    if not m.text: return
    txt=m.text.upper().strip()
    uid=m.chat.id
    if uid not in data["alert_users"]:
        data["alert_users"].append(uid); save()

    if any(k in txt for k in ["DASHBOARD","BALANCE","/SALDO","/START","HOLA"]):
        tot,flot=totals()
        bot.send_message(uid,f"V34 CONCENTRADO\nhttps://telegram-bot-cijp.onrender.com\n\nTotal: ${tot:.2f}\nSaldo: ${data['b']:.2f}\nFlot: {flot:+.2f}$\nPos: {len(data['pos'])}/{MAX_POS}\nAuto: {'ON' if data.get('auto') else 'OFF'}\nHoy: {data.get('gan_hoy',0):+.2f}$")

    elif txt in ALL_COINS:
        # LOGICA COMPRA MANUAL
        if any(p["sym"]==txt for p in data["pos"]):
            bot.send_message(uid,f"⚠️ Ya tienes {txt}")
        elif len(data["pos"])>=MAX_POS:
            bot.send_message(uid,f"❌ Lleno {MAX_POS}/{MAX_POS}")
        elif data["b"]<MONTO:
            bot.send_message(uid,f"❌ Saldo insuficiente ${data['b']:.2f}")
        else:
            pr=P(txt)
            data["pos"].append({"sym":txt,"monto":MONTO,"precio_entry":pr,"gan":0})
            data["b"]-=MONTO; data["trades_hoy"]+=1; save()
            bot.send_message(uid,f"✅ COMPRA V34 {txt} ${MONTO} a ${pr:.2f}")

    elif "AUTO ON" in txt:
        data["auto"]=True; save(); bot.send_message(uid,"🤖 AUTO ON ✅")
    elif "AUTO OFF" in txt:
        data["auto"]=False; save(); bot.send_message(uid,"🛑 AUTO OFF")

    elif txt.startswith("SELL") or "VENDER" in txt:
        sym=txt.replace("SELL","").strip()
        for p in data["pos"][:]:
            if p["sym"]==sym:
                pr=P(sym); gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                data["b"]+=p["monto"]+gan; data["gan_total"]+=gan; data["pos"].remove(p); save()
                bot.send_message(uid,f"💰 VENDIDO {sym} {gan:+.2f}$")

# --- AUTO LOOP RSI LOGICA ORIGINAL ---
def auto_loop():
    while True:
        try:
            if data.get("auto",True):
                for sym in ALL_COINS:
                    closes=C(sym)
                    rsi=RSI(closes); pr=P(sym)
                    if rsi<32 and len(data["pos"])<MAX_POS and not any(p["sym"]==sym for p in data["pos"]) and data["b"]>=MONTO:
                        data["pos"].append({"sym":sym,"monto":MONTO,"precio_entry":pr,"gan":0})
                        data["b"]-=MONTO; data["trades_hoy"]+=1; save()
                        for u in data["alert_users"]:
                            try: bot.send_message(u,f"🤖 AUTO V34 {sym} RSI {rsi:.1f} ${pr:.2f}")
                            except: pass
            time.sleep(90)
        except: time.sleep(30)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
