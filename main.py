import os, time, requests, threading, json, calendar
from datetime import datetime, date
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
RENDER_URL = "https://telegram-bot-cijp.onrender.com"
DATA_FILE = "data.json"

DEFAULT = {
    "VERSION": "V104 MAQUINA COMPLETA CIRCULO LIMPIO",
    "COINS": ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "ACTIVOS": ["ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "MAX": 7, "TRAIL_PCT": 0.2, "RETAIL_PCT": 0.3, "STOP_LOSS_PCT": -7.0,
    "BALANCE": 10310.00, "BALANCE_INICIAL": 10000.0,
    "FECHA_INICIO": str(date.today()), "DIAS_TOTAL": 30, "FEES_PCT": 0.1,
    "AUTO": True, "COMPOUND": True,
    "bolas": [], "prices": {}, "high": {}, "history": {},
    "profit_por_moneda": {}, "stats_entradas": {}, "stats_exitosas": {},
    "trades_log": [], "chat_id": 0, "ganadas_hoy": 0, "perdidas_hoy": 0,
    "bruta_total": 315.0, "comisiones_total": 5.0
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
                if d.get("RETAIL_PCT",0.3) < 0.3: d["RETAIL_PCT"]=0.3
                return d
        except: pass
    return DEFAULT.copy()

def save_data():
    try:
        with open(DATA_FILE,"w") as f: json.dump(CONFIG,f)
    except: pass

CONFIG = load_data()

def get_mes_info():
    hoy = datetime.now()
    dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    dia_actual = hoy.day
    pct = (dia_actual / dias_mes) * 100
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    return dia_actual, dias_mes, pct, meses[hoy.month-1], hoy.year

def get_all_prices():
    for coin in CONFIG["COINS"]:
        try:
            r=requests.get(f"https://api.coinbase.com/v2/prices/{coin}-MXN/spot",timeout=4).json()
            CONFIG["prices"][coin]=float(r["data"]["amount"])
            CONFIG["history"][coin].append(CONFIG["prices"][coin])
            if len(CONFIG["history"][coin])>60: CONFIG["history"][coin].pop(0)
        except: pass

def send_ganada(coin, gain_pct, neto):
    try:
        if CONFIG["chat_id"]==0: return
        total_e=sum(CONFIG["stats_entradas"].values()); total_g=sum(CONFIG["stats_exitosas"].values())
        text=f"✅ GANADA LIMPIA {coin}\n💰 {gain_pct:.2f}% | NETO +${neto:.2f}\n💵 BAL ${CONFIG['BALANCE']:.2f} (+${CONFIG['BALANCE']-CONFIG['BALANCE_INICIAL']:.0f})\n📊 {total_g}G/{total_e-total_g}P de {total_e} | Hoy {CONFIG['ganadas_hoy']}G/{CONFIG['perdidas_hoy']}P\nMÁQUINA DE HACER DINERO"
        kb={"inline_keyboard": [[{"text":"💵 ABRIR MÁQUINA DE HACER DINERO","url":RENDER_URL}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CONFIG["chat_id"],"text":text,"reply_markup":kb},timeout=5)
    except: pass

def send_tg_dashboard():
    try:
        if CONFIG["chat_id"]==0: return
        costo=CONFIG["BALANCE"]/CONFIG["MAX"]; acum=CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]
        total_e=sum(CONFIG["stats_entradas"].values()); total_g=sum(CONFIG["stats_exitosas"].values())
        text=f"💵 MÁQUINA DE HACER DINERO\nBAL ${CONFIG['BALANCE']:.2f} ACUM +${acum:.0f}\nCOSTO/BOLA ${costo:.0f} MAX {CONFIG['MAX']} RETAIL {CONFIG['RETAIL_PCT']}% STOP {CONFIG['STOP_LOSS_PCT']}%\nRESUMEN {total_g}G/{total_e-total_g}P de {total_e}"
        kb={"inline_keyboard": [[{"text":"💵 ABRIR MÁQUINA DE HACER DINERO","url":RENDER_URL}]]}
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
                    CONFIG["high"][str(nid)]=price; CONFIG["stats_entradas"][coin]+=1
                    CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} 🟢 ENTRO {coin} ${price:.2f} Costo ${costo:.0f}")
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
                    bruta=b["costo"]*gain/100; com=b["costo"]*0.002; neto=bruta-com
                    CONFIG["BALANCE"]+=neto; CONFIG["profit_por_moneda"][b["coin"]]+=neto
                    CONFIG["bruta_total"]+=bruta; CONFIG["comisiones_total"]+=com
                    if venta_profit and neto>0:
                        CONFIG["stats_exitosas"][b["coin"]]+=1; CONFIG["ganadas_hoy"]+=1
                        CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} ✅ GANADA {b['coin']} {gain:.2f}% NETO +${neto:.2f}")
                        save_data(); send_ganada(b["coin"],gain,neto)
                    else:
                        CONFIG["perdidas_hoy"]+=1
                        CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} ❌ PERDIDA {b['coin']} {gain:.2f}% NETO ${neto:.2f}")
                        save_data()
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
    dia_actual, dias_mes, pct, nombre_mes, year = get_mes_info()
    circ=283; offset=circ-(pct/100*circ)
    acum=CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]
    costo_bola=CONFIG["BALANCE"]/CONFIG["MAX"]
    gan_neta=costo_bola*CONFIG["RETAIL_PCT"]/100 - costo_bola*0.002
    total_e=sum(CONFIG["stats_entradas"].values()); total_g=sum(CONFIG["stats_exitosas"].values()); total_p=total_e-total_g

    html=f"""<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='12'><title>MAQUINA DE HACER DINERO</title></head>
<body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px;text-align:center'>
<style>.circle-wrap{{position:relative;width:260px;height:260px;margin:15px auto}}.circle-wrap svg{{transform:rotate(-90deg);width:260px;height:260px}}.circle-bg{{fill:none;stroke:#1a1a1a;stroke-width:16}}.circle-fill{{fill:none;stroke:#FFD700;stroke-width:16;stroke-linecap:round;filter:drop-shadow(0 0 12px #FFD700)}}.circle-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}}.stats-box{{background:#141414;border:1px solid #333;border-radius:10px;padding:12px;width:280px;margin:10px auto;text-align:left;font-size:13px}}</style>

<div style='background:#111;border:1px solid #222;border-radius:12px;padding:10px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center'>
<div style='text-align:left'><b style='color:#FFD700;font-size:16px'>⚙️ MAQUINA DE HACER DINERO</b><br><span style='color:#00ff66;font-size:11px'>● BOT ACTIVO</span></div>
<div style='text-align:right;font-size:11px;color:#aaa'>Día {dia_actual}/{dias_mes} • {pct:.0f}% del mes<br>{nombre_mes} {year}</div>
</div>

<div class="circle-wrap"><svg><circle class="circle-bg" cx="130" cy="130" r="100"></circle><circle class="circle-fill" cx="130" cy="130" r="100" stroke-dasharray="{circ}" stroke-dashoffset="{offset}"></circle></svg>
<div class="circle-text"><div style='font-size:11px;color:#aaa;letter-spacing:1px'>BASE $10,000</div><div style='font-size:16px;color:#4ade80;margin-top:6px;font-weight:bold'>ACUMULADO</div><div style='font-size:48px;color:#4ade80;font-weight:bold;line-height:1'>+${acum:.0f}</div></div></div>

<div class="stats-box">
<div style='display:flex;justify-content:space-between;margin:6px 0'><span style='color:#aaa'>Ganancia Bruta:</span><span style='color:#fff;font-weight:bold'>${CONFIG['bruta_total']:.0f}</span></div>
<div style='display:flex;justify-content:space-between;margin:6px 0'><span style='color:#aaa'>Comisiones:</span><span style='color:#ff5a5a'>-${CONFIG['comisiones_total']:.2f}</span></div>
<div style='display:flex;justify-content:space-between;margin:6px 0'><span style='color:#aaa'>Total Neto:</span><span style='color:#4ade80;font-weight:bold'>+${acum:.0f}</span></div>
<hr style='border:0;border-top:1px solid #222;margin:10px 0'>
<div style='display:flex;justify-content:space-between'><span style='color:#FFD700;font-weight:bold'>BALANCE</span><span style='color:#FFD700;font-size:22px;font-weight:bold'>${CONFIG['BALANCE']:.0f}</span></div>
</div>

<div style='background:#1a1a1a;padding:10px;border-left:4px solid #00ff66;font-size:11px;text-align:left;margin:10px auto;width:90%'>⚙️ CONFIG REAL: MAX {CONFIG['MAX']} | MINORISTA {CONFIG['RETAIL_PCT']}% | PARADA {CONFIG['STOP_LOSS_PCT']}% | SENDERO {CONFIG['TRAIL_PCT']}% | BOLA NIEVE {"EN" if CONFIG["COMPOUND"] else "OFF"}<br>COSTO/BOLA <b style='color:#FFD700'>${costo_bola:.2f}</b> = ${CONFIG['BALANCE']:.0f}/{CONFIG['MAX']} | GANANCIA <b style='color:#00ff66'>+${gan_neta:.2f} neto</b> por bola<br>MONEDAS: {', '.join(CONFIG['ACTIVOS'])} | DIA {dia_actual}/{dias_mes} {nombre_mes}</div>

<div style='background:#111;padding:10px;margin:10px auto;border:1px solid #00c853;text-align:left;width:90%'><b style='color:#00c853'>🎯 MINORISTA ACTUAL {CONFIG['RETAIL_PCT']}% - SOLO RENTABLES</b><br><br>"""
    for v in [0.3,0.4,0.5,0.6,1.0]:
        bg="#00c853" if CONFIG["RETAIL_PCT"]==v else "#333"
        html+=f"<a href='/set_retail/{v}' style='margin:3px;padding:10px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block;font-weight:bold'>{v}%</a>"
    html+=f"</div><div style='background:#222;padding:10px;margin:10px auto;border:1px solid #ff4444;text-align:left;width:90%'><b style='color:#ff4444'>🚨 STOP LOSS ACTUAL {CONFIG['STOP_LOSS_PCT']}%</b><br><br>"
    for s in [-3.0,-5.0,-7.0,-10.0,-15.0]:
        bg="#ff4444" if CONFIG["STOP_LOSS_PCT"]==s else "#333"
        html+=f"<a href='/set_stop/{s}' style='margin:2px;padding:10px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{s}%</a>"
    html+=f"</div><div style='background:#1a1a1a;padding:10px;margin:10px auto;border:1px solid #FFD700;text-align:left;width:90%'><b style='color:#FFD700'>🎲 ENTRADAS 1 A 10 - ACTUAL {CONFIG['MAX']}</b><br><br>"
    for i in range(1,11):
        bg="#FFD700" if CONFIG["MAX"]==i else "#333"; col="#000" if CONFIG["MAX"]==i else "#fff"
        html+=f"<a href='/set_max/{i}' style='margin:2px;padding:10px 12px;background:{bg};color:{col};text-decoration:none;border-radius:6px;display:inline-block;font-weight:bold'>{i}</a>"
    html+=f"</div><div style='background:#111;padding:10px;margin:10px auto;border:1px solid #2962ff;text-align:left;width:90%'><b style='color:#2962ff'>🪙 MONEDAS - TOCA PARA ACTIVAR/DESACTIVAR</b><br><br>"
    for c in CONFIG["COINS"]:
        bg="#00c853" if c in CONFIG["ACTIVOS"] else "#444"; price=CONFIG["prices"].get(c,0)
        html+=f"<a href='/toggle/{c}' style='margin:2px;padding:10px 14px;background:{bg};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{c} {price:.2f} {'ON' if c in CONFIG['ACTIVOS'] else 'OFF'}</a>"
    html+=f"</div><div style='background:#151515;padding:10px;margin:10px auto;border:1px solid #FFD700;text-align:left;width:90%'><b style='color:#FFD700'>🔥 BOLAS ACTIVAS MAX {CONFIG['MAX']} | COSTO C/U ${costo_bola:.2f}</b><br>"
    if not CONFIG["bolas"]: html+=f"Esperando fondo -0.4%... Proxima bola ${costo_bola:.0f} vendera en +{CONFIG['RETAIL_PCT']}% = +${gan_neta:.2f} neto<br>"
    for b in CONFIG["bolas"]:
        cur=CONFIG["prices"].get(b["coin"],b["entry"]); gain=(cur-b["entry"])/b["entry"]*100
        html+=f"{b['coin']} E {b['entry']:.2f} -> {cur:.2f} ({gain:.2f}%) <a href='/vender/{b['id']}' style='color:#FFD700'>[VENDER]</a><br>"
    html+=f"</div><div style='background:#1a1a1a;padding:10px;margin:10px auto;border:1px solid #00ff66;text-align:left;width:90%'><b style='color:#00ff66'>📊 DESGLOSE POR MONEDA - ENTRADAS / GANADAS / PERDIDAS / WIN% / PROFIT</b><br><br><table style='width:100%;font-size:11px'><tr style='background:#222'><th>MONEDA</th><th>ENT</th><th>GAN</th><th>PER</th><th>WIN%</th><th>GANANCIA</th></tr>"
    for c in CONFIG["COINS"]:
        ent=CONFIG["stats_entradas"].get(c,0); win=CONFIG["stats_exitosas"].get(c,0); loss=ent-win; profit=CONFIG["profit_por_moneda"].get(c,0); winpct=(win/ent*100) if ent>0 else 0; col="#00ff66" if profit>=0 else "#ff4444"
        html+=f"<tr><td>{c}</td><td>{ent}</td><td style='color:#00ff66'>{win}</td><td style='color:#ff4444'>{loss}</td><td>{winpct:.0f}%</td><td style='color:{col}'>${profit:.2f}</td></tr>"
    html+=f"</table><br>Total: {total_g}G / {total_p}P de {total_e} | Hoy: {CONFIG['ganadas_hoy']}G/{CONFIG['perdidas_hoy']}P | {nombre_mes} {dia_actual}/{dias_mes}</div>"
    html+=f"<div style='background:#0f0f0f;padding:10px;font-size:10px;text-align:left;width:90%;margin:10px auto;max-height:300px;overflow:auto'><b>📜 ULTIMOS COMERCIOS (QUE MONEDA FUE)</b><br>"
    for t in CONFIG["trades_log"][:50]: html+=f"{t}<br>"
    html+=f"</div><div style='margin:15px'><a href='/toggle_auto' style='padding:12px 20px;background:{'#00c853' if CONFIG['AUTO'] else '#ff4444'};color:#fff;text-decoration:none;border-radius:8px;margin:5px;display:inline-block'>{'ENCENDIDO AUTOMATICO' if CONFIG['AUTO'] else 'APAGADO AUTOMATICO'}</a><a href='/toggle_compound' style='padding:12px 20px;background:#FFD700;color:#000;text-decoration:none;border-radius:8px;margin:5px;display:inline-block'>BOLA NIEVE {'EN' if CONFIG['COMPOUND'] else 'OFF'}</a></div></body></html>"
    return html

@app.route("/set_retail/<float:val>")
def set_retail(val):
    if val>=0.3: CONFIG["RETAIL_PCT"]=val; save_data()
    return dash()
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
            cur=CONFIG["prices"].get(b["coin"],b["entry"]); gain=(cur-b["entry"])/b["entry"]*100
            bruta=b["costo"]*gain/100; com=b["costo"]*0.002; neto=bruta-com
            CONFIG["BALANCE"]+=neto; CONFIG["bolas"].remove(b); save_data()
    return dash()
@app.route("/"+BOT_TOKEN, methods=["POST"])
def webhook():
    data=request.get_json()
    if not data: return jsonify({"ok":True})
    if "callback_query" in data: CONFIG["chat_id"]=data["callback_query"]["message"]["chat"]["id"]; save_data(); send_tg_dashboard(); return jsonify({"ok":True})
    if "message" not in data: return jsonify({"ok":True})
    CONFIG["chat_id"]=data["message"]["chat"]["id"]; save_data(); send_tg_dashboard(); return jsonify({"ok":True})
@app.route("/estado")
def estado(): return jsonify(CONFIG)
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
