import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V136 MISMA LOGICA FIX FINAL", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {
    "BASE_USD": 500.0,
    "BASE_MXN": 9750.0,
    "ACUMULADO_MXN": 310.0,
    "ACUMULADO_USD": 15.90,
    "FEE_ENTRY_PCT": 0.10,
    "FEE_EXIT_PCT": 0.10,
    "TP_PCT": 0.30,
    "AUTO": True,
    "BOLAS_MAX": 6,
    "RATE_MXN": 19.50
}
MONEDAS = {"ADA":True,"AVAX":True,"BNB":True,"BTC":False,"DOGE":True,"ETH":True,"SOL":True,"XRP":True}
bolas = []
historial = []
PRECIOS = {}

def send_tg(text):
    global CHAT_ID
    if not TOKEN or not CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":text}, timeout=5)
    except:
        pass

def get_rate_mxn():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN", timeout=4)
        p = float(r.json()['price'])
        if 10 < p < 30:
            CONFIG["RATE_MXN"]=p
            CONFIG["BASE_MXN"]=CONFIG["BASE_USD"]*p
            return p
    except:
        pass
    return CONFIG["RATE_MXN"]

def get_precio(moneda):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={moneda}USDT", timeout=4)
        p = float(r.json()['price'])
        PRECIOS[moneda]=p
        return p
    except:
        return PRECIOS.get(moneda, 0)

def get_total_mxn():
    return CONFIG["BASE_MXN"] + CONFIG["ACUMULADO_MXN"]

def get_costo_mxn():
    return get_total_mxn() / CONFIG["BOLAS_MAX"]

def get_costo_usd():
    return get_costo_mxn() / CONFIG["RATE_MXN"]

def calc_desglose(entrada, salida, costo_usd, rate):
    if not entrada or salida==0:
        return {}
    pct_bruto = ((salida - entrada) / entrada) * 100
    bruta_usd = costo_usd * (pct_bruto/100)
    com_entry_usd = costo_usd * (CONFIG["FEE_ENTRY_PCT"]/100)
    com_exit_usd = (costo_usd + bruta_usd) * (CONFIG["FEE_EXIT_PCT"]/100)
    com_total_usd = com_entry_usd + com_exit_usd
    neta_usd = bruta_usd - com_total_usd
    pct_neto = (neta_usd / costo_usd) * 100
    return {
        "pct_bruto": pct_bruto,
        "pct_neto": pct_neto,
        "bruta_usd": bruta_usd,
        "bruta_mxn": bruta_usd * rate,
        "com_entry_usd": com_entry_usd,
        "com_entry_mxn": com_entry_usd * rate,
        "com_exit_usd": com_exit_usd,
        "com_exit_mxn": com_exit_usd * rate,
        "com_total_usd": com_total_usd,
        "com_total_mxn": com_total_usd * rate,
        "neta_usd": neta_usd,
        "neta_mxn": neta_usd * rate
    }

def get_stats():
    rate = get_rate_mxn()
    CONFIG["ACUMULADO_MXN"] = CONFIG["ACUMULADO_USD"] * rate
    CONFIG["BASE_MXN"] = CONFIG["BASE_USD"] * rate
    flot_usd=0
    flot_mxn=0
    vend=0
    for b in bolas:
        p=get_precio(b["moneda"])
        if p>0:
            b["actual"]=p
        d = calc_desglose(b["compra"], b["actual"], b["costo_usd"], rate)
        b.update(d)
        b["usd"]=d.get("neta_usd",0)
        b["mxn"]=d.get("neta_mxn",0)
        b["neto"]=d.get("pct_neto",0)
        flot_usd+=b["usd"]
        flot_mxn+=b["mxn"]
        if b["neto"]>=CONFIG["TP_PCT"]:
            vend+=1
    total_mxn=get_total_mxn()
    total_usd=total_mxn/rate
    prog=(datetime.now().day/30)*100
    return total_usd,total_mxn,flot_usd,flot_mxn,prog,vend,rate,get_costo_usd(),get_costo_mxn()

