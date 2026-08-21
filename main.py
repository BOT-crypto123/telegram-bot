import os, sys, requests, threading, time, traceback
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V123 DUAL USD/MXN 500 USD", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {"BASE_USD":500.0,"ACUMULADO_USD":16.20,"FEES_PCT":0.10,"TP_PCT":0.30,"AUTO":True,"BOLAS_MAX":10,"COSTO_BOLA_USD":52.89,"RATE_MXN":19.50}
MONEDAS = {"BTC":True,"ETH":True,"XRP":True,"SOL":True,"DOGE":True,"ADA":True,"AVAX":True,"BNB":True}
bolas = [
  {"id":1,"moneda":"XRP","compra":2.85,"costo_usd":52.89,"actual":2.85,"neto":0,"usd":0},
  {"id":2,"moneda":"ETH","compra":2450.5,"costo_usd":52.89,"actual":2450.5,"neto":0,"usd":0}
]
historial = []
PRECIOS = {}

def get_rate_mxn():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN", timeout=4)
        p = float(r.json()['price'])
        if p>10 and p<30:
            CONFIG["RATE_MXN"]=p
            return p
    except: pass
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDMXN", timeout=4)
        p = float(r.json()['price'])
        if p>10:
            CONFIG["RATE_MXN"]=p
            return p
    except: pass
    return CONFIG["RATE_MXN"]

def get_precio(moneda):
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=" + moneda + "USDT", timeout=4)
        p = float(r.json()['price'])
        PRECIOS[moneda]=p
        return p
    except:
        return PRECIOS.get(moneda,0)

def calc(e,a,c_usd):
    if not e or a==0: return 0,0,0
    bruto=((a-e)/e)*100
    neto=bruto-CONFIG["FEES_PCT"]
    usd=c_usd*(neto/100)
    return bruto,neto,usd

def get_stats():
    rate = get_rate_mxn()
    flot_usd=0;vend=0
    for b in bolas:
        p=get_precio(b["moneda"])
        if p>0: b["actual"]=p
        _,neto,usd=calc(b["compra"],b["actual"],b["costo_usd"])
        b["neto"]=neto; b["usd"]=usd; b["mxn"]=usd*rate
        flot_usd+=usd
        if neto>=CONFIG["TP_PCT"]: vend+=1
    bal_usd=CONFIG["BASE_USD"]+CONFIG["ACUMULADO_USD"]
    total_usd=bal_usd+flot_usd
    prog=(datetime.now().day/30)*100
    return bal_usd,flot_usd,total_usd,prog,vend,rate

