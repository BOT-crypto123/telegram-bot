import os, sys, requests, threading, time, random, traceback
from flask import Flask, request, jsonify
from datetime import datetime

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V118 MINIMAL BINANCE", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {"BASE":10000.0,"ACUMULADO":316.0,"FEES_PCT":0.10,"TP_PCT":0.30,"AUTO":True,"BOLAS_MAX":8,"COSTO_BOLA":1031.63}
MONEDAS = {"BTC":True,"ETH":True,"XRP":True,"SOL":True,"DOGE":True,"ADA":True,"AVAX":True,"BNB":True}
bolas = [{"id":1,"moneda":"XRP","compra":2.85,"costo":1031.63,"actual":2.85,"neto":0,"usd":0},{"id":2,"moneda":"ETH","compra":2450.5,"costo":1031.63,"actual":2450.5,"neto":0,"usd":0}]
PRECIOS = {}

def get_precio(moneda):
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + moneda + "USDT", timeout=4)
        return float(r.json()['price'])
    except:
        return 0

def calc(e,a,c):
    if not e or a==0: return 0,0,0
    neto = ((a-e)/e)*100 - CONFIG["FEES_PCT"]
    return 0, neto, c*(neto/100)

def get_stats():
    flot=0;vend=0
    for b in bolas:
        p = get_precio(b["moneda"])
        if p>0: b["actual"]=p
        _,neto,usd = calc(b["compra"], b["actual"], b["costo"])
        b["neto"]=neto; b["usd"]=usd; flot+=usd
        if neto>=CONFIG["TP_PCT"]: vend+=1
    bal = CONFIG["BASE"]+CONFIG["ACUMULADO"]
    return bal, flot, bal+flot, vend

def enviar(cid, txt):
    try:
        data={"chat_id":cid,"text":txt,"reply_markup":{"keyboard":[["DASHBOARD","BALANCE"],["AUTO ON","AUTO OFF"],["TP 0.3","TP 0.6"],["COMPRAR","WEB"]],"resize_keyboard":True}}
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", json=data, timeout=5)
    except Exception as e:
        print("ERR enviar "+str(e), flush=True)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    try:
        bal,flot,total,vend = get_stats()
        html = "<h2>V118 LIVE BINANCE TP 0.3 BASE</h2>"
        html += "<p>BAL $"+str(round(bal,2))+" FLOT $"+str(round(flot,2))+" TOTAL $"+str(round(total,2))+"</p>"
        html += "<p>TP "+str(CONFIG["TP_PCT"])+"% FEES 0.10% BOLAS "+str(len(bolas))+"/"+str(CONFIG["BOLAS_MAX"])+" VEND "+str(vend)+"</p>"
        html += "<p><a href='/api/data'>/api/data</a> | AUTO "+str(CONFIG["AUTO"])+"</p>"
        html += "<p><button onclick=\"fetch('/api/tp?val=0.3').then(()=>location.reload())\">TP 0.3 BASE</button>"
        html += "<button onclick=\"fetch('/api/tp?val=0.4').then(()=>location.reload())\">TP 0.4</button>"
        html += "<button onclick=\"fetch('/api/tp?val=0.5').then(()=>location.reload())\">TP 0.5</button>"
        html += "<button onclick=\"fetch('/api/tp?val=0.6').then(()=>location.reload())\">TP 0.6 MAX</button></p>"
        html += "<p><button onclick=\"fetch('/api/auto').then(()=>location.reload())\">AUTO ON/OFF</button></p>"
        html += "<p>Si ves esto, ya quedo Live. Ahora si le metemos el circulo chingon.</p>"
        return html
    except Exception as e:
        print(traceback.format_exc(), flush=True)
        return "Error: "+str(e), 500

@app.route('/api/data')
def data():
    bal,flot,total,vend=get_stats()
    return jsonify({"balance":bal,"flotante":flot,"total":total,"vendibles":vend,"config":CONFIG,"bolas":bolas,"monedas":MONEDAS})

@app.route('/api/tp')
def tp():
    try:
        v=float(request.args.get('val','0.3'))
        CONFIG["TP_PCT"]=round(max(0.1,min(2.0,v)),2)
    except: pass
    return "ok"

@app.route('/api/max')
def maxb():
    CONFIG["BOLAS_MAX"]=int(request.args.get('val','2'))
    return "ok"

@app.route('/api/auto')
def auto():
    CONFIG["AUTO"]=not CONFIG["AUTO"]
    return "ok"

@app.route('/', methods=['POST'])
def wh():
    global CHAT_ID
    try:
        j=request.get_json(force=True, silent=True)
        if not j: return "ok",200
        msg=j.get("message",{})
        txt=msg.get("text","").strip().upper()
        cid=msg.get("chat",{}).get("id")
        if cid: CHAT_ID=cid
        bal,flot,total,vend=get_stats()
        if txt.startswith("TP "):
            try:
                v=float(txt.replace("TP","").strip())
                CONFIG["TP_PCT"]=round(v,2)
                enviar(cid,"TP CAMBIADO A "+str(CONFIG["TP_PCT"])+"% BASE 0.3% ya ganas")
            except:
                enviar(cid,"Usa TP 0.3, TP 0.4, TP 0.5, TP 0.6")
        elif txt in ["DASHBOARD","/START","START"]:
            t="V118 LIVE\nBAL $"+str(round(bal,2))+" TOTAL $"+str(round(total,2))+"\nTP "+str(CONFIG["TP_PCT"])+"% Fees 0.10% Neto "+str(round(CONFIG["TP_PCT"]-0.10,2))+"%\nBOLAS "+str(len(bolas))+"/"+str(CONFIG["BOLAS_MAX"])+" VEND "+str(vend)+"\nWEB: "+URL
            enviar(cid,t)
        elif txt=="AUTO ON":
            CONFIG["AUTO"]=True
            enviar(cid,"AUTO ON")
        elif txt=="AUTO OFF":
            CONFIG["AUTO"]=False
            enviar(cid,"AUTO OFF")
        elif txt in ["BALANCE","WEB"]:
            enviar(cid,"BAL $"+str(round(bal,2))+" TOTAL $"+str(round(total,2))+" "+URL)
    except Exception as e:
        print("ERR WH "+traceback.format_exc(), flush=True)
    return "ok",200

def loop():
    print("LOOP V118 INICIADO", flush=True)
    while True:
        try:
            time.sleep(40)
        except:
            time.sleep(5)

threading.Thread(target=loop, daemon=True).start()

if TOKEN:
    try:
        requests.get("https://api.telegram.org/bot"+TOKEN+"/deleteWebhook?drop_pending_updates=true", timeout=5)
        requests.get("https://api.telegram.org/bot"+TOKEN+"/setWebhook?url="+URL, timeout=5)
        print("WEBHOOK OK", flush=True)
    except Exception as e:
        print("ERR WEBHOOK "+str(e), flush=True)

print("V118 LISTO - INICIANDO FLASK", flush=True)
try:
    port = int(os.environ.get("PORT","10000"))
    app.run(host='0.0.0.0', port=port, debug=False)
except Exception as e:
    print("FATAL FLASK "+traceback.format_exc(), flush=True)
