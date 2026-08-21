import os, time, requests, threading, json
from datetime import datetime, date
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
RENDER_URL = "https://telegram-bot-cijp.onrender.com"
DATA_FILE = "data.json"

DEFAULT = {
    "VERSION": "V102 MAQUINA DE HACER DINERO",
    "COINS": ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "ACTIVOS": ["ETH", "SOL", "DOGE", "XRP", "ADA", "AVAX", "SHIB"],
    "MAX": 7, "TRAIL_PCT": 0.2, "RETAIL_PCT": 0.3, "STOP_LOSS_PCT": -7.0,
    "BALANCE": 10310.00, "BALANCE_INICIAL": 10000.0,
    "FECHA_INICIO": str(date.today()), "DIAS_TOTAL": 30,
    "AUTO": True, "COMPOUND": True,
    "bolas": [], "prices": {}, "high": {}, "history": {},
    "profit_por_moneda": {}, "stats_entradas": {}, "stats_exitosas": {},
    "trades_log": [], "chat_id": 0, "ganadas_hoy": 0, "perdidas_hoy": 0
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

def send_ganada(coin, gain_pct, neto):
    try:
        if CONFIG["chat_id"]==0: return
        total_e=sum(CONFIG["stats_entradas"].values()); total_g=sum(CONFIG["stats_exitosas"].values())
        text=f"✅ GANADA LIMPIA {coin}\n💰 {gain_pct:.2f}% | NETO +${neto:.2f}\n💵 BAL ${CONFIG['BALANCE']:.2f} (+${CONFIG['BALANCE']-CONFIG['BALANCE_INICIAL']:.0f})\n📊 {total_g}G/{total_e-total_g}P de {total_e} | Hoy {CONFIG['ganadas_hoy']}G/{CONFIG['perdidas_hoy']}P\nDIA {get_dia_actual()}/30 - MAQUINA DE HACER DINERO"
        kb={"inline_keyboard": [[{"text":"🚀 ABRIR MÁQUINA DE HACER DINERO","url":RENDER_URL}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CONFIG["chat_id"],"text":text,"reply_markup":kb},timeout=5)
    except: pass

def send_tg_dashboard():
    try:
        if CONFIG["chat_id"]==0: return
        costo=CONFIG["BALANCE"]/CONFIG["MAX"]; acum=CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]
        total_e=sum(CONFIG["stats_entradas"].values()); total_g=sum(CONFIG["stats_exitosas"].values())
        text=f"💵 MÁQUINA DE HACER DINERO DIA {get_dia_actual()}/30\nBAL ${CONFIG['BALANCE']:.2f} ACUM +${acum:.0f}\nCOSTO/BOLA ${costo:.0f} MAX {CONFIG['MAX']} RETAIL {CONFIG['RETAIL_PCT']}% STOP {CONFIG['STOP_LOSS_PCT']}%\nRESUMEN {total_g}G/{total_e-total_g}P de {total_e}"
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
                if CONFIG["AUTO"] and dip <= -0.4 and 0.05 <= rec <= 0.3 and len(CONFIG["bolas"]) < CONFIG["MAX"]:
                    costo=CONFIG["BALANCE"]/CONFIG["MAX"] if CONFIG["COMPOUND"] else CONFIG["BALANCE_INICIAL"]/CONFIG["MAX"]
                    nid=int(time.time())%10000
                    CONFIG["bolas"].append({"id":nid,"coin":coin,"entry":price,"costo":costo,"time":time.strftime("%H:%M")})
                    CONFIG["high"][str(nid)]=price; CONFIG["stats_entradas"][coin]+=1
                    CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} 🟢 ENTRO {coin} ${price:.2f}"); save_data()
                for b in CONFIG["bolas"][:]:
                    if b["coin"]!=coin: continue
                    key=str(b["id"])
                    if key not in CONFIG["high"]: CONFIG["high"][key]=b["entry"]
                    if price>CONFIG["high"][key]: CONFIG["high"][key]=price
                    gain=(price-b["entry"])/b["entry"]*100; trail=(price-CONFIG["high"][key])/CONFIG["high"][key]*100
                    if not ( (gain >= CONFIG["RETAIL_PCT"] and trail <= -CONFIG["TRAIL_PCT"]) or gain <= CONFIG["STOP_LOSS_PCT"]): continue
                    neto=b["costo"]*gain/100 - b["costo"]*0.002; CONFIG["BALANCE"]+=neto; CONFIG["profit_por_moneda"][b["coin"]]+=neto
                    if gain>0 and neto>0: CONFIG["stats_exitosas"][b["coin"]]+=1; CONFIG["ganadas_hoy"]+=1; CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} ✅ GANADA {b['coin']} {gain:.2f}% +${neto:.2f}"); save_data(); send_ganada(b["coin"],gain,neto)
                    else: CONFIG["perdidas_hoy"]+=1; CONFIG["trades_log"].insert(0,f"{time.strftime('%H:%M')} ❌ PERDIDA {b['coin']} {gain:.2f}%"); save_data()
                    CONFIG["bolas"].remove(b)
            time.sleep(20)
        except: time.sleep(20)

threading.Thread(target=check_auto,daemon=True).start()

