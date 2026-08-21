import os, time, requests, threading, json
from datetime import datetime, date
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
RENDER_URL = "https://telegram-bot-cijp.onrender.com"
DATA_FILE = "data.json"

DEFAULT = {
    "VERSION": "V99 COMPLETO CIRCULO + DESGLOSE + BOTON",
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

def send_tg(text, with_button=True):
    try:
        if CONFIG["chat_id"]==0: return
        kb = {"inline_keyboard": [[{"text": "🚀 ABRIR DASHBOARD", "url": RENDER_URL}]]} if with_button else None
        payload = {"chat_id":CONFIG["chat_id"],"text":text}
        if kb: payload["reply_markup"]=kb
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json=payload,timeout=5)
    except: pass

def send_tg_dashboard():
    try:
        if CONFIG["chat_id"]==0: return
        costo = CONFIG["BALANCE"]/CONFIG["MAX"]
        acumulado = CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]
        text = f"💵 V99 DIA {get_dia_actual()}/30\nBAL ${CONFIG['BALANCE']:.2f} ACUM +${acumulado:.0f}\nCOSTO/BOLA ${costo:.0f} MAX {CONFIG['MAX']} RETAIL {CONFIG['RETAIL_PCT']}% STOP {CONFIG['STOP_LOSS_PCT']}%\n\n👇 PICALE PARA ABRIR:"
        kb = {"inline_keyboard": [[{"text":"🚀 ABRIR DASHBOARD","url":RENDER_URL}],[{"text":"📊 Stats","callback_data":"STATS"},{"text":"🔄 Refresh","callback_data":"REF"}]]}
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
                    CONFIG["bolas"].append({"id":nid,"coin":coin,"entry":price,"costo":costo,"time":time.strftime("%H:%M")})
                    CONFIG["high"][str(nid)]=price
                    CONFIG["stats_entradas"][coin]+=1
                    CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} 🟢 COMPRO {coin} ${price:.2f} Costo ${costo:.0f} dip {dip:.1f}%")
                    save_data()
                for b in CONFIG["bolas"][:]:
                    if b["coin"]!=coin: continue
                    key=str(b["id"])
                    if key not in CONFIG["high"]: CONFIG["high"][key]=b["entry"]
                    if price>CONFIG["high"][key]: CONFIG["high"][key]=price
                    gain=(price-b["entry"])/b["entry"]*100; trail=(price-CONFIG["high"][key])/CONFIG["high"][key]*100
                    venta_profit = gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]
                    venta_stop = gain <= CONFIG["STOP_LOSS_PCT"]
                    if not (venta_profit or venta_stop): continue
                    bruto=b["costo"]*gain/100; fees=b["costo"]*0.002; neto=bruto-fees
                    CONFIG["BALANCE"]+=neto; CONFIG["profit_hoy"]+=neto
                    CONFIG["profit_por_moneda"][b["coin"]]+=neto
                    if neto>0: CONFIG["stats_exitosas"][b["coin"]]+=1
                    tipo="💰 PROFIT" if venta_profit else "🚨 STOP"
                    CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} {tipo} {b['coin']} {gain:.2f}% NETO ${neto:.2f} BAL ${CONFIG['BALANCE']:.0f}")
                    send_tg(f"{tipo} {b['coin']} {gain:.2f}% NETO ${neto:.2f} BAL ${CONFIG['BALANCE']:.0f}")
                    CONFIG["bolas"].remove(b); save_data()
            time.sleep(20)
        except: time.sleep(20)

def keep_alive():
    while True:
        try: time.sleep(600); requests.get(RENDER_URL,timeout=5)
        except: pass

threading.Thread(target=check_auto,daemon=True).start()
threading.Thread(target=keep_alive,daemon=True).start()

