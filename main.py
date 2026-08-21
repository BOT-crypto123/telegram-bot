import os, time, requests, threading, json
from datetime import datetime, date
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
RENDER_URL = "https://telegram-bot-cijp.onrender.com"
DATA_FILE = "data.json"

DEFAULT = {
    "VERSION": "V98.3 BOTON TELEGRAM SIN DISCORD",
    "COINS": ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "ACTIVOS": ["ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "MAX": 4, "TRAIL_PCT": 0.2, "RETAIL_PCT": 0.1, "STOP_LOSS_PCT": -7.0,
    "BALANCE": 10310.00, "BALANCE_INICIAL": 10000.0,
    "FECHA_INICIO": str(date.today()), "DIAS_TOTAL": 30, "FEES_PCT": 0.1,
    "AUTO": True, "COMPOUND": True,
    "bolas": [], "prices": {}, "high": {}, "history": {},
    "profit_hoy": 310.00, "profit_por_moneda": {}, "stats_entradas": {}, "stats_exitosas": {},
    "trades_log": [], "chat_id": 0
}
for c in DEFAULT["COINS"]:
    DEFAULT["prices"][c]=1.0; DEFAULT["history"][c]=[]; DEFAULT["profit_por_moneda"][c]=0; DEFAULT["stats_entradas"][c]=0; DEFAULT["stats_exitosas"][c]=0

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r") as f:
                d=json.load(f)
                for k,v in DEFAULT.items():
                    if k not in d: d[k]=v
                return d
        except: pass
    return DEFAULT.copy()

def save_data():
    try:
        with open(DATA_FILE,"w") as f: json.dump(CONFIG,f)
    except: pass

CONFIG = load_data()

def get_dia_actual():
    try: return min(max((date.today()-datetime.strptime(CONFIG["FECHA_INICIO"], "%Y-%m-%d").date()).days+1,1),30)
    except: return 1

def get_all_prices():
    for coin in CONFIG["COINS"]:
        try:
            r=requests.get(f"https://api.coinbase.com/v2/prices/{coin}-MXN/spot",timeout=4).json()
            CONFIG["prices"][coin]=float(r["data"]["amount"])
            CONFIG["history"][coin].append(CONFIG["prices"][coin])
            if len(CONFIG["history"][coin])>60: CONFIG["history"][coin].pop(0)
        except: pass

def send_tg_dashboard():
    try:
        if CONFIG["chat_id"]==0: return
        costo = CONFIG["BALANCE"]/CONFIG["MAX"]
        text = f"💵 V98.3 DIA {get_dia_actual()}/30\nBAL ${CONFIG['BALANCE']:.2f} ACUM +${CONFIG['BALANCE']-CONFIG['BALANCE_INICIAL']:.0f}\nCOSTO/BOLA ${costo:.0f} MAX {CONFIG['MAX']} RETAIL {CONFIG['RETAIL_PCT']}% STOP {CONFIG['STOP_LOSS_PCT']}%\n\n👇 ABRE TU MAQUINA:"
        kb = {
            "inline_keyboard": [
                [{"text": "🚀 ABRIR DASHBOARD", "url": RENDER_URL}],
                [{"text": "📊 Balance", "callback_data": "BAL"}, {"text": "🔄 Refresh", "callback_data": "REF"}]
            ]
        }
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CONFIG["chat_id"],"text":text,"reply_markup":kb},timeout=5)
    except: pass

