import os, sys, requests, threading, time, random, traceback
from flask import Flask, request, jsonify
from datetime import datetime

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V120 FIX UNPACK", flush=True)

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
        p = float(r.json()['price'])
        PRECIOS[moneda]=p
        return p
    except:
        return PRECIOS.get(moneda,0)

def calc(e,a,c):
    if not e or a==0: return 0,0,0
    bruto=((a-e)/e)*100
    neto=bruto-CONFIG["FEES_PCT"]
    usd=c*(neto/100)
    return bruto,neto,usd

def get_stats():
    flot=0;vend=0
    for b in bolas:
        p=get_precio(b["moneda"])
        if p>0:
            b["actual"]=p
        _,neto,usd=calc(b["compra"],b["actual"],b["costo"])
        b["neto"]=neto; b["usd"]=usd; flot+=usd
        if neto>=CONFIG["TP_PCT"]: vend+=1
    bal=CONFIG["BASE"]+CONFIG["ACUMULADO"]
    total=bal+flot
    prog=(datetime.now().day/30)*100
    return bal,flot,total,prog,vend

def comprar_bola(moneda):
    if len(bolas)>=CONFIG["BOLAS_MAX"]: return None
    for x in bolas:
        if x["moneda"]==moneda: return None
    p=get_precio(moneda)
    if p==0: return None
    n={"id":int(time.time()),"moneda":moneda,"compra":p,"costo":CONFIG["COSTO_BOLA"],"actual":p,"neto":0,"usd":0}
    bolas.append(n)
    return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if b["id"]==id_bola:
            CONFIG["ACUMULADO"]+=b["usd"]
            bolas.remove(b)
            return b
    return None

def enviar_solo_dashboard(cid, txt):
    try:
        data={"chat_id":cid,"text":txt,"reply_markup":{"keyboard":[["DASHBOARD"]],"resize_keyboard":True,"is_persistent":True}}
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", json=data, timeout=5)
    except Exception as e:
        print("ERR enviar "+str(e), flush=True)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    try:
        html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V120 FIX</title>"
        html += "<style>body{background:#0a0e1a;color:#fff;font-family:Arial;padding:10px;margin:0}.card{background:#121a2b;border-radius:14px;padding:12px;margin:10px 0;border:1px solid #333}.btn{padding:10px 14px;border-radius:10px;border:none;margin:4px;font-weight:bold}.on{background:#f3ba2f;color:#000}.off{background:#1e2a44;color:#888}.tp{background:#00ff88;color:#000}.tp-active{outline:2px solid #fff}.rojo{border-color:#ff3040}.verde{border-color:#00ff88}.circle-wrap{position:relative;width:210px;height:210px;margin:15px auto}.bg{fill:none;stroke:#1a2332;stroke-width:12}.prog{fill:none;stroke:#f3ba2f;stroke-width:12;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%;transition:0.8s}.center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}.input-tp{background:#000;color:#00ff88;border:2px solid #f3ba2f;border-radius:8px;padding:8px;width:70px;text-align:center;font-weight:bold}</style></head><body>"
        html += "<h2 style='text-align:center;color:#f3ba2f'>V120 BINANCE TP 0.3 BASE FIX</h2>"
        html += "<div class='circle-wrap'><svg width='210' height='210'><circle class='bg' cx='105' cy='105' r='90'></circle><circle id='pc' class='prog' cx='105' cy='105' r='90' stroke-dasharray='565' stroke-dashoffset='565'></circle></svg><div class='center'><div id='totalBig' style='font-size:30px;font-weight:bold'>$0</div><div id='progTxt' style='font-size:11px;color:#8aa'>DIA</div><div id='tpTxt' style='font-size:11px;color:#00ff88'>TP 0.3%</div></div></div>"
        html += "<div class='card'><div id='formula'></div></div>"
        html += "<div class='card' style='border:2px solid #00ff88'><b>TP MANUAL BASE 0.3%</b><br><br><input id='tpInput' class='input-tp' type='number' step='0.05' value='0.30'> <button class='btn tp' onclick='setTP()'>APLICAR</button> <span id='tpActual'></span><br><br><button class='btn tp' id='b03' onclick='apiTP(0.3)'>0.3% BASE</button><button class='btn tp' id='b04' onclick='apiTP(0.4)'>0.4%</button><button class='btn tp' id='b05' onclick='apiTP(0.5)'>0.5%</button><button class='btn tp' id='b06' onclick='apiTP(0.6)'>0.6% MAX</button></div>"
        html += "<div class='card'>AUTO: <button class='btn on' onclick='api(\"auto\")'>ON/OFF</button> <span id='autoSt'></span> | MAX: <button class='btn off' onclick='api(\"max?val=2\")'>2</button><button class='btn off' onclick='api(\"max?val=5\")'>5</button><button class='btn off' onclick='api(\"max?val=8\")'>8</button><button class='btn off' onclick='api(\"max?val=10\")'>10</button></div>"
        html += "<div class='card'>MONEDAS:<div id='mons'></div></div><div class='card'>COMPRAR:<div id='comprarBtns'></div></div><div id='bolas'></div>"
        html += "<script>async function load(){let r=await fetch('/api/data');let d=await r.json();document.getElementById('totalBig').innerText='$'+d.total.toFixed(0);document.getElementById('formula').innerHTML='BASE $'+d.config.BASE+' + ACUM $'+d.config.ACUMULADO.toFixed(2)+' + FLOT $'+d.flotante.toFixed(2)+' = <b>TOTAL $'+d.total.toFixed(2)+'</b><br>BAL $'+d.balance.toFixed(2)+' | BOLAS '+d.bolas.length+'/'+d.config.BOLAS_MAX+' VEND '+d.vendibles;document.getElementById('progTxt').innerText='DIA '+new Date().getDate()+'/30 '+d.progreso.toFixed(1)+'%';document.getElementById('tpTxt').innerText='TP '+d.config.TP_PCT+'% Neto '+(d.config.TP_PCT-d.config.FEES_PCT).toFixed(2)+'%';document.getElementById('tpActual').innerText='ACTUAL '+d.config.TP_PCT+'%';document.getElementById('autoSt').innerText=d.config.AUTO?'ON':'OFF';let circ=565-(565*d.progreso/100);document.getElementById('pc').style.strokeDashoffset=circ;let m='';for(let k in d.monedas){m+='<button class=\"btn '+(d.monedas[k]?'on':'off')+'\" onclick=\"api(\\'moneda?m='+k+'\\')\">'+k+'</button>'}document.getElementById('mons').innerHTML=m;let c='';for(let k in d.monedas){if(d.monedas[k]){c+='<button class=\"btn on\" onclick=\"api(\\'comprar?m='+k+'\\')\">COMPRAR '+k+'</button>'}}document.getElementById('comprarBtns').innerHTML=c;let b='';d.bolas.forEach(x=>{b+='<div class=\"card '+(x.neto>=d.config.TP_PCT?'verde':'rojo')+'\"><b>'+x.moneda+'</b> '+x.compra+' -> '+x.actual.toFixed(4)+' Neto '+x.neto.toFixed(2)+'% $'+x.usd.toFixed(2)+' <button class=\"btn off\" onclick=\"api(\\'vender?id='+x.id+'\\')\">VENDER</button></div>'});document.getElementById('bolas').innerHTML=b;}async function api(u){await fetch('/api/'+u);load();}async function apiTP(v){await fetch('/api/tp?val='+v);load();}async function setTP(){let v=document.getElementById('tpInput').value;await fetch('/api/tp?val='+v);load();}load();setInterval(load,4000);</script></body></html>"
        return html
    except Exception as e:
        print(traceback.format_exc(), flush=True)
        return "Error "+str(e),500

