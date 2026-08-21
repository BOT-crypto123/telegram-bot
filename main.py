import os, time, requests, threading, json
from datetime import datetime, date
from flask import Flask, jsonify, request

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
RENDER_URL = "https://telegram-bot-cijp.onrender.com"
DATA_FILE = "data.json"

DEFAULT = {
    "VERSION": "V95.1 DINAMICO 8 MONEDAS",
    "COINS": ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "ACTIVOS": ["ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "MAX": 4,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.1,
    "BALANCE": 10310.00,
    "BALANCE_INICIAL": 10000.0,
    "FECHA_INICIO": str(date.today()),
    "DIAS_TOTAL": 30,
    "FEES_PCT": 0.1,
    "AUTO": True,
    "bolas": [],
    "prices": {"SOL":1484.31,"DOGE":1.39,"BTC":1232606.83,"ETH":39814.75,"XRP":12.5,"ADA":8.2,"AVAX":420.0,"SHIB":0.00025},
    "high": {},
    "history": {"SOL":[],"DOGE":[],"BTC":[],"ETH":[],"XRP":[],"ADA":[],"AVAX":[],"SHIB":[]},
    "trades_hoy": 8,
    "profit_hoy": 310.00,
    "profit_bruto": 340.00,
    "profit_fees": 30.00,
    "profit_por_moneda": {"BTC":0,"ETH":120,"SOL":150,"DOGE":40,"XRP":0,"ADA":0,"AVAX":0,"SHIB":0},
    "stats_entradas": {"BTC":0,"ETH":3,"SOL":4,"DOGE":2,"XRP":0,"ADA":0,"AVAX":0,"SHIB":0},
    "stats_exitosas": {"BTC":0,"ETH":2,"SOL":3,"DOGE":1,"XRP":0,"ADA":0,"AVAX":0,"SHIB":0},
    "trades_log": [],
    "chat_id": 0
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r") as f:
                d=json.load(f)
                for k,v in DEFAULT.items():
                    if k not in d: d[k]=v
                # asegurar que nuevas monedas existan en dicts viejos
                for coin in DEFAULT["COINS"]:
                    if coin not in d["profit_por_moneda"]: d["profit_por_moneda"][coin]=0
                    if coin not in d["stats_entradas"]: d["stats_entradas"][coin]=0
                    if coin not in d["stats_exitosas"]: d["stats_exitosas"][coin]=0
                    if coin not in d["history"]: d["history"][coin]=[]
                    if coin not in d["prices"]: d["prices"][coin]=1.0
                return d
        except: pass
    return DEFAULT.copy()

def save_data():
    try:
        with open(DATA_FILE,"w") as f: json.dump(CONFIG,f)
    except: pass

CONFIG = load_data()
if "FECHA_INICIO" not in CONFIG or not CONFIG["FECHA_INICIO"]:
    CONFIG["FECHA_INICIO"]=str(date.today()); save_data()

def get_dia_actual():
    try:
        inicio = datetime.strptime(CONFIG["FECHA_INICIO"], "%Y-%m-%d").date()
        hoy = date.today()
        dias = (hoy - inicio).days + 1
        return min(max(dias,1), CONFIG["DIAS_TOTAL"])
    except: return 2

def get_all_prices():
    for coin in CONFIG["COINS"]:
        try:
            # SHIB viene en MXN tambien
            r=requests.get(f"https://api.coinbase.com/v2/prices/{coin}-MXN/spot",timeout=4).json()
            CONFIG["prices"][coin]=float(r["data"]["amount"])
            CONFIG["history"][coin].append(CONFIG["prices"][coin])
            if len(CONFIG["history"][coin])>60: CONFIG["history"][coin].pop(0)
        except: pass

def send_tg(text):
    try:
        if CONFIG["chat_id"]==0: return
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CONFIG["chat_id"],"text":text},timeout=5)
    except: pass

