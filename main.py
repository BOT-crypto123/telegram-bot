import os, requests
from flask import Flask, request
from datetime import datetime

print("INICIANDO V106 WEBHOOK PURO - SIN POLLING")

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CONFIG = {"BASE":10000.0,"ACUMULADO":316.0,"FEES_PCT":0.35}
bolas = [{"moneda":"XRP","compra":22.24,"costo":1031.63},{"moneda":"ETH","compra":40049.34,"costo":1031.63}]

def calc(e,a,c):
    if not e or not a: return 0,0
    b=((a-e)/e)*100; n=b-CONFIG["FEES_PCT"]; return n, c*(n/100)
def precio(m): return {"BTC":1273222.19,"ETH":39926.52,"SOL":1531.61,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33}.get(m,0)

def responder(cid):
    tot=0
    msg=f"MAQUINA V106 BAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f} ACUM +${CONFIG['ACUMULADO']}\n\n"
    for b in bolas:
        a=precio(b['moneda']); n,us=calc(b['compra'],a,b['costo']); tot+=us
        msg+=f"{'VERDE' if n>=0 else 'ROJO'} {b['moneda']} E {b['compra']} -> {a} {n:.2f}% ${us:.2f}\n"
    msg+=f"\nTOTAL FLOTANTE: ${tot:.2f}\n{URL}"
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":msg},timeout=10)
        print(f"Enviado DASHBOARD a {cid}")
    except Exception as e:
        print(f"Error envio: {e}")

app=Flask(__name__)

@app.route('/',methods=['GET'])
def home():
    return f"<h1>V106 LIVE {datetime.now()} SIN 409</h1><p>Webhook activo</p>"

@app.route('/',methods=['POST'])
def webhook():
    try:
        data=request.get_json(force=True,silent=True)
        if not data: return "ok",200
        print(f"Webhook POST: {data}")
        msg=data.get("message",{})
        txt=msg.get("text","").strip().upper()
        cid=msg.get("chat",{}).get("id")
        print(f"Comando: {txt} de {cid}")
        if txt=="DASHBOARD" and cid:
            responder(cid)
        if txt=="AUTO ON" and cid:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":"AUTO ON OK V106"})
    except Exception as e:
        print(f"Error webhook: {e}")
    return "ok",200

# Auto-configura webhook al iniciar
if TOKEN:
    try:
        r=requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL}",timeout=10).json()
        print(f"Webhook seteado: {r}")
    except Exception as e:
        print(f"Error seteando webhook: {e}")

print("V106 LISTO - ESPERANDO POST DE TELEGRAM")
app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