def comprar_bola(moneda):
    if len(bolas)>=CONFIG["BOLAS_MAX"]: return None
    for x in bolas:
        if x["moneda"]==moneda: return None
    p=get_precio(moneda)
    if p==0: return None
    n={"id":int(time.time()),"moneda":moneda,"compra":p,"costo_usd":CONFIG["COSTO_BOLA_USD"],"actual":p,"neto":0,"usd":0,"mxn":0}
    bolas.append(n)
    return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if b["id"]==id_bola:
            CONFIG["ACUMULADO_USD"]+=b["usd"]
            historial.insert(0,{"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"neto":round(b["neto"],2),"usd":round(b["usd"],2),"mxn":round(b["mxn"],2)})
            bolas.remove(b)
            return b
    return None

def tabla_por_moneda():
    stats=defaultdict(lambda: {"entradas":0,"ganadas":0,"total_usd":0.0,"total_mxn":0.0})
    for h in historial:
        m=h["moneda"]
        stats[m]["entradas"]+=1
        if h["usd"]>0: stats[m]["ganadas"]+=1
        stats[m]["total_usd"]+=h["usd"]
        stats[m]["total_mxn"]+=h["mxn"]
    for b in bolas:
        stats[b["moneda"]]["entradas"]+=1
    return stats

def enviar_solo_dashboard(cid, txt):
    try:
        data={"chat_id":cid,"text":txt,"reply_markup":{"keyboard":[["DASHBOARD"]],"resize_keyboard":True,"is_persistent":True}}
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", json=data, timeout=5)
    except: pass

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    try:
        html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V123 DUAL</title>"
        html += "<style>body{background:#0a0e1a;color:#fff;font-family:Arial;padding:10px;margin:0}.card{background:#121a2b;border-radius:14px;padding:12px;margin:10px 0;border:1px solid #222}.btn{padding:9px 13px;border-radius:10px;border:none;margin:4px;font-weight:bold}.on{background:#f3ba2f;color:#000}.off{background:#1e2a44;color:#666}.tp{background:#00ff88;color:#000}.circle-wrap{position:relative;width:240px;height:240px;margin:18px auto}.bg{fill:none;stroke:#1e2a44;stroke-width:14}.prog{fill:none;stroke:#f3ba2f;stroke-width:14;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}.center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}.mxn-big{font-size:36px;color:#00ff88;font-weight:900}.usd-small{font-size:13px;color:#8aa}.acum-mxn{font-size:44px;color:#00ff88;font-weight:900;text-align:center}.acum-usd{font-size:14px;color:#8aa;text-align:center}.table{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}.table th{background:#1a2332;color:#f3ba2f;padding:7px;text-align:left}.table td{padding:6px;border-bottom:1px solid #222}</style></head><body>"
        html += "<h2 style='text-align:center;color:#f3ba2f;margin:6px'>BINANCE 500 USD / MXN REAL</h2>"
        html += "<div class='circle-wrap'><svg width='240' height='240'><circle class='bg' cx='120' cy='120' r='100'></circle><circle id='pc' class='prog' cx='120' cy='120' r='100' stroke-dasharray='628' stroke-dashoffset='628'></circle></svg><div class='center'><div style='font-size:11px;color:#8aa;letter-spacing:2px'>BASE</div><div id='baseMxn' class='mxn-big'>$0 MXN</div><div id='baseUsd' class='usd-small'>$500 USD</div><div id='rateTxt' style='font-size:10px;color:#f3ba2f;margin-top:4px'></div><div id='diaTxt' style='font-size:11px;color:#8aa;margin-top:2px'></div></div></div>"
        html += "<div class='card' style='border:2px solid #00ff88'><div style='text-align:center;color:#8aa;font-size:11px;letter-spacing:2px'>ACUMULADO</div><div id='acumMxn' class='acum-mxn'>$0 MXN</div><div id='acumUsd' class='acum-usd'>$0 USD</div><div id='totalLine' style='text-align:center;color:#555;font-size:11px;margin-top:6px'></div></div>"
        html += "<div class='card' style='border:1px solid #00ff88'><b>TP BASE 0,3% BINANCE</b> <span style='font-size:11px;color:#8aa'>Fees 0,10% Neto 0,20%</span><br><br><input id='tpInput' style='background:#000;color:#00ff88;border:2px solid #f3ba2f;border-radius:8px;padding:6px;width:65px;text-align:center;font-weight:bold' type='number' step='0.05' value='0.30'> <button class='btn tp' onclick='setTP()'>APLICAR</button> <span id='tpActual' style='font-size:12px;color:#f3ba2f'></span><br><br><button class='btn tp' onclick='apiTP(0.3)'>0,3% BASE</button><button class='btn tp' onclick='apiTP(0.4)'>0,4%</button><button class='btn tp' onclick='apiTP(0.5)'>0,5%</button><button class='btn tp' onclick='apiTP(0.6)'>0,6% MAX</button></div>"
        html += "<div class='card'>AUTO <button class='btn on' onclick='api(\"auto\")'>ON/OFF</button> <span id='autoSt'></span> | MAX <button class='btn off' onclick='api(\"max?val=2\")'>2</button><button class='btn off' onclick='api(\"max?val=5\")'>5</button><button class='btn off' onclick='api(\"max?val=8\")'>8</button><button class='btn off' onclick='api(\"max?val=10\")'>10</button></div>"
        html += "<div class='card'>MONEDAS:<div id='mons'></div></div><div class='card'>COMPRAR:<div id='comprarBtns'></div></div>"
        html += "<div class='card'><b>ABIERTAS (USD chiquito / MXN grande)</b><div id='bolas'></div></div>"
        html += "<div class='card'><b>TABLA POR MONEDA - DUAL</b><table class='table'><thead><tr><th>MONEDA</th><th>ENTRADAS</th><th>GANADAS</th><th>USD</th><th>MXN</th><th>% WIN</th></tr></thead><tbody id='tablaMon'></tbody></table></div>"
        html += "<div class='card'><b>HISTORIAL DUAL</b><table class='table'><thead><tr><th>FECHA</th><th>MON</th><th>NETO</th><th>USD</th><th>MXN</th></tr></thead><tbody id='hist'></tbody></table></div>"
        html += "<script>async function load(){let r=await fetch('/api/data');let d=await r.json();"
        html += "document.getElementById('baseMxn').innerText='$'+(d.config.BASE_USD*d.rate).toFixed(0)+' MXN';"
        html += "document.getElementById('baseUsd').innerText='$'+d.config.BASE_USD.toFixed(2)+' USD';"
        html += "document.getElementById('rateTxt').innerText='1 USDT = $'+d.rate.toFixed(2)+' MXN (Binance)';"
        html += "document.getElementById('diaTxt').innerText='DIA '+new Date().getDate()+'/30 '+d.progreso.toFixed(1)+'% TP '+d.config.TP_PCT+'%';"
        html += "document.getElementById('acumMxn').innerText='$'+(d.config.ACUMULADO_USD*d.rate).toFixed(2)+' MXN';"
        html += "document.getElementById('acumUsd').innerText='$'+d.config.ACUMULADO_USD.toFixed(2)+' USD';"
        html += "document.getElementById('totalLine').innerText='TOTAL $'+d.total_usd.toFixed(2)+' USD / $'+(d.total_usd*d.rate).toFixed(2)+' MXN | FLOT $'+d.flotante_usd.toFixed(2)+' USD / $'+(d.flotante_usd*d.rate).toFixed(2)+' MXN';"
        html += "document.getElementById('tpActual').innerText='TP '+d.config.TP_PCT+'%';"
        html += "document.getElementById('autoSt').innerText=d.config.AUTO?'ON':'OFF';"
        html += "let circ=628-(628*d.progreso/100);document.getElementById('pc').style.strokeDashoffset=circ;"
        html += "let m='';for(let k in d.monedas){m+='<button class=\"btn '+(d.monedas[k]?'on':'off')+'\" onclick=\"api(\\'moneda?m='+k+'\\')\">'+k+'</button>'}document.getElementById('mons').innerHTML=m;"
        html += "let c='';for(let k in d.monedas){if(d.monedas[k]){c+='<button class=\"btn on\" onclick=\"api(\\'comprar?m='+k+'\\')\">COMPRAR '+k+'</button>'}}document.getElementById('comprarBtns').innerHTML=c;"
        html += "let b='';d.bolas.forEach(x=>{b+='<div style=\"padding:6px 0;border-bottom:1px solid #222\"><b>'+x.moneda+'</b> Neto '+x.neto.toFixed(2)+'% <span style=\"color:#00ff88;font-weight:bold\">$'+(x.usd*d.rate).toFixed(2)+' MXN</span> <span style=\"color:#8aa;font-size:11px\">$'+x.usd.toFixed(2)+' USD</span> '+(x.neto>=d.config.TP_PCT?'✅':'🔴')+' <button class=\"btn off\" style=\"float:right\" onclick=\"api(\\'vender?id='+x.id+'\\')\">VENDER</button></div>'});document.getElementById('bolas').innerHTML=b||'Sin posiciones';"
        html += "let tm='';for(let mon in d.tabla){let s=d.tabla[mon];let win=s.entradas?((s.ganadas/s.entradas)*100).toFixed(0):0;tm+='<tr><td><b>'+mon+'</b></td><td>'+s.entradas+'</td><td style=\"color:#00ff88\">'+s.ganadas+'</td><td style=\"font-size:10px;color:#8aa\">$'+s.total_usd.toFixed(2)+'</td><td style=\"color:#00ff88\">$'+s.total_mxn.toFixed(2)+'</td><td>'+win+'%</td></tr>';}document.getElementById('tablaMon').innerHTML=tm||'<tr><td colspan=6>Sin datos</td></tr>';"
        html += "let h='';d.historial.forEach(x=>{h+='<tr><td>'+x.fecha+'</td><td>'+x.moneda+'</td><td>'+x.neto+'%</td><td style=\"font-size:10px;color:#8aa\">$'+x.usd+'</td><td style=\"color:#00ff88\">$'+x.mxn+'</td></tr>';});document.getElementById('hist').innerHTML=h||'<tr><td colspan=5>Sin historial</td></tr>';"
        html += "}"
        html += "async function api(u){await fetch('/api/'+u);load();}async function apiTP(v){await fetch('/api/tp?val='+v);load();}async function setTP(){let v=document.getElementById('tpInput').value;await fetch('/api/tp?val='+v);load();}load();setInterval(load,5000);"
        html += "</script></body></html>"
        return html
    except Exception as e:
        print(traceback.format_exc(), flush=True)
        return "Error "+str(e),500

@app.route('/api/data')
def data():
    bal_usd,flot_usd,total_usd,prog,vend,rate=get_stats()
    return jsonify({"balance_usd":bal_usd,"flotante_usd":flot_usd,"total_usd":total_usd,"balance":bal_usd,"flotante":flot_usd,"total":total_usd,"progreso":prog,"vendibles":vend,"config":CONFIG,"bolas":bolas,"monedas":MONEDAS,"historial":historial,"tabla":tabla_por_moneda(),"rate":rate})

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
        bal_usd,flot_usd,total_usd,prog,vend,rate=get_stats()
        if txt=="DASHBOARD" or txt=="/START" or txt=="START":
            t="DASHBOARD DUAL 500 USD\nBASE $500 USD = $"+str(round(CONFIG["BASE_USD"]*rate,0))+" MXN\nACUM $"+str(round(CONFIG["ACUMULADO_USD"],2))+" USD = $"+str(round(CONFIG["ACUMULADO_USD"]*rate,2))+" MXN\nRate $"+str(round(rate,2))+" MXN\n"+URL
            enviar_solo_dashboard(cid,t)
        else:
            enviar_solo_dashboard(cid,"DASHBOARD:\n"+URL)
    except Exception as e:
        print(traceback.format_exc(), flush=True)
    return "ok",200

if TOKEN:
    try:
        requests.get("https://api.telegram.org/bot"+TOKEN+"/deleteWebhook?drop_pending_updates=true", timeout=5)
        requests.get("https://api.telegram.org/bot"+TOKEN+"/setWebhook?url="+URL, timeout=5)
        print("WEBHOOK OK", flush=True)
    except Exception as e:
        print("ERR WEBHOOK "+str(e), flush=True)

print("V123 DUAL LISTO", flush=True)
app.run(host='0.0.0.0', port=int(os.environ.get("PORT","10000")))
