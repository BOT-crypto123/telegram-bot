import os, sys, requests, threading, time, random
from flask import Flask, request, jsonify
from datetime import datetime

os.environ['PYTHONUNBUFFERED']='1'
sys.stdout.reconfigure(line_buffering=True)
print("INICIANDO V114 BINANCE TP MANUAL 0.3 BASE", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "FEES_PCT": 0.10, # BINANCE 0.05% compra + 0.05% venta = 0.10% total
    "TP_PCT": 0.30, # BASE 0.30% COMO PEDISTE - DESDE AQUI YA HAY GANANCIA
    "AUTO": True,
    "BOLAS_MAX": 8,
    "COSTO_BOLA": 1031.63,
    "EXCHANGE": "BINANCE"
}

MONEDAS = {"BTC": True, "ETH": True, "XRP": True, "SOL": True, "DOGE": True, "ADA": True, "AVAX": True, "BNB": True}

bolas = [
    {"id":1,"moneda":"XRP","compra":2.85,"costo":1031.63,"actual":2.85},
    {"id":2,"moneda":"ETH","compra":2450.50,"costo":1031.63,"actual":2450.50},
]

historial = []
PRECIOS = {}

def get_precio_binance(moneda):
    try:
        symbol = f"{moneda}USDT"
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
        price = float(r['price'])
        PRECIOS[moneda] = price
        return price
    except:
        return PRECIOS.get(moneda, 0)

def calc(e,a,c):
    if not e or a==0: return 0,0,0
    bruto=((a-e)/e)*100
    neto=bruto-CONFIG["FEES_PCT"]
    usd=c*(neto/100)
    return bruto, neto, usd

def get_stats():
    flot=0; vend=0
    for b in bolas:
        actual = get_precio_binance(b["moneda"])
        if actual!=0: b["actual"]=actual
        _, neto, usd = calc(b["compra"], b["actual"], b["costo"])
        b["neto"]=neto; b["usd"]=usd; flot+=usd
        if neto>=CONFIG["TP_PCT"]: vend+=1
    bal=CONFIG["BASE"]+CONFIG["ACUMULADO"]
    return bal, flot, bal+flot, (datetime.now().day/30)*100, vend

