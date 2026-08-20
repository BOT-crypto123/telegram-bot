import os, time, requests
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"
RENDER_URL = "https://telegram-bot-cijp.onrender.com"

CONFIG = {
    "VERSION": "V70 DASH TOTAL",
    "MAX": 5,
    "TRAIL_PCT": 0.4,
    "RETAIL_PCT": 0.8,
    "BALANCE": 10000,
    "FEES": 0.1,
    "AUTO_COMPRA": False, # False = solo alerta, True = compra automatico
    "bolas": [
        {"id":1, "entry":69500},
        {"id":2, "entry":69800},
        {"id":3, "entry":70000},
        {"id":4, "entry":70200},
        {"id":5, "entry":70500},
    ],
    "last_price": 115500,
    "cache_time": 0,
    "ultima_alerta": 0
}

def get_price():
    try:
        r=requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=5).json()
        return float(r["data"]["amount"])
    except: return 115500

def calc():
    price=get_price()
    if time.time()-CONFIG["cache_time"]>30:
        CONFIG["last_price"]=price; CONFIG["cache_time"]=time.time()
    else: price=CONFIG["last_price"]
    costo=CONFIG["BALANCE"]/CONFIG["MAX"] if CONFIG["MAX"]>0 else 0
    rows=""; tb=tf=tn=0
    for b in CONFIG["bolas"]:
        bruto = price - b["entry"]
        fees = costo * CONFIG["FEES"]/100 * 2
        neto = bruto - fees
        tb+=bruto; tf+=fees; tn+=neto
        rows+=f"<tr><td>{b['id']}</td><td>${b['entry']}</td><td>${bruto:.2f}</td><td>${fees:.2f}</td><td style='color:{'lime' if neto>0 else 'red'}'><b>${neto:.2f}</b></td></tr>"
    return price,costo,rows,tb,tf,tn

@app.route("/")
def dash():
    price,costo,rows,bruto,fees,neto = calc()
    
    max_btns = "".join([f"<a href='/set_max/{i}' style='margin:3px;padding:8px 14px;background:{'#00c853' if i==CONFIG['MAX'] else '#333'};color:white;text-decoration:none;display:inline-block;border-radius:4px'>{i}</a>" for i in range(2,11)])
    
    trail_btns = "".join([f"<a href='/set_trail/{p}' style='margin:3px;padding:8px 12px;background:{'#00c853' if p==CONFIG['TRAIL_PCT'] else '#333'};color:white;text-decoration:none;display:inline-block;border-radius:4px'>{p}%</a>" for p in [0.1,0.2,0.3,0.4,0.6,0.8,1.0,1.5,2.0]])
    
    retail_btns = "".join([f"<a href='/set_retail/{r}' style='margin:3px;padding:8px 12px;background:{'orange' if r==CONFIG['RETAIL_PCT'] else '#333'};color:white;text-decoration:none;display:inline-block;border-radius:4px'>{r}%</a>" for r in [0.1,0.2,0.3,0.4,0.6,0.8,1.0,1.5]])

    auto_btn = f"<a href='/toggle_auto' style='padding:10px 20px;background:{'#00c853' if CONFIG['AUTO_COMPRA'] else '#ff3d00'};color:white;text-decoration:none;font-weight:bold;border-radius:6px'>AUTO COMPRA: {'ON - Compra solo' if CONFIG['AUTO_COMPRA'] else 'OFF - Solo alerta entrada'}</a>"

    return f"""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20"></head>
    <body style="font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:12px">
    <h3 style="color:#0f0">{CONFIG['VERSION']} | {len(CONFIG['bolas'])}/{CONFIG['MAX']} ABIERTAS | FLOAT ${neto:.2f}</h3>
    
    <div style="background:#1a1a1a;padding:12px;border-left:4px solid #0f0;margin-bottom:12px">
    BTC: <b>${price:.2f}</b> | Costo bola: ${costo:.2f}<br>
    <b>BRUTO ${bruto:.2f} - FEES ${fees:.2f} = NETO ${neto:.2f}</b><br>
    FLOAT = suma Neto = <b style="color:lime">${neto:.2f}</b>
    </div>

    <div style="background:#111;padding:12px;border:1px solid #333;margin-bottom:10px;text-align:center">
    {auto_btn}<br><br>
    <small>ON = el bot compra solo cuando ve oportunidad<br>OFF = solo te manda alerta por Telegram de entrada</small>
    </div>

    <div style="background:#111;padding:12px;border:1px solid #333;margin-bottom:10px">
    <b>MAXIMO OPERACIONES ABIERTAS:</b><br><br>{max_btns}<br><small>Actual: {CONFIG['MAX']} maximo</small>
    </div>

    <div style="background:#111;padding:12px;border:1px solid #333;margin-bottom:10px">
    <b>TRAIL %:</b><br><br>{trail_btns}<br><small>Actual: {CONFIG['TRAIL_PCT']}% - Vende solo en retorno</small>
    </div>

    <div style="background:#111;padding:12px;border:1px solid orange;margin-bottom:12px">
    <b>RETAIL variable % (ganancia objetivo):</b><br><br>{retail_btns}<br><small>Actual: {CONFIG['RETAIL_PCT']}%</small>
    </div>

    <table border=1 style="width:100%;border-collapse:collapse;background:#111" cellpadding=7>
    <tr style="background:#222"><th>Bola</th><th>Entry</th><th>Bruto</th><th>Fees</th><th>Neto = Bruto-Fees</th></tr>
    {rows}
    <tr style="background:#333"><td colspan=2><b>TOTAL FLOAT</b></td><td><b>${bruto:.2f}</b></td><td><b>${fees:.2f}</b></td><td><b style="color:lime">${neto:.2f}</b></td></tr>
    </table>

    <p style="margin-top:15px">
    <a href="/alerta_entrada" style="background:#2196f3;padding:10px 15px;color:white;text-decoration:none;border-radius:4px">PROBAR ALERTA ENTRADA</a>
    <a href="/reset" style="background:red;padding:10px 15px;color:white;text-decoration:none;border-radius:4px;margin-left:10px">RESET 0/{CONFIG['MAX']}</a>
    </p>
    </body></html>
    """

