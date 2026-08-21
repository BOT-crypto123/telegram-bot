import os, time, threading, requests
from flask import Flask, request
from datetime import datetime

print("INICIANDO V105.9 AUTO-FIX")

CONFIG = {"BASE":10000.0,"ACUMULADO":316.0,"BOLAS_MAX":10,"COSTO_BOLA":1031.63,"FEES_PCT":0.35}
bolas = [{"moneda":"XRP","compra":22.24,"costo":1031.63},{"moneda":"ETH","compra":40049.34,"costo":1031.63}]
TOKEN = os.environ.get("TELEGRAM_TOKEN")
print(f"TOKEN existe? {'SI' if TOKEN else 'NO'}")

if TOKEN:
    try:
        r=requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true",timeout=10).json()
        print(f"Webhook auto-borrado: {r}")
    except Exception as e:
        print(f"Error borrando webhook: {e}")

def valido(p): return p and p>0.001
def calc(e,a,c):
    if not valido(e) or not valido(a): return 0,0,0
    b=((a-e)/e)*100; n=b-CONFIG["FEES_PCT"]; u=c*(n/100); return b,n,u
def precio(m): return {"BTC":1273222.19,"ETH":39926.52,"SOL":1531.61,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33}.get(m,0)

def responder(cid):
    tot=0; msg=f"MAQUINA V105.9 BAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f}\n\n"
    for b in bolas:
        a=precio(b['moneda']); _,n,us=calc(b['compra'],a,b['costo']); tot+=us
        msg+=f"{'VERDE' if n>=0 else 'ROJO'} {b['moneda']} {n:.2f}% ${us:.2f}\n"
    msg+=f"\nTOTAL FLOTANTE: ${tot:.2f}\nhttps://telegram-bot-cijp.onrender.com"
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":msg})

app=Flask(__name__)
@app.route('/',methods=['GET'])
def home(): return f"<h1>V105.9 LIVE {datetime.now()}</h1>"
@app.route('/',methods=['POST'])
def wh(): return "ok",200

def run_flask(): app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_flask,daemon=True).start()

def bot_polling():
    off=0; print("Polling iniciado V105.9...")
    while True:
        try:
            if not TOKEN: time.sleep(10); continue
            r=requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={off}&timeout=15",timeout=20).json()
            if not r.get("ok"): print(f"Error API: {r}"); time.sleep(5); continue
            for u in r.get("result",[]):
                off=u["update_id"]+1
                txt=u.get("message",{}).get("text","").strip().upper()
                cid=u.get("message",{}).get("chat",{}).get("id")
                print(f"Polling: {txt} de {cid}")
                if txt=="DASHBOARD" and cid: responder(cid)
                if txt=="AUTO ON" and cid: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":"AUTO ON OK V105.9"})
        except Exception as e:
            print(f"Error polling loop: {e}"); time.sleep(5)

threading.Thread(target=bot_polling,daemon=True).start()
print("V105.9 LISTO")
while True: time.sleep(10)