@app.route("/")
def dash():
    get_all_prices()
    dia=get_dia_actual(); pct=(dia/30)*100; circ=283; offset=circ-(pct/100*circ)
    acumulado=CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]
    costo_bola = CONFIG["BALANCE"]/CONFIG["MAX"] if CONFIG["MAX"]>0 else 0
    gan_neta = costo_bola*CONFIG["RETAIL_PCT"]/100 - costo_bola*0.002
    perd_neta = costo_bola*abs(CONFIG["STOP_LOSS_PCT"])/100 + costo_bola*0.002

    html=f"""<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='12'><title>V99 COMPLETO</title></head>
<body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px;text-align:center'>
<style>.circle-wrap{{position:relative;width:240px;height:240px;margin:15px auto}}.circle-wrap svg{{transform:rotate(-90deg);width:240px;height:240px}}.circle-bg{{fill:none;stroke:#222;stroke-width:12}}.circle-fill{{fill:none;stroke:#FFD700;stroke-width:12;stroke-linecap:round;filter:drop-shadow(0 0 8px #FFD700)}}.circle-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}}</style>
<h1 style='color:#FFD700;font-size:20px;margin:5px'>💵 V99 COMPLETO 💵</h1>

<div class="circle-wrap"><svg><circle class="circle-bg" cx="120" cy="120" r="90"></circle><circle class="circle-fill" cx="120" cy="120" r="90" stroke-dasharray="{circ}" stroke-dashoffset="{offset}"></circle></svg>
<div class="circle-text"><div style='font-size:10px;color:#aaa'>BASE</div><div style='font-size:18px'>${CONFIG['BALANCE_INICIAL']:.0f}</div><div style='font-size:11px;color:#aaa;margin-top:8px'>ACUMULADO BOLA NIEVE</div><div style='font-size:36px;color:#00ff66;font-weight:bold'>+${acumulado:.0f}</div><div style='font-size:12px;color:#FFD700'>DIA {dia} / 30 AUTO {"ON" if CONFIG["AUTO"] else "OFF"}</div><div style='font-size:10px;color:#aaa'>BAL ${CONFIG['BALANCE']:.2f}</div></div></div>

<div style='background:#1a1a1a;padding:10px;border-left:4px solid #00ff66;font-size:12px;text-align:left;margin:10px 0'>
<b style='color:#FFD700'>⚙️ CONFIG ACTUAL:</b> MAX <b>{CONFIG['MAX']}</b> | RETAIL <b>{CONFIG['RETAIL_PCT']}%</b> | STOP <b>{CONFIG['STOP_LOSS_PCT']}%</b> | TRAIL {CONFIG['TRAIL_PCT']}% | BOLA NIEVE {'ON' if CONFIG['COMPOUND'] else 'OFF'}<br>
COSTO/BOLA <b style='color:#FFD700'>${costo_bola:.2f}</b> = ${CONFIG['BALANCE']:.0f}/{CONFIG['MAX']} | Si vendes +{CONFIG['RETAIL_PCT']}% ganas <b style='color:#00ff66'>${gan_neta:.2f} neto</b> | Si STOP {CONFIG['STOP_LOSS_PCT']}% pierdes <b style='color:#ff4444'>${perd_neta:.2f}</b><br>
MONEDAS: {', '.join(CONFIG['ACTIVOS'])}
</div>

<div style='background:#111;padding:10px;margin:10px 0;border:1px solid #00c853;text-align:left'><b style='color:#00c853'>🎯 RETAIL (GANANCIA POR BOLA) ACTUAL {CONFIG['RETAIL_PCT']}%</b><br><br>"""
    for v in [0.1,0.2,0.3,0.4,0.5,0.6,1.0]:
        bg="#00c853" if CONFIG["RETAIL_PCT"]==v else "#333"
        html+=f"<a href='/set_retail/{v}' style='margin:2px;padding:8px 12px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{v}%</a>"
    html+=f"</div><div style='background:#222;padding:10px;margin:10px 0;border:1px solid #ff4444;text-align:left'><b style='color:#ff4444'>🚨 STOP LOSS (PERDIDA MAX) ACTUAL {CONFIG['STOP_LOSS_PCT']}%</b><br><br>"
    for s in [-3.0,-5.0,-7.0,-10.0,-15.0]:
        bg="#ff4444" if CONFIG["STOP_LOSS_PCT"]==s else "#333"
        html+=f"<a href='/set_stop/{s}' style='margin:2px;padding:8px 12px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{s}%</a>"
    html+=f"</div><div style='background:#1a1a1a;padding:10px;margin:10px 0;border:1px solid #FFD700;text-align:left'><b style='color:#FFD700'>🎲 ENTRADAS 1 A 10 - ACTUAL {CONFIG['MAX']} BOLAS</b><br><span style='font-size:10px;color:#aaa'>Costo por bola ${costo_bola:.0f} c/u</span><br><br>"
    for i in range(1,11):
        bg="#FFD700" if CONFIG["MAX"]==i else "#333"; col="#000" if CONFIG["MAX"]==i else "#fff"
        html+=f"<a href='/set_max/{i}' style='margin:2px;padding:10px 12px;background:{bg};color:{col};text-decoration:none;border-radius:6px;display:inline-block;font-weight:bold'>{i}</a>"
    html+=f"</div><div style='background:#111;padding:10px;margin:10px 0;border:1px solid #2962ff;text-align:left'><b style='color:#2962ff'>🪙 MONEDAS ON/OFF - TOCA PARA ACTIVAR/DESACTIVAR</b><br><br>"
    for c in CONFIG["COINS"]:
        bg="#00c853" if c in CONFIG["ACTIVOS"] else "#444"; price=CONFIG["prices"].get(c,0)
        html+=f"<a href='/toggle/{c}' style='margin:2px;padding:10px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{c} {price:.2f} {'ON' if c in CONFIG['ACTIVOS'] else 'OFF'}</a>"

    # DESGLOSE BOLAS ACTIVAS
    html+=f"</div><div style='background:#151515;padding:10px;margin:10px 0;border:1px solid #FFD700;text-align:left'><b style='color:#FFD700'>🔥 BOLAS ACTIVAS MAX {CONFIG['MAX']} | COSTO C/U ${costo_bola:.2f}</b><br>"
    if not CONFIG["bolas"]:
        html+=f"<span style='color:#aaa'>Esperando fondo -0.4%... Proxima bola ${costo_bola:.0f} vendera en +{CONFIG['RETAIL_PCT']}% = +${gan_neta:.2f} neto</span><br>"
    for b in CONFIG["bolas"]:
        cur=CONFIG["prices"].get(b["coin"],b["entry"]); gain=(cur-b["entry"])/b["entry"]*100; color="#00ff66" if gain>=0 else "#ff4444"
        html+=f"<div style='margin:4px 0;padding:4px;background:#222'>[{b.get('time','--')}] {b['coin']} E ${b['entry']:.2f} → ${cur:.2f} <b style='color:{color}'>{gain:.2f}%</b> Costo ${b['costo']:.0f} <a href='/vender/{b['id']}' style='color:#FFD700'>[VENDER]</a></div>"

    # DESGLOSE ENTRADAS Y GANADAS/PERDIDAS POR MONEDA
    html+=f"</div><div style='background:#1a1a1a;padding:10px;margin:10px 0;border:1px solid #00ff66;text-align:left'><b style='color:#00ff66'>📊 DESGLOSE POR MONEDA - ENTRADAS / GANADAS / PERDIDAS / PROFIT</b><br><br>"
    html+="<table style='width:100%;font-size:11px;border-collapse:collapse'><tr style='background:#222'><th>MONEDA</th><th>ENTRADAS</th><th>GANADAS</th><th>PERDIDAS</th><th>WIN%</th><th>PROFIT</th></tr>"
    for c in CONFIG["COINS"]:
        ent=CONFIG["stats_entradas"].get(c,0); win=CONFIG["stats_exitosas"].get(c,0); loss=ent-win; profit=CONFIG["profit_por_moneda"].get(c,0)
        winpct = (win/ent*100) if ent>0 else 0
        col="#00ff66" if profit>=0 else "#ff4444"
        html+=f"<tr style='border-bottom:1px solid #333'><td>{c}</td><td>{ent}</td><td style='color:#00ff66'>{win}</td><td style='color:#ff4444'>{loss}</td><td>{winpct:.0f}%</td><td style='color:{col}'>${profit:.2f}</td></tr>"
    html+="</table></div>"

    # LOG COMPLETO
    html+=f"<div style='background:#0f0f0f;padding:10px;margin:10px 0;text-align:left;font-size:10px;max-height:300px;overflow:auto;border:1px solid #333'><b>📜 HISTORIAL ULTIMOS TRADES (QUE MONEDA FUE)</b><br>"
    for t in CONFIG["trades_log"][:50]:
        color="#00ff66" if "PROFIT" in t or "VENDI" in t or "💰" in t else "#ffaa00" if "COMPRO" in t else "#ff4444"
        html+=f"<div style='color:{color};margin:2px 0'>{t}</div>"
    html+=f"</div><div style='margin:15px 0'><a href='/toggle_auto' style='padding:12px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#ff4444'};color:#fff;text-decoration:none;border-radius:8px;margin:5px;display:inline-block'>AUTO {'ON' if CONFIG['AUTO'] else 'OFF'}</a><a href='/toggle_compound' style='padding:12px 20px;background:{'#FFD700' if CONFIG['COMPOUND'] else '#444'};color:{'#000' if CONFIG['COMPOUND'] else '#fff'};text-decoration:none;border-radius:8px;margin:5px;display:inline-block'>BOLA NIEVE {'ON' if CONFIG['COMPOUND'] else 'OFF'}</a></div></body></html>"
    return html