@app.route('/api/data')
def data():
    bal,flot,total,prog,vend=get_stats()
    return jsonify({"balance":bal,"flotante":flot,"total":total,"progreso":prog,"vendibles":vend,"config":CONFIG,"bolas":bolas,"monedas":MONEDAS})

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

@app.route('/api/moneda')
def mon():
    m=request.args.get('m')
    if m in MONEDAS: MONEDAS[m]=not MONEDAS[m]
    return "ok"

@app.route('/api/comprar')
def comprar():
    m=request.args.get('m','BTC')
    comprar_bola(m)
    return "ok"

@app.route('/api/vender')
def vender():
    try:
        vender_bola(int(request.args.get('id')))
    except: pass
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
        bal,flot,total,prog,vend=get_stats()
        if txt=="DASHBOARD" or txt=="/START" or txt=="START" or txt=="WEB" or txt=="BALANCE":
            t="DASHBOARD BINANCE TP 0.3% BASE\nTOTAL $"+str(round(total,2))+" BAL $"+str(round(bal,2))+" FLOT $"+str(round(flot,2))+"\nTP "+str(CONFIG["TP_PCT"])+"% Neto "+str(round(CONFIG["TP_PCT"]-0.10,2))+"%\nBOLAS "+str(len(bolas))+"/"+str(CONFIG["BOLAS_MAX"])+" VEND "+str(vend)+"\nAbre Dashboard:\n"+URL
            enviar_solo_dashboard(cid,t)
        else:
            t="Usa DASHBOARD:\n"+URL
            enviar_solo_dashboard(cid,t)
    except Exception as e:
        print("ERR WH "+traceback.format_exc(), flush=True)
    return "ok",200

if TOKEN:
    try:
        requests.get("https://api.telegram.org/bot"+TOKEN+"/deleteWebhook?drop_pending_updates=true", timeout=5)
        requests.get("https://api.telegram.org/bot"+TOKEN+"/setWebhook?url="+URL, timeout=5)
        print("WEBHOOK OK", flush=True)
    except Exception as e:
        print("ERR WEBHOOK "+str(e), flush=True)

print("V120 LISTO", flush=True)
app.run(host='0.0.0.0', port=int(os.environ.get("PORT","10000")))