def check_auto():
    while True:
        try:
            get_all_prices()
            for coin in CONFIG["ACTIVOS"]:
                hist=CONFIG["history"][coin]
                if len(hist)<10: continue
                price=CONFIG["prices"][coin]
                max_20=max(hist[-20:]); min_5=min(hist[-5:])
                dip=(price-max_20)/max_20*100; rec=(price-min_5)/min_5*100
                entrada = dip <= -0.4 and 0.05 <= rec <= 0.3
                if CONFIG["AUTO"] and entrada and len(CONFIG["bolas"]) < CONFIG["MAX"]:
                    costo=CONFIG["BALANCE"]/CONFIG["MAX"]; nid=int(time.time())%10000
                    CONFIG["bolas"].append({"id":nid,"coin":coin,"entry":price,"costo":costo,"time":time.strftime("%H:%M")})
                    CONFIG["high"][str(nid)]=price
                    CONFIG["stats_entradas"][coin]+=1
                    CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} ROBOT COMPRO {coin} ${price:.4f} dip {dip:.2f}%")
                    save_data()
                for b in CONFIG["bolas"][:]:
                    if b["coin"]!=coin: continue
                    key=str(b["id"])
                    if key not in CONFIG["high"]: CONFIG["high"][key]=b["entry"]
                    if price>CONFIG["high"][key]: CONFIG["high"][key]=price
                    gain=(price-b["entry"])/b["entry"]*100; trail=(price-CONFIG["high"][key])/CONFIG["high"][key]*100
                    if gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]:
                        bruto=b["costo"]*gain/100; fees=b["costo"]*CONFIG["FEES_PCT"]/100*2; neto=bruto-fees
                        CONFIG["BALANCE"]+=neto; CONFIG["profit_hoy"]+=neto; CONFIG["profit_bruto"]+=bruto; CONFIG["profit_fees"]+=fees
                        CONFIG["profit_por_moneda"][b["coin"]]+=neto; CONFIG["trades_hoy"]+=1
                        if neto>0: CONFIG["stats_exitosas"][b["coin"]]+=1
                        CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} VENDIO {b['coin']} NETO ${neto:.2f}")
                        if neto>0: send_tg(f"💰 VENDI {b['coin']} NETO ${neto:.2f} BAL ${CONFIG['BALANCE']:.2f}")
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
    dia=get_dia_actual(); total=CONFIG["DIAS_TOTAL"]; pct=(dia/total)*100; circ=283; offset=circ-(pct/100*circ)
    acumulado=CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]
    html=f"""<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='15'><title>V95 DINAMICO</title></head>
<body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px;text-align:center'>
<style>.circle-wrap{{position:relative;width:220px;height:220px;margin:20px auto}}.circle-wrap svg{{transform:rotate(-90deg);width:220px;height:220px}}.circle-bg{{fill:none;stroke:#222;stroke-width:12}}.circle-fill{{fill:none;stroke:#FFD700;stroke-width:12;stroke-linecap:round;filter:drop-shadow(0 0 8px #FFD700)}}.circle-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}}</style>
<h1 style='color:#FFD700;font-size:18px'>💵 MAQUINA DE HACER DINEROS 8 MONEDAS 💵</h1>
<div class="circle-wrap"><svg><circle class="circle-bg" cx="110" cy="110" r="90"></circle><circle class="circle-fill" cx="110" cy="110" r="90" stroke-dasharray="{circ}" stroke-dashoffset="{offset}"></circle></svg>
<div class="circle-text"><div style='font-size:10px;color:#aaa'>BASE</div><div style='font-size:16px'>${CONFIG['BALANCE_INICIAL']:.0f}</div><div style='font-size:11px;color:#aaa;margin-top:6px'>ACUMULADO</div><div style='font-size:32px;color:#00ff66;font-weight:bold'>+${acumulado:.0f}</div><div style='font-size:12px;color:#FFD700'>DIA {dia} / {total} AUTO</div></div></div>
<div style='background:#1a1a1a;padding:10px;border-left:4px solid #00ff66;font-size:12px;text-align:left'>PERSISTENCIA: ON ✅ | ANTI-SLEEP: ON ✅ | BAL ${CONFIG['BALANCE']:.2f} | ESTRATEGIA: FONDO -0.4% + REBOTE | 8 MONEDAS</div>
<div style='background:#111;padding:10px;margin:10px 0;border:1px solid #FFD700;text-align:left'><b style='color:#FFD700'>📊 DESGLOSE POR MONEDA (MAS DINAMISMO)</b><br><br>
<table style='width:100%;font-size:11px;border-collapse:collapse'><tr style='color:#aaa'><th>MONEDA</th><th>ENT</th><th>OK</th><th>WIN%</th><th>NETO</th></tr>"""
    for c in CONFIG["COINS"]:
        ent=CONFIG["stats_entradas"].get(c,0); ex=CONFIG["stats_exitosas"].get(c,0)
        wr=(ex/ent*100) if ent>0 else 0
        neto=CONFIG["profit_por_moneda"].get(c,0)
        html+=f"<tr><td>{c}</td><td>{ent}</td><td>{ex}</td><td>{wr:.0f}%</td><td style='color:#0f0'>${neto:.0f}</td></tr>"
    html+="</table></div>"
    html+=f"<div style='background:#222;padding:10px;margin:10px 0;border:1px solid #00c853;text-align:left'><b style='color:#00c853'>🎯 VENTA RETAIL Actual: {CONFIG['RETAIL_PCT']}%</b><br><br>"
    for v in [0.1,0.2,0.3,0.4,0.5,0.6]:
        bg="#00c853" if CONFIG["RETAIL_PCT"]==v else "#333"
        html+=f"<a href='/set_retail/{v}' style='margin:2px;padding:8px 12px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{v}%</a>"
    html+="</div><div style='background:#111;padding:10px;margin:10px 0;border:1px solid #2962ff;text-align:left'><b style='color:#2962ff'>🪙 MONEDAS ACTIVAS - 8 MONEDAS</b><br><br>"
    for c in CONFIG["COINS"]:
        bg="#00c853" if c in CONFIG["ACTIVOS"] else "#444"
        html+=f"<a href='/toggle/{c}' style='margin:2px;padding:10px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{c} {'ON' if c in CONFIG['ACTIVOS'] else 'OFF'}</a>"
    html+=f"</div><div style='background:#151515;padding:8px;margin:10px 0;font-size:11px;text-align:left'><b>BOLAS ACTIVAS MAX {CONFIG['MAX']}</b><br>"
    if not CONFIG["bolas"]: html+="Robot esperando fondo...<br>"
    for b in CONFIG["bolas"]:
        cur=CONFIG["prices"][b["coin"]]; gain=(cur-b["entry"])/b["entry"]*100
        html+=f"{b['coin']} E {b['entry']:.4f} -> {cur:.4f} ({gain:.2f}%) <a href='/vender/{b['id']}' style='color:#FFD700'>[VENDER]</a><br>"
    html+=f"</div><div style='text-align:center'><a href='/toggle_auto' style='padding:10px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#f00'};color:#fff;text-decoration:none;border-radius:8px'>AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</a></div></body></html>"
    return html

