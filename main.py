import os, time, threading, requests
from flask import Flask, request
from datetime import datetime

print("INICIANDO MAQUINA V105.8 FIX...")

CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "BOLAS_MAX": 10,
    "COSTO_BOLA": 1031.63,
    "FEES_PCT": 0.35,
    "MIN_RETAIL_PCT": 0.3,
    "STOP_PCT": -7.0,
    "TRAIL_PCT": 0.2,
    "MONEDAS": ["BTC","ETH","SOL","DOGE","XRP","ADA","AVAX"],
}

bolas = [
    {"moneda": "XRP", "compra": 22.24, "costo": 1031.63},
    {"moneda": "ETH", "compra": 40049.34, "costo": 1031.63},
]

TOKEN = os.environ.get("TELEGRAM_TOKEN")
print(f"TOKEN existe? {'SI' if TOKEN else 'NO'}")

def valido(p): 
    return p and p != 0 and p > 0.001

def calc(entra, actual, costo):
    if not valido(entra) or not valido(actual): 
        return 0,0,0
    try:
        bruto = ((actual-entra)/entra)*100
        neto = bruto - CONFIG["FEES_PCT"]
        usd = costo*(neto/100)
        return bruto,neto,usd
    except: 
        return 0,0,0

def precio(m):
    d={"BTC":1273222.19,"ETH":39926.52,"SOL":1531.61,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33}
    return d.get(m,0)

def responder_dashboard(cid):
    tot=0
    msg = f"MAQUINA V105.8 BAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f} ACUM +${CONFIG['ACUMULADO']}\n\n"
    for b in bolas:
        a=precio(b['moneda'])
        _,n,us=calc(b['compra'],a,b['costo'])
        tot+=us
        emoji = "VERDE" if n>=0 else "ROJO"
        msg += f"{emoji} {b['moneda']} E {b['compra']} -> {a} ({n:.2f}%) ${us:.2f} FLOTANTE\n"
    msg += f"\nTOTAL FLOTANTE: ${tot:.2f}\n"
    msg += "https://telegram-bot-cijp.onrender.com"
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":msg})
    except Exception as e:
        print(f"Error enviando: {e}")

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    total=0
    html="<html><head><meta name='viewport' content='width=device-width'><style>body{background:#0e0e0e;color:#fff;font-family:monospace;padding:10px}.card{background:#1a1a1a;padding:12px;border-radius:12px;margin-bottom:10px}.rojo{color:#ff4444}.verde{color:#00ff88}.bola{border-left:4px solid #ff4444;padding:8px;margin:8px 0;background:#222}</style></head><body><h2>MAQUINA V105.8 FIX</h2>"
    html+=f"<div class='card'>BAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f}<br>{datetime.now().strftime('%H:%M:%S')}</div><div class='card'><h3>BOLAS</h3>"
    for b in bolas:
        act=precio(b['moneda'])
        _,neto,usd=calc(b['compra'],act,b['costo'])
        total+=usd
        col="verde" if neto>=0 else "rojo"
        html+=f"<div class='bola'><b>{b['moneda']}</b> E {b['compra']} -> {act}<br><span class='{col}'>{neto:.2f}% ${usd:.2f}</span></div>"
    html+=f"<hr><b class='rojo'>TOTAL: ${total:.2f}</b></div></body></html>"
    return html

@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data: 
            return "ok", 200
        txt = data.get("message",{}).get("text","").strip().upper()
        cid = data.get("message",{}).get("chat",{}).get("id")
        print(f"Webhook: {txt}")
        if txt == "DASHBOARD" and cid:
            responder_dashboard(cid)
        if txt == "AUTO ON" and cid:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":"AUTO ON OK"})
    except Exception as e:
        print(f"Error webhook: {e}")
    return "ok", 200

def run_flask():
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))

threading.Thread(target=run_flask,daemon=True).start()

def bot_polling():
    offset=0
    print("Polling iniciado...")
    while True:
        try:
            if not TOKEN: 
                time.sleep(10)
                continue
            r=requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=10",timeout=15).json()
            for u in r.get("result",[]):
                offset=u["update_id"]+1
                txt=u.get("message",{}).get("text","").strip().upper()
                cid=u.get("message",{}).get("chat",{}).get("id")
                print(f"Polling: {txt}")
                if txt=="DASHBOARD" and cid:
                    responder_dashboard(cid)
        except Exception as e:
            print(f"Error polling: {e}")
            time.sleep(5)

threading.Thread(target=bot_polling,daemon=True).start()
print("V105.8 LISTO - SIN ERROR 404")
while True: 
    time.sleep(10)