@app.route("/set_max/<int:n>")
def set_max(n): CONFIG["MAX"]=max(2,min(10,n)); return dash()
@app.route("/set_trail/<float:p>")
def set_trail(p): CONFIG["TRAIL_PCT"]=p; return dash()
@app.route("/set_retail/<float:r>")
def set_retail(r): CONFIG["RETAIL_PCT"]=r; return dash()
@app.route("/toggle_auto")
def toggle_auto(): CONFIG["AUTO_COMPRA"]= not CONFIG["AUTO_COMPRA"]; return dash()
@app.route("/reset")
def reset(): CONFIG["bolas"]=[]; return dash()
@app.route("/alerta_entrada")
def alerta_entrada():
    price,costo,rows,bruto,fees,neto = calc()
    try:
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        msg=f"🔔 OPORTUNIDAD ENTRADA\nBTC ${price:.2f}\nMAX {len(CONFIG['bolas'])}/{CONFIG['MAX']}\nTRAIL {CONFIG['TRAIL_PCT']}% RETAIL {CONFIG['RETAIL_PCT']}%\nFLOAT ${neto:.2f}\n{RENDER_URL}\nModo: {'AUTO' if CONFIG['AUTO_COMPRA'] else 'SOLO ALERTA'}"
        requests.post(url, json={"chat_id": "TU_CHAT_ID", "text": msg}, timeout=5)
    except: pass
    return dash()
@app.route("/estado")
def estado(): return jsonify(CONFIG)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json(force=True, silent=True) or {}
    chat_id=data.get("message",{}).get("chat",{}).get("id")
    if chat_id:
        price,costo,rows,bruto,fees,neto = calc()
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        txt=f"📊 DASH {RENDER_URL}\n{len(CONFIG['bolas'])}/{CONFIG['MAX']} MAX | TRAIL {CONFIG['TRAIL_PCT']}% | RETAIL {CONFIG['RETAIL_PCT']}%\nBTC ${price:.2f}\nBRUTO ${bruto:.2f} - FEES ${fees:.2f} = NETO ${neto:.2f}\nFLOAT ${neto:.2f}\nAUTO: {'ON' if CONFIG['AUTO_COMPRA'] else 'OFF solo alerta'}"
        try: requests.post(url, json={"chat_id": chat_id, "text": txt}, timeout=5)
        except: pass
    return jsonify({"ok": True})
@app.route("/<path:p>", methods=["POST"])
def catch_all(p): return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