@app.route("/set_retail/<float:val>")
def set_retail(val): CONFIG["RETAIL_PCT"]=val; save_data(); return dash()
@app.route("/toggle/<coin>")
def toggle_coin(coin):
    if coin in CONFIG["ACTIVOS"]:
        if len(CONFIG["ACTIVOS"])>1: CONFIG["ACTIVOS"].remove(coin)
    else: CONFIG["ACTIVOS"].append(coin)
    save_data(); return dash()
@app.route("/toggle_auto")
def toggle_auto(): CONFIG["AUTO"]=not CONFIG["AUTO"]; save_data(); return dash()
@app.route("/vender/<int:bid>")
def vender(bid):
    for b in CONFIG["bolas"][:]:
        if b["id"]==bid:
            cur=CONFIG["prices"][b["coin"]]; gain=(cur-b["entry"])/b["entry"]*100
            bruto=b["costo"]*gain/100; fees=b["costo"]*CONFIG["FEES_PCT"]/100*2; neto=bruto-fees
            CONFIG["BALANCE"]+=neto; CONFIG["profit_hoy"]+=neto; CONFIG["bolas"].remove(b); save_data()
    return dash()
@app.route("/"+BOT_TOKEN, methods=["POST"])
def webhook():
    data=request.get_json()
    if not data or "message" not in data: return jsonify({"ok":True})
    CONFIG["chat_id"]=data["message"]["chat"]["id"]; save_data()
    text=f"💸 V95.1 8 MONEDAS DIA {get_dia_actual()}/30 ACUM +${CONFIG['BALANCE']-CONFIG['BALANCE_INICIAL']:.0f}"
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CONFIG["chat_id"],"text":text},timeout=5)
    except: pass
    return jsonify({"ok":True})
@app.route("/estado")
def estado(): return jsonify(CONFIG)
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