def comprar_bola(moneda):
    if len(bolas)>=CONFIG["BOLAS_MAX"]:
        return None
    for x in bolas:
        if x["moneda"]==moneda:
            return None
    p=get_precio(moneda)
    if p==0:
        return None
    n={"id":int(time.time()*1000),"moneda":moneda,"compra":p,"costo_usd":get_costo_usd(),"costo_mxn":get_costo_mxn(),"actual":p}
    bolas.append(n)
    return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if b["id"]==id_bola:
            CONFIG["ACUMULADO_USD"]+=b["neta_usd"]
            CONFIG["ACUMULADO_MXN"]+=b["neta_mxn"]
            h={"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"costo_mxn":round(b["costo_mxn"],2),"costo_usd":round(b["costo_usd"],2),"com_entry_mxn":round(b["com_entry_mxn"],2),"com_entry_usd":round(b["com_entry_usd"],4),"com_exit_mxn":round(b["com_exit_mxn"],2),"com_exit_usd":round(b["com_exit_usd"],4),"com_total_mxn":round(b["com_total_mxn"],2),"com_total_usd":round(b["com_total_usd"],4),"bruta_mxn":round(b["bruta_mxn"],2),"bruta_usd":round(b["bruta_usd"],4),"neta_mxn":round(b["neta_mxn"],2),"neta_usd":round(b["neta_usd"],4),"pct_bruto":round(b["pct_bruto"],3),"pct_neto":round(b["pct_neto"],3)}
            historial.insert(0,h)
            bolas.remove(b)
            if b["neta_usd"]>0:
                send_tg(f"CIERRE GANADOR\n{b['moneda']} NETO {b['pct_neto']:.2f}% (BRUTO {b['pct_bruto']:.2f}%)\nNETA: ${b['neta_mxn']:.2f} MXN (${b['neta_usd']:.2f} USD)")
            return b
    return None

def tabla_por_moneda():
    stats=defaultdict(lambda: {"entradas":0,"ganadas":0,"total_usd":0.0,"total_mxn":0.0,"com_mxn":0.0,"bruta_mxn":0.0})
    for h in historial:
        m=h["moneda"]
        stats[m]["entradas"]+=1
        if h["neta_mxn"]>0:
            stats[m]["ganadas"]+=1
        stats[m]["total_usd"]+=h["neta_usd"]
        stats[m]["total_mxn"]+=h["neta_mxn"]
        stats[m]["com_mxn"]+=h["com_total_mxn"]
        stats[m]["bruta_mxn"]+=h["bruta_mxn"]
    for b in bolas:
        stats[b["moneda"]]["entradas"]+=1
    return stats

def loop_auto():
    while True:
        try:
            if CONFIG["AUTO"]:
                get_stats()
                for b in bolas[:]:
                    if b.get("pct_neto",0)>=CONFIG["TP_PCT"]:
                        vender_bola(b["id"])
                if len(bolas)<CONFIG["BOLAS_MAX"]:
                    disponibles=[]
                    for m, on in MONEDAS.items():
                        if not on:
                            continue
                        ocupado=False
                        for x in bolas:
                            if x["moneda"]==m:
                                ocupado=True
                                break
                        if not ocupado:
                            disponibles.append(m)
                    if len(disponibles)>0:
                        elegir=random.choice(disponibles)
                        comprar_bola(elegir)
        except Exception:
            print(traceback.format_exc(), flush=True)
        time.sleep(12)

threading.Thread(target=loop_auto, daemon=True).start()
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MAQUINA DE HACER DINERO</title>
<style>
body{background:#061126;color:#fff;font-family:Arial;padding:10px;margin:0}
.titulo{font-size:26px;text-align:center;color:#FFD700;margin:12px 0 4px 0;font-weight:900}
.subtitulo{font-size:10px;color:#8aa;text-align:center;letter-spacing:4px;margin-bottom:12px}
.card{background:#0c1e3a;border-radius:16px;padding:14px;margin:12px 0;border:1px solid #14365f}
.btn{padding:9px 14px;border-radius:10px;border:none;margin:4px;font-weight:bold;cursor:pointer}
.on{background:#0ea5e9;color:#fff}.off{background:#0f284a;color:#5a7aa5}.tp{background:#00e5ff;color:#000;font-weight:900}
.circle-wrap{position:relative;width:270px;height:270px;margin:18px auto}
.bg{fill:none;stroke:#0f284a;stroke-width:14}.prog{fill:none;stroke:#FFD700;stroke-width:14;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}
.center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}
.mxn-big{font-size:44px;color:#00ff88;font-weight:900;line-height:1}
.usd-small{font-size:11px;color:#5a7aa5;margin-top:4px}
.acum-mxn{font-size:48px;color:#00ff88;font-weight:900;text-align:center;line-height:1}
.acum-usd{font-size:13px;color:#5a7aa5;text-align:center}
.table{width:100%;border-collapse:collapse;margin-top:10px;font-size:11px}
.table th{background:#0f284a;color:#FFD700;padding:8px 4px;text-align:center;font-size:9px}
.table td{padding:7px 4px;border-bottom:1px solid #14365f;text-align:center}
.comp{background:#00ff88;color:#000;padding:12px;border-radius:12px;font-weight:900;text-align:center;margin:8px 0;font-size:18px}
.badge-mxn{color:#00ff88;font-weight:900;font-size:13px}.badge-usd{color:#5a7aa5;font-size:10px}.badge-com{color:#ff6b6b;font-size:10px}.badge-bruta{color:#ffd93d;font-weight:700}.scroll{overflow-x:auto}
</style>
</head>
<body>
<div class="titulo">MAQUINA DE HACER DINERO</div>
<div class="subtitulo">SISTEMA COMPUESTO 500 USD - MXN GRANDE</div>
<div class="circle-wrap"><svg width="270" height="270"><circle class="bg" cx="135" cy="135" r="110"></circle><circle id="pc" class="prog" cx="135" cy="135" r="110" stroke-dasharray="691" stroke-dashoffset="691"></circle></svg>
<div class="center"><div style="font-size:9px;color:#8aa;letter-spacing:2px">BASE 500 USD + ACUM</div><div id="baseMxn" class="mxn-big">$0 MXN</div><div id="baseUsd" class="usd-small">$0 USD</div><div id="rateTxt" style="font-size:9px;color:#FFD700;margin-top:6px"></div><div id="diaTxt" style="font-size:10px;color:#5a7aa5;margin-top:2px"></div></div></div>
<div class="card" style="border:2px solid #00ff88"><div style="text-align:center;color:#8aa;font-size:9px;letter-spacing:3px">ACUMULADO NETO REAL</div><div id="acumMxn" class="acum-mxn">$0 MXN</div><div id="acumUsd" class="acum-usd">$0 USD</div><div id="totalLine" style="text-align:center;color:#5a7aa5;font-size:10px;margin-top:6px"></div><div id="costoLine" class="comp"></div><div id="costoUsdLine" style="text-align:center;color:#5a7aa5;font-size:10px"></div><div style="text-align:center;color:#8aa;font-size:9px;margin-top:6px">FEE ENTRADA 0.10% + FEE SALIDA 0.10% = 0.20% TOTAL YA DESCONTADO</div></div>
<div class="card" style="border:1px solid #00ff88"><b style="color:#00ff88">TP 0,3% NETO REAL (0,5% BRUTO APROX)</b><br><br><button class="btn tp" onclick="doTP(0.3)">0,3% NETO</button><button class="btn tp" onclick="doTP(0.4)">0,4%</button><button class="btn tp" onclick="doTP(0.5)">0,5%</button><button class="btn tp" onclick="doTP(0.6)">0,6%</button></div>
<div class="card">AUTO <button id="autoBtn" class="btn on" onclick="doApi('auto')">ENCENDIDO</button> <span id="autoSt"></span> | ENTRADAS<br><button class="btn off" onclick="doApi('max?val=2')">2</button><button class="btn off" onclick="doApi('max?val=4')">4</button><button class="btn off" onclick="doApi('max?val=6')">6</button><button class="btn off" onclick="doApi('max?val=8')">8</button><button class="btn off" onclick="doApi('max?val=10')">10</button><div id="ejemploDiv" style="font-size:10px;color:#00ff88;margin-top:8px"></div></div>
<div class="card">MONEDAS ACTIVAS:<div id="mons"></div></div>
<div class="card"><b style="color:#00ff88">ABIERTAS - CON DESGLOSE</b><div id="bolas"></div></div>
<div class="card"><b style="color:#FFD700">RESUMEN POR MONEDA - NETA + COMISIONES</b><div class="scroll"><table class="table"><thead><tr><th>MON</th><th>ENT</th><th>GAN</th><th>BRUTA MXN</th><th>COMIS MXN</th><th>NETA MXN</th><th>USD ch</th><th>WIN</th></tr></thead><tbody id="tablaMon"></tbody></table></div></div>
<div class="card"><b style="color:#00ff88">HISTORIAL COMPLETO - DESGLOSE REAL BINANCE</b><div class="scroll"><table class="table"><thead><tr><th>FECHA</th><th>MON</th><th>ENT/SAL</th><th>COSTO</th><th>COM ENT</th><th>COM SAL</th><th>COM TOT</th><th>BRUTA</th><th>NETA MXN</th><th>USD ch</th><th>%</th></tr></thead><tbody id="hist"></tbody></table></div></div>
<script>
async function load(){
  let r=await fetch("/api/data");
  let d=await r.json();
  document.getElementById("baseMxn").innerText="$"+d.total_mxn.toFixed(2)+" MXN";
  document.getElementById("baseUsd").innerText="$"+d.total_usd.toFixed(2)+" USD";
  document.getElementById("rateTxt").innerText="1 USDT = $"+d.rate.toFixed(2)+" MXN";
  document.getElementById("diaTxt").innerText="DIA "+new Date().getDate()+"/30 TP "+d.config.TP_PCT+"% NETO";
  document.getElementById("acumMxn").innerText="$"+d.config.ACUMULADO_MXN.toFixed(2)+" MXN";
  document.getElementById("acumUsd").innerText="$"+d.config.ACUMULADO_USD.toFixed(2)+" USD";
  document.getElementById("totalLine").innerText="BASE $"+d.config.BASE_MXN.toFixed(0)+" MXN | FLOT NETO $"+d.flot_mxn.toFixed(2)+" MXN";
  document.getElementById("costoLine").innerText="ENTRADA ACTUAL: $"+d.costo_mxn.toFixed(0)+" MXN";
  document.getElementById("costoUsdLine").innerText="$"+d.costo_usd.toFixed(2)+" USD ch | "+d.config.BOLAS_MAX+" entradas";
  document.getElementById("ejemploDiv").innerText="Ej: $"+d.total_mxn.toFixed(2)+" / "+d.config.BOLAS_MAX+" = $"+d.costo_mxn.toFixed(0)+" MXN por bola";
  document.getElementById("autoSt").innerText=d.config.AUTO?"TRABAJANDO":"PAUSADO";
  document.getElementById("autoBtn").innerText=d.config.AUTO?"ENCENDIDO":"APAGADO";
  let circ=691-(691*d.progreso/100);
  document.getElementById("pc").style.strokeDashoffset=circ;
  let m="";
  for(let k in d.monedas){
    let cls=d.monedas[k]?"on":"off";
    m+='<button class="btn '+cls+'" onclick="doMoneda(\''+k+'\')">'+k+'</button>';
  }
  document.getElementById("mons").innerHTML=m;
  let b="";
  d.bolas.forEach(function(x){
    b+='<div style="padding:10px 0;border-bottom:1px solid #14365f"><b>'+x.moneda+'</b> '+x.compra.toFixed(4)+' -> '+x.actual.toFixed(4)+'<br>';
    b+='<span style="font-size:10px;color:#5a7aa5">Costo $'+x.costo_mxn.toFixed(0)+' MXN ($'+x.costo_usd.toFixed(2)+')</span><br>';
    b+='<span class="badge-bruta">Bruta $'+(x.bruta_mxn||0).toFixed(2)+'</span> | <span class="badge-com">Comis $'+(x.com_total_mxn||0).toFixed(2)+'</span><br>';
    b+='<span class="badge-mxn">Neta $'+(x.neta_mxn||0).toFixed(2)+' MXN</span> <span class="badge-usd">$'+(x.neta_usd||0).toFixed(2)+' USD</span> | Neto '+(x.pct_neto||0).toFixed(2)+'%</div>';
  });
  document.getElementById("bolas").innerHTML=b||"Limpio - AUTO cazara solo";
  let tm="";
  for(let mon in d.tabla){
    let s=d.tabla[mon];
    let win=s.entradas?((s.ganadas/s.entradas)*100).toFixed(0):0;
    tm+="<tr><td><b>"+mon+"</b></td><td>"+s.entradas+"</td><td style=color:#00ff88>"+s.ganadas+"</td><td><span class=badge-bruta>$"+s.bruta_mxn.toFixed(2)+"</span></td><td><span class=badge-com>$"+s.com_mxn.toFixed(2)+"</span></td><td><span class=badge-mxn>$"+s.total_mxn.toFixed(2)+"</span></td><td><span class=badge-usd>$"+s.total_usd.toFixed(2)+"</span></td><td>"+win+"%</td></tr>";
  }
  document.getElementById("tablaMon").innerHTML=tm||"<tr><td colspan=8>Desde cero</td></tr>";
  let h="";
  d.historial.forEach(function(x){
    h+="<tr><td>"+x.fecha+"</td><td><b>"+x.moneda+"</b></td><td style=font-size:9px>"+x.entrada.toFixed(4)+"<br>-> "+x.salida.toFixed(4)+"</td><td><span style=font-size:9px>$"+x.costo_mxn+"<br><span class=badge-usd>$"+x.costo_usd+"</span></span></td><td><span class=badge-com>$"+x.com_entry_mxn+"<br><span class=badge-usd>$"+x.com_entry_usd+"</span></span></td><td><span class=badge-com>$"+x.com_exit_mxn+"<br><span class=badge-usd>$"+x.com_exit_usd+"</span></span></td><td><span class=badge-com>$"+x.com_total_mxn+"<br><span class=badge-usd>$"+x.com_total_usd+"</span></span></td><td><span class=badge-bruta>$"+x.bruta_mxn+"<br><span class=badge-usd>$"+x.bruta_usd+"</span></span></td><td><span class=badge-mxn>$"+x.neta_mxn+"</span></td><td><span class=badge-usd>$"+x.neta_usd+"</span></td><td>"+x.pct_neto+"%<br><span style=font-size:8px;color:#5a7aa5>"+x.pct_bruto+"% br</span></td></tr>";
  });
  document.getElementById("hist").innerHTML=h||"<tr><td colspan=11>Desde cero $310 MXN</td></tr>";
}
async function doApi(u){await fetch("/api/"+u);load();}
async function doTP(v){await fetch("/api/tp?val="+v);load();}
async function doMoneda(m){await fetch("/api/moneda?m="+m);load();}
load();
setInterval(load,5000);
</script>
</body>
</html>
'''

@app.route('/api/data')
def data():
    total_usd,total_mxn,flot_usd,flot_mxn,prog,vend,rate,costo_usd,costo_mxn=get_stats()
    return jsonify({"total_usd":total_usd,"total_mxn":total_mxn,"flot_usd":flot_usd,"flot_mxn":flot_mxn,"progreso":prog,"vendibles":vend,"config":CONFIG,"bolas":bolas,"monedas":MONEDAS,"historial":historial,"tabla":tabla_por_moneda(),"rate":rate,"costo_usd":costo_usd,"costo_mxn":costo_mxn})

@app.route('/api/tp')
def tp():
    try:
        CONFIG["TP_PCT"]=round(max(0.1,min(2.0,float(request.args.get('val','0.3')))),2)
    except:
        pass
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
    if m in MONEDAS:
        MONEDAS[m]=not MONEDAS[m]
    return "ok"

@app.route('/', methods=['POST'])
def wh():
    global CHAT_ID
    try:
        j=request.get_json(force=True, silent=True)
        if not j:
            return "ok",200
        msg=j.get("message",{})
        cid=msg.get("chat",{}).get("id")
        if cid:
            CHAT_ID=cid
        get_stats()
        t=f"MAQUINA DE HACER DINERO\nTotal: ${get_total_mxn():.2f} MXN\nEntrada: ${get_costo_mxn():.0f} MXN\nAcum: ${CONFIG['ACUMULADO_MXN']:.2f} MXN\nFee 0.10%+0.10% descontado\n{URL}"
        try:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":cid,"text":t,"reply_markup":{"keyboard":[["DASHBOARD"]],"resize_keyboard":True,"is_persistent":True}}, timeout=5)
        except:
            pass
    except:
        print(traceback.format_exc(), flush=True)
    return "ok",200

if TOKEN:
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL}", timeout=5)
    except:
        pass

app.run(host='0.0.0.0', port=int(os.environ.get("PORT","10000")))