def check_auto():
    while True:
        try:
            get_all_prices()
            for coin in CONFIG["ACTIVOS"]:
                hist=CONFIG["history"][coin]
                if len(hist)<15: continue
                price=CONFIG["prices"][coin]
                max_20=max(hist[-20:]); min_5=min(hist[-5:])
                dip=(price-max_20)/max_20*100; rec=(price-min_5)/min_5*100
                entrada = dip <= -0.4 and 0.05 <= rec <= 0.3
                if CONFIG["AUTO"] and entrada and len(CONFIG["bolas"]) < CONFIG["MAX"]:
                    costo = CONFIG["BALANCE"]/CONFIG["MAX"] if CONFIG["COMPOUND"] else CONFIG["BALANCE_INICIAL"]/CONFIG["MAX"]
                    nid=int(time.time())%10000
                    CONFIG["bolas"].append({"id":nid,"coin":coin,"entry":price,"costo":costo})
                    CONFIG["high"][str(nid)]=price; CONFIG["stats_entradas"][coin]+=1; save_data()
                for b in CONFIG["bolas"][:]:
                    if b["coin"]!=coin: continue
                    key=str(b["id"])
                    if key not in CONFIG["high"]: CONFIG["high"][key]=b["entry"]
                    if price>CONFIG["high"][key]: CONFIG["high"][key]=price
                    gain=(price-b["entry"])/b["entry"]*100; trail=(price-CONFIG["high"][key])/CONFIG["high"][key]*100
                    venta_profit = gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]
                    venta_stop = gain <= CONFIG["STOP_LOSS_PCT"]
                    if not (venta_profit or venta_stop): continue
                    bruto=b["costo"]*gain/100; neto=bruto-b["costo"]*0.002
                    CONFIG["BALANCE"]+=neto
                    log=f"{'💰 VENDI' if venta_profit else '🚨 STOP'} {b['coin']} {gain:.2f}% NETO ${neto:.2f}"
                    try:
                        if CONFIG["chat_id"]!=0:
                            kb={"inline_keyboard": [[{"text":"🚀 ABRIR DASHBOARD","url":RENDER_URL}]]}
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CONFIG["chat_id"],"text":log,"reply_markup":kb},timeout=5)
                    except: pass
                    CONFIG["bolas"].remove(b); save_data()
            time.sleep(25)
        except: time.sleep(25)

def keep_alive():
    while True:
        try: time.sleep(600); requests.get(RENDER_URL,timeout=5)
        except: pass

threading.Thread(target=check_auto,daemon=True).start()
threading.Thread(target=keep_alive,daemon=True).start()

@app.route("/")
def dash():
    get_all_prices()
    dia=get_dia_actual(); costo_bola = CONFIG["BALANCE"]/CONFIG["MAX"]
    html=f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='15'></head><body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px'><h1 style='color:#FFD700'>💵 V98.3 LIMPIO 💵</h1><div style='background:#1a1a1a;padding:10px'>BAL ${CONFIG['BALANCE']:.2f} COSTO/BOLA ${costo_bola:.0f} MAX {CONFIG['MAX']}</div>"
    for v in [0.1,0.2,0.3,0.4,0.5]: html+=f"<a href='/set_retail/{v}' style='margin:2px;padding:8px;background:{'#0c6' if CONFIG['RETAIL_PCT']==v else '#333'};color:#fff;text-decoration:none'>{v}%</a>"
    html+=f"<br><br>"
    for s in [-5.0,-7.0,-10.0]: html+=f"<a href='/set_stop/{s}' style='margin:2px;padding:8px;background:{'#f44' if CONFIG['STOP_LOSS_PCT']==s else '#333'};color:#fff;text-decoration:none'>{s}%</a><br><br>"
    for i in range(1,11): html+=f"<a href='/set_max/{i}' style='margin:2px;padding:8px;background:{'#FFD700' if CONFIG['MAX']==i else '#333'};color:{'#000' if CONFIG['MAX']==i else '#fff'};text-decoration:none'>{i}</a>"
    html+="</body></html>"
    return html

@app.route("/set_retail/<float:val>")
def set_retail(val): CONFIG["RETAIL_PCT"]=val; save_data(); return dash()
@app.route("/set_max/<int:val>")
def set_max(val):
    if 1 <= val <= 10: CONFIG["MAX"]=val; save_data()
    return dash()
@app.route("/set_stop/<float:val>")
def set_stop(val): CONFIG["STOP_LOSS_PCT"]=val; save_data(); return dash()
@app.route("/"+BOT_TOKEN, methods=["POST"])
def webhook():
    data=request.get_json()
    if not data: return jsonify({"ok":True})
    if "callback_query" in data:
        CONFIG["chat_id"]=data["callback_query"]["message"]["chat"]["id"]; save_data()
        send_tg_dashboard()
        return jsonify({"ok":True})
    if "message" not in data: return jsonify({"ok":True})
    CONFIG["chat_id"]=data["message"]["chat"]["id"]; save_data()
    send_tg_dashboard()
    return jsonify({"ok":True})
@app.route("/estado")
def estado(): return jsonify(CONFIG)
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
