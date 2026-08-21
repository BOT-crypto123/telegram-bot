import os, time, threading, requests
from flask import Flask
from datetime import datetime

print("INICIANDO MAQUINA V105.6...")

CONFIG = {
    "BASE": 10000.0, "ACUMULADO": 316.0, "BOLAS_MAX": 10,
    "COSTO_BOLA": 1031.63, "FEES_PCT": 0.35, "MIN_RETAIL_PCT": 0.3,
    "STOP_PCT": -7.0, "TRAIL_PCT": 0.2,
    "MONEDAS": ["BTC","ETH","SOL","DOGE","XRP","ADA","AVAX"],
}
bolas = [
    {"moneda": "XRP", "compra": 22.24, "costo": 1031.63},
    {"moneda": "ETH", "compra": 40049.34, "costo": 1031.63},
]
TOKEN = os.environ.get("TELEGRAM_TOKEN")
print(f"TOKEN existe? {'SI' if TOKEN else 'NO - AGREGA EN RENDER ENVIRONMENT'}")

def valido(p): return p and p != 0 and p > 0.001
def calc(entra, actual, costo):
    if not valido(entra) or not valido(actual): return 0,0,0
    try:
        bruto = ((actual-entra)/entra)*100
        neto = bruto - CONFIG["FEES_PCT"]
        usd = costo*(neto/100)
        return bruto,neto,usd
    except: return 0,0,0
def precio(m):
    d={"BTC":1273222.19,"ETH":39926.52,"SOL":1531.61,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33}
    return d.get(m,0)

app = Flask(__name__)
@app.route('/')
def home():
    total=0
    html="<html><head><meta name='viewport' content='width=device-width'><style>body{background:#0e0e0e;color:#fff;font-family:monospace;padding:10px}.card{background:#1a1a1a;padding:12px;border-radius:12px;margin-bottom:10px}.rojo{color:#ff4444}.verde{color:#00ff88}.bola{border-left:4px solid #ff4444;padding:8px;margin:8px 0;background:#222}</style></head><body><h2>💰 MAQUINA V105.6 FINAL</h2>"
    html+=f"<div class='card'>BAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f} ACUM +${CONFIG['ACUMULADO']}<br>{datetime.now().strftime('%H:%M:%S')}</div><div class='card'><h3>BOLAS ABIERTAS</h3>"
    for b in bolas:
        act=precio(b['moneda']); _,neto,usd=calc(b['compra'],act,b['costo']); total+=usd
        col="verde" if neto>=0 else "rojo"
        html+=f"<div class='bola'><b>{b['moneda']}</b> E {b['compra']} -> {act}<br><span class='{col}'>{neto:.2f}% ${usd:.2f}</span></div>"
    html+=f"<hr><b class='rojo'>TOTAL: ${total:.2f}</b></div></body></html>"
    return html

def run_flask():
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_flask,daemon=True).start()

def bot():
    offset=0
    print("🤖 Telegram polling iniciado...")
    while True:
        try:
            if not TOKEN:
                print("ERROR: No hay TELEGRAM_TOKEN en Environment")
                time.sleep(10); continue
            r=requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=10",timeout=15).json()
            for u in r.get("result",[]):
                offset=u["update_id"]+1
                txt=u.get("message",{}).get("text","").strip().upper()
                cid=u.get("message",{}).get("chat",{}).get("id")
                print(f"Mensaje recibido: {txt}")
                if not txt: continue
                if txt=="DASHBOARD":
                    tot=0; msg=f"💰 *MAQUINA V105.6*\nBAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f}\n\n"
                    for b in bolas:
                        a=precio(b['moneda']); _,n,us=calc(b['compra'],a,b['costo']); tot+=us
                        msg+=f"{'🟢' if n>=0 else '🔴'} {b['moneda']} E {b['compra']} -> {a} ({n:.2f}%) ${us:.2f}\n"
                    msg+=f"\n*TOTAL: ${tot:.2f}*"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":msg,"parse_mode":"Markdown"})
                elif txt=="AUTO ON":
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":"✅ AUTO ON"})
        except Exception as e:
            print(f"Error bot: {e}"); time.sleep(5)

threading.Thread(target=bot,daemon=True).start()
print("🚀 V105.6 FINAL TODO LISTO - ESPERANDO DASHBOARD")
while True: time.sleep(10)