@app.route("/")
def dash():
    get_all_prices()
    dia=get_dia_actual(); pct=(dia/30)*100; circ=283; offset=circ-(pct/100*circ)
    acum=CONFIG["BALANCE"]-CONFIG["BALANCE_INICIAL"]; costo_bola=CONFIG["BALANCE"]/CONFIG["MAX"]; gan_neta=costo_bola*CONFIG["RETAIL_PCT"]/100 - costo_bola*0.002
    total_e=sum(CONFIG["stats_entradas"].values()); total_g=sum(CONFIG["stats_exitosas"].values()); total_p=total_e-total_g
    html=f"""<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='12'></head>
<body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px;text-align:center'>
<style>.circle-wrap{{position:relative;width:240px;height:240px;margin:15px auto}}svg{{transform:rotate(-90deg);width:240px;height:240px}}.circle-bg{{fill:none;stroke:#222;stroke-width:12}}.circle-fill{{fill:none;stroke:#FFD700;stroke-width:12}}.circle-text{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)}}</style>
<h1 style='color:#FFD700;font-size:22px'>💵 MÁQUINA DE HACER DINERO 💵</h1>
<div class="circle-wrap"><svg><circle class="circle-bg" cx="120" cy="120" r="90"></circle><circle class="circle-fill" cx="120" cy="120" r="90" stroke-dasharray="{circ}" stroke-dashoffset="{offset}"></circle></svg>
<div class="circle-text"><div style='font-size:10px'>BASE</div><div>${CONFIG['BALANCE_INICIAL']:.0f}</div><div style='font-size:11px;margin-top:6px'>ACUMULADO BOLA NIEVE</div><div style='font-size:34px;color:#00ff66;font-weight:bold'>+${acum:.0f}</div><div style='font-size:12px;color:#FFD700'>DIA {dia}/30 | {total_g}G/{total_p}P de {total_e}</div><div style='font-size:10px'>BAL ${CONFIG['BALANCE']:.2f}</div></div></div>
<div style='background:#1a1a1a;padding:8px;border-left:4px solid #00ff66;font-size:12px;text-align:left'>MAX {CONFIG['MAX']} RETAIL {CONFIG['RETAIL_PCT']}% STOP {CONFIG['STOP_LOSS_PCT']}% COSTO ${costo_bola:.0f} GANANCIA +${gan_neta:.2f} por bola</div>
<div style='background:#111;padding:8px;margin:8px 0;border:1px solid #00c853;text-align:left'><b>🎯 RETAIL</b> """
    for v in [0.3,0.4,0.5,0.6,1.0]:
        bg="#00c853" if CONFIG["RETAIL_PCT"]==v else "#333"
        html+=f"<a href='/set_retail/{v}' style='margin:2px;padding:8px;background:{bg};color:#fff;text-decoration:none;border-radius:5px'>{v}%</a>"
    html+=f"</div><div style='background:#1a1a1a;padding:8px;margin:8px 0;border:1px solid #FFD700;text-align:left'><b>🎲 ENTRADAS 1-10 ACTUAL {CONFIG['MAX']}</b><br>"
    for i in range(1,11):
        bg="#FFD700" if CONFIG["MAX"]==i else "#333"; col="#000" if CONFIG["MAX"]==i else "#fff"
        html+=f"<a href='/set_max/{i}' style='margin:2px;padding:8px;background:{bg};color:{col};text-decoration:none;border-radius:5px'>{i}</a>"
    html+=f"</div><div style='background:#151515;padding:8px;margin:8px 0;border:1px solid #FFD700;text-align:left'><b>🔥 BOLAS ACTIVAS</b><br>"
    if not CONFIG["bolas"]: html+=f"Esperando fondo -0.4%...<br>"
    for b in CONFIG["bolas"]:
        cur=CONFIG["prices"].get(b["coin"],b["entry"]); gain=(cur-b["entry"])/b["entry"]*100
        html+=f"{b['coin']} {gain:.2f}% <a href='/vender/{b['id']}' style='color:#FFD700'>[VENDER]</a><br>"
    html+=f"</div><div style='background:#1a1a1a;padding:8px;border:1px solid #00ff66;text-align:left'><b>📊 DESGLOSE POR MONEDA</b><br><table style='width:100%;font-size:11px'><tr style='background:#222'><th>MON</th><th>ENT</th><th>GAN</th><th>PER</th><th>PROFIT</th></tr>"
    for c in CONFIG["COINS"]:
        ent=CONFIG["stats_entradas"].get(c,0); win=CONFIG["stats_exitosas"].get(c,0); profit=CONFIG["profit_por_moneda"].get(c,0)
        html+=f"<tr><td>{c}</td><td>{ent}</td><td style='color:#00ff66'>{win}</td><td style='color:#ff4444'>{ent-win}</td><td>${profit:.2f}</td></tr>"
    html+=f"</table><br>{total_g}G/{total_p}P de {total_e} | Hoy {CONFIG['ganadas_hoy']}G/{CONFIG['perdidas_hoy']}P</div></body></html>"
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
@app.route("/vender/<int:bid>")
def vender(bid):
    for b in CONFIG["bolas"][:]:
        if b["id"]==bid: CONFIG["BALANCE"]+=b["costo"]*0.002; CONFIG["bolas"].remove(b); save_data()
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