def comprar_bola(moneda):
    if len(bolas) >= CONFIG["BOLAS_MAX"]: return None
    if moneda in [x["moneda"] for x in bolas]: return None
    p=get_precio_binance(moneda)
    if p==0: return None
    n={"id":int(time.time()),"moneda":moneda,"compra":p,"costo":CONFIG["COSTO_BOLA"],"actual":p,"neto":0,"usd":0}
    bolas.append(n)
    return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if b["id"]==id_bola:
            CONFIG["ACUMULADO"]+=b["usd"]
            historial.insert(0,{"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"neto":round(b["neto"],2),"usd":round(b["usd"],2),"estado":"CERRADA"})
            bolas.remove(b)
            return b
    return None

def enviar(cid, txt, botones=True):
    try:
        data={"chat_id":cid,"text":txt}
        if botones:
            data["reply_markup"]={"keyboard":[["DASHBOARD","BALANCE"],["AUTO ON","AUTO OFF"],["TP 0.3","TP 0.6"],["COMPRAR","WEB"]],"resize_keyboard":True,"is_persistent":True}
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=data, timeout=10)
    except: pass

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>V114 TP MANUAL 0.3 BASE</title>
<style>
body{background:#0a0e1a;color:#fff;font-family:Arial;padding:12px}
.card{background:#121a2b;border-radius:14px;padding:12px;margin:10px 0;border:1px solid #f3ba2f}
.btn{padding:10px 14px;border-radius:10px;border:none;margin:4px;font-weight:bold;cursor:pointer}
.on{background:#f3ba2f;color:#000}.off{background:#1e2a44;color:#888}.tp{background:#00ff88;color:#000;border:2px solid #00ff88}.tp-active{background:#fff;color:#000;border:2px solid #00ff88;box-shadow:0 0 10px #00ff88}
.input-tp{background:#000;color:#00ff88;border:2px solid #f3ba2f;border-radius:10px;padding:10px;width:100px;font-size:18px;font-weight:bold;text-align:center}
.rojo{border-color:#ff3040}.verde{border-color:#00ff88}
</style></head><body>
<h2 style="text-align:center;color:#f3ba2f">V114 BINANCE TP MANUAL</h2>
<div class="card" style="border-color:#00ff88">
<b>FORMULA:</b> BASE + ACUM + FLOT = TOTAL<br>
<span id="res"></span><br>
<small>BINANCE FEES 0.10% | BASE TP 0.30% ya hay ganancia neta</small>
</div>

<div class="card" style="border:2px solid #00ff88">
<h3 style="margin:0 0 10px 0;color:#00ff88">TP MANUAL - Base 0.30% ganancia</h3>
<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
<input type="number" id="tpInput" class="input-tp" step="0.05" min="0.10" max="2.0" value="0.30">
<button class="btn tp" onclick="setTPManual()">APLICAR TP</button>
<span id="tpActual" style="color:#f3ba2f;font-weight:bold"></span>
</div>
<div style="margin-top:10px">
Botones rapidos base:<br>
<button class="btn tp" id="b03" onclick="apiTP(0.3)">0.3% BASE</button>
<button class="btn tp" id="b04" onclick="apiTP(0.4)">0.4%</button>
<button class="btn tp" id="b05" onclick="apiTP(0.5)">0.5%</button>
<button class="btn tp" id="b06" onclick="apiTP(0.6)">0.6% MAX</button>
</div>
<div style="margin-top:8px;font-size:12px;color:#8aa">
0.3% = +0.20% neto real | 0.4% = +0.30% neto | 0.5% = +0.40% neto | 0.6% = +0.50% neto (descontando 0.10% Binance)
</div>
</div>

<div class="card">AUTO: <button class="btn on" onclick="api('auto')">AUTO ON/OFF</button> BOLAS MAX: <button class="btn off" onclick="api('max?val=2')">2</button><button class="btn off" onclick="api('max?val=5')">5</button><button class="btn off" onclick="api('max?val=8')">8</button></div>
<div class="card">MONEDAS 8:<div id="mons"></div></div>
<div id="ab"></div>

<script>
let currentTP=0.30
async function load(){let r=await fetch('/api/data');let d=await r.json();currentTP=d.config.TP_PCT;
document.getElementById('res').innerHTML=`BAL $${d.balance.toFixed(2)} BASE $${d.config.BASE} + ACUM $${d.config.ACUMULADO.toFixed(2)} | FLOT $${d.flotante.toFixed(2)} | TOTAL $${d.total.toFixed(2)} | BOLAS ${d.bolas.length}/${d.config.BOLAS_MAX} VENDIBLES ${d.vendibles} AUTO ${d.config.AUTO?'ON':'OFF'}`;
document.getElementById('tpActual').innerText=`TP ACTUAL: ${d.config.TP_PCT}%`;
document.getElementById('tpInput').value=d.config.TP_PCT;
document.querySelectorAll('[id^=b0]').forEach(b=>b.classList.remove('tp-active'));
if(d.config.TP_PCT==0.3) document.getElementById('b03').classList.add('tp-active');
if(d.config.TP_PCT==0.4) document.getElementById('b04').classList.add('tp-active');
if(d.config.TP_PCT==0.5) document.getElementById('b05').classList.add('tp-active');
if(d.config.TP_PCT==0.6) document.getElementById('b06').classList.add('tp-active');
let m='';for(let k in d.monedas){m+=`<button class="btn ${d.monedas[k]?'on':'off'}" onclick="api('moneda?m=${k}')">${k}</button>`}document.getElementById('mons').innerHTML=m;
let ab='';d.bolas.forEach(b=>{ab+=`<div class="card ${b.neto>=d.config.TP_PCT?'verde':'rojo'}"><b>${b.moneda}</b> ${b.compra} -> ${b.actual.toFixed(4)} Neto ${b.neto.toFixed(2)}% $${b.usd.toFixed(2)} ${b.neto>=d.config.TP_PCT?'✅ VENDIBLE':''} <button class="btn off" onclick="api('vender?id=${b.id}')">VENDER</button></div>`});document.getElementById('ab').innerHTML=ab;
}
async function api(u){await fetch('/api/'+u);load();}
async function apiTP(v){await fetch('/api/tp?val='+v);load();}
async function setTPManual(){let v=parseFloat(document.getElementById('tpInput').value);if(v<0.1||v>2){alert('Min 0.1% Max 2%');return;}await fetch('/api/tp?val='+v);load();}
load();setInterval(load,5000);
</script></body></html>
"""

app=Flask(__name__)
@app.route('/', methods=['GET'])
def home(): return HTML
@app.route('/api/data')
def data():
    bal, flot, total, prog, vend = get_stats()
    return jsonify({"balance":bal,"flotante":flot,"total":total,"progreso":prog,"vendibles":vend,"config":CONFIG,"bolas":bolas,"monedas":MONEDAS,"historial":historial})
@app.route('/api/tp')
def tp():
    try:
        v=float(request.args.get('val',0.3))
        if v<0.1: v=0.1
        if v>2.0: v=2.0
        CONFIG["TP_PCT"]=round(v,2)
    except: pass
    return "ok"
@app.route('/api/max')
def maxb(): CONFIG["BOLAS_MAX"]=int(request.args.get('val',2)); return "ok"
@app.route('/api/auto')
def auto(): CONFIG["AUTO"]=not CONFIG["AUTO"]; return "ok"
@app.route('/api/moneda')
def mon():
    m=request.args.get('m')
    if m in MONEDAS: MONEDAS[m]=not MONEDAS[m]
    return "ok"
@app.route('/api/vender')
def vender():
    try:
        b=vender_bola(int(request.args.get('id')))
        if b and CHAT_ID: enviar(CHAT_ID, f"VENDIDA {b['moneda']} TP {CONFIG['TP_PCT']}% Neto {b['neto']:.2f}% Ganancia ${b['usd']:.2f}", True)
    except: pass
    return "ok"

@app.route('/', methods=['POST'])
def wh():
    global CHAT_ID
    try:
        data=request.get_json(force=True, silent=True)
        if not data: return "ok",200
        msg=data.get("message",{})
        txt=msg.get("text","").strip().upper()
        cid=msg.get("chat",{}).get("id")
        if cid: CHAT_ID=cid
        bal, flot, total, prog, vend = get_stats()

        if txt.startswith("TP "):
            try:
                v=float(txt.replace("TP","").strip())
                CONFIG["TP_PCT"]=round(v,2)
                enviar(cid, f"✅ TP CAMBIADO A {CONFIG['TP_PCT']}% MANUAL\nBase 0.3% = +0.20% neto real (Binance 0.10% fees)\nMAX 0.6% = +0.50% neto", True)
            except:
                enviar(cid, "Usa: TP 0.3, TP 0.4, TP 0.5, TP 0.6", True)
        elif txt in ["DASHBOARD","/START","START","TP 0.3","TP 0.6"]:
            if txt=="TP 0.3": CONFIG["TP_PCT"]=0.3
            if txt=="TP 0.6": CONFIG["TP_PCT"]=0.6
            t=f"V114 BINANCE TP MANUAL 0.3% BASE\nBAL ${bal:.2f} FLOT ${flot:.2f} TOTAL ${total:.2f}\nTP ACTUAL: {CONFIG['TP_PCT']}% (FEES Binance 0.10%)\nNeto real: {CONFIG['TP_PCT']-0.10:.2f}%\nBOLAS {len(bolas)}/{CONFIG['BOLAS_MAX']} VEND {vend}\n\nBOTONES:\nTP 0.3% = BASE ganancia\nTP 0.4% = +0.30% neto\nTP 0.5% = +0.40% neto\nTP 0.6% = MAX +0.50% neto\n\nEn Telegram escribe TP 0.35 para cualquier valor\nWEB: {URL}"
            enviar(cid, t, True)
        elif txt=="COMPRAR":
            for mon, activa in MONEDAS.items():
                if activa:
                    n=comprar_bola(mon)
                    if n:
                        enviar(cid, f"COMPRADA {mon} a {n['compra']} TP {CONFIG['TP_PCT']}%", True)
                        break
            else:
                enviar(cid, "Max alcanzado", True)
        elif txt=="AUTO ON": CONFIG["AUTO"]=True; enviar(cid, f"AUTO ON TP {CONFIG['TP_PCT']}% BASE", True)
        elif txt=="AUTO OFF": CONFIG["AUTO"]=False; enviar(cid, "AUTO OFF", True)
        elif txt in ["WEB","BALANCE","DASHBOARD"]:
            bal, flot, total, prog, vend = get_stats()
            enviar(cid, f"BAL ${bal:.2f} TOTAL ${total:.2f} TP {CONFIG['TP_PCT']}%", True)
    except Exception as e:
        print(e, flush=True)
    return "ok",200

def auto_loop():
    print("LOOP V114 TP MANUAL 0.3 BASE", flush=True)
    while True:
        try:
            if CONFIG["AUTO"] and CHAT_ID:
                bal, flot, total, prog, vend = get_stats()
                for b in bolas[:]:
                    if b["neto"] >= CONFIG["TP_PCT"]:
                        vb=vender_bola(b["id"])
                        if vb:
                            enviar(CHAT_ID, f"🤖 VENTA TP {CONFIG['TP_PCT']}%\n{vb['moneda']} {vb['compra']} -> {vb['actual']:.4f}\nNeto {vb['neto']:.2f}% (Fees 0.10% Binance)\nGanancia ${vb['usd']:.2f}", True)
                        time.sleep(1)
                if len(bolas) < CONFIG["BOLAS_MAX"]:
                    cand=[m for m,on in MONEDAS.items() if on and m not in [bb["moneda"] for bb in bolas]]
                    if cand:
                        n=comprar_bola(random.choice(cand))
                        if n: enviar(CHAT_ID, f"🤖 COMPRA {n['moneda']} a {n['compra']} TP {CONFIG['TP_PCT']}%", True)
            time.sleep(40)
        except: time.sleep(10)

threading.Thread(target=auto_loop, daemon=True).start()

if TOKEN:
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true", timeout