@app.route("/set_retail/<float:val>")
def set_retail(val): CONFIG["RETAIL_PCT"]=val; save_data(); return dash()
@app.route("/set_max/<int:val>")
def set_max(val):
    if 1 <= val <= 10: CONFIG["MAX"]=val; save_data()
    return dash()
@app.route("/set_stop/<float:val>")
def set_stop(val): CONFIG["STOP_LOSS_PCT"]=val; save_data(); return dash()
@app.route("/toggle/<coin>")
def toggle_coin(coin):
    if coin in CONFIG["ACTIVOS"]:
        if len(CONFIG["ACTIVOS"])>1: CONFIG["ACTIVOS"].remove(coin)
    else: CONFIG["ACTIVOS"].append(coin)
    save_data(); return dash()
@app.route("/toggle_auto")
def toggle_auto(): CONFIG["AUTO"]=not CONFIG["AUTO"]; save_data(); return dash()
@app.route("/toggle_compound")
def toggle_compound(): CONFIG["COMPOUND"]=not CONFIG["COMPOUND"]; save_data(); return dash()
@app.route("/vender/<int:bid>")
def vender(bid):
    for b in CONFIG["bolas"][:]:
        if b["id"]==bid:
            cur=CONFIG["prices"].get(b["coin"],b["entry"]); gain=(cur-b["entry"])/b["entry"]*100; neto=b["costo"]*gain/100 - b["costo"]*0.002
            CONFIG["BALANCE"]+=neto; CONFIG["bolas"].remove(b); CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} MANUAL {b['coin']} {gain:.2f}% NETO ${neto:.2f}"); save_data()
    return dash()
@app.route("/"+BOT_TOKEN, methods=["POST"])
def webhook():
    data=request.get_json()
    if not data: return jsonify({"ok":True})
    if "callback_query" in data:
        CONFIG["chat_id"]=data["callback_query"]["message"]["chat"]["id"]; save_data(); send_tg_dashboard()
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":data["callback_query"]["id"],"text":"Abriendo dashboard"},timeout=5)
        except: pass
        return jsonify({"ok":True})
    if "message" not in data: return jsonify({"ok":True})
    CONFIG["chat_id"]=data["message"]["chat"]["id"]; save_data(); send_tg_dashboard()
    return jsonify({"ok":True})
@app.route("/estado")
def estado(): return jsonify(CONFIG)
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
