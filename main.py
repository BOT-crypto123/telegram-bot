import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V141 BASE 500 USD REAL", flush=True)

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

def get_rate_mxn():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN", timeout=4)
        p = float(r.json()['price'])
        if 10 < p < 30:
            CONFIG["RATE_MXN"]=p
            CONFIG["BASE_MXN"]=CONFIG["BASE_USD"]*p
            return p
    except: pass
    return CONFIG["RATE_MXN"]

def get_precio(moneda):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={moneda}USDT", timeout=4)
        p = float(r.json()['price']); PRECIOS[moneda]=p; return p
    except: return PRECIOS.get(moneda, 0)

def get_total_mxn(): return CONFIG["BASE_MXN"] + CONFIG["ACUMULADO_MXN"]
def get_costo_mxn(): return get_total_mxn() / CONFIG["BOLAS_MAX"]
def get_costo_usd(): return get_costo_mxn() / CONFIG["RATE_MXN"]

def calc_desglose(entrada, salida, costo_usd, rate):
    if not entrada or salida==0: return {}
    pct_bruto = ((salida - entrada) / entrada) * 100
    bruta_usd = costo_usd * (pct_bruto/100)
    com_entry_usd = costo_usd * (CONFIG["FEE_ENTRY_PCT"]/100)
    com_exit_usd = (costo_usd + bruta_usd) * (CONFIG["FEE_EXIT_PCT"]/100)
    com_total_usd = com_entry_usd + com_exit_usd
    neta_usd = bruta_usd - com_total_usd
    pct_neto = (neta_usd / costo_usd) * 100
    return {"pct_bruto":pct_bruto,"pct_neto":pct_neto,"bruta_usd":bruta_usd,"bruta_mxn":bruta_usd*rate,"com_total_usd":com_total_usd,"com_total_mxn":com_total_usd*rate,"neta_usd":neta_usd,"neta_mxn":neta_usd*rate}

def get_stats():
    rate = get_rate_mxn()
    CONFIG["ACUMULADO_MXN"] = CONFIG["ACUMULADO_USD"] * rate
    CONFIG["BASE_MXN"] = CONFIG["BASE_USD"] * rate
    flot_usd=0; flot_mxn=0
    for b in bolas:
        p=get_precio(b["moneda"])
        if p>0: b["actual"]=p
        d = calc_desglose(b["compra"], b["actual"], b["costo_usd"], rate)
        b.update(d); b["usd"]=d.get("neta_usd",0); b["mxn"]=d.get("neta_mxn",0); b["neto"]=d.get("pct_neto",0)
        flot_usd+=b["usd"]; flot_mxn+=b["mxn"]
    total_mxn=get_total_mxn(); total_usd=total_mxn/rate; prog=(datetime.now().day/30)*100
    return total_usd,total_mxn,flot_usd,flot_mxn,prog,rate,get_costo_usd(),get_costo_mxn()

def comprar_bola(moneda):
    if len(bolas)>=CONFIG["BOLAS_MAX"]: return None
    for x in bolas:
        if x["moneda"]==moneda: return None
    p=get_precio(moneda)
    if p==0: return None
    n={"id":int(time.time()*1000),"moneda":moneda,"compra":p,"costo_usd":get_costo_usd(),"costo_mxn":get_costo_mxn(),"actual":p}
    bolas.append(n); return n

def vender_bola(id_bola):
    for b in bolas[:]:
        if str(b["id"])==str(id_bola):
            CONFIG["ACUMULADO_USD"]+=b["neta_usd"]; CONFIG["ACUMULADO_MXN"]+=b["neta_mxn"]
            h={"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"costo_mxn":round(b["costo_mxn"],2),"neta_mxn":round(b["neta_mxn"],2),"neta_usd":round(b["neta_usd"],4),"pct_bruto":round(b["pct_bruto"],3),"pct_neto":round(b["pct_neto"],3)}
            historial.insert(0,h); bolas.remove(b); return b
    return None

def resumen_total():
    if not historial: return {"total_entradas":0,"ganadas":0,"perdidas":0,"total_mxn":0,"total_usd":0,"mejor_moneda":"","peor_moneda":"","mas_entradas":""}
    total_mxn=sum(h["neta_mxn"] for h in historial)
    total_usd=sum(h["neta_usd"] for h in historial)
    ganadas=len([h for h in historial if h["neta_mxn"]>0])
    perdidas=len([h for h in historial if h["neta_mxn"]<=0])
    conteo=Counter(h["moneda"] for h in historial)
    mas_entradas=conteo.most_common(1)[0][0] if conteo else "-"
    por_moneda=defaultdict(float)
    for h in historial: por_moneda[h["moneda"]]+=h["neta_mxn"]
    mejor=max(por_moneda, key=por_moneda.get) if por_moneda else "-"
    peor=min(por_moneda, key=por_moneda.get) if por_moneda else "-"
    return {"total_entradas":len(historial),"ganadas":ganadas,"perdidas":perdidas,"total_mxn":total_mxn,"total_usd":total_usd,"mas_entradas":mas_entradas,"mejor_moneda":mejor,"peor_moneda":peor,"conteo":dict(conteo),"por_moneda":dict(por_moneda)}

def tabla_por_moneda():
    stats=defaultdict(lambda: {"entradas":0,"ganadas":0,"perdidas":0,"total_mxn":0.0,"total_usd":0.0})
    for h in historial:
        m=h["moneda"]; stats[m]["entradas"]+=1
        if h["neta_mxn"]>0: stats[m]["ganadas"]+=1
        else: stats[m]["perdidas"]+=1
        stats[m]["total_mxn"]+=h["neta_mxn"]; stats[m]["total_usd"]+=h["neta_usd"]
    for b in bolas: stats[b["moneda"]]["entradas"]+=1
    return stats

def loop_auto():
    while True:
        try:
            if CONFIG["AUTO"]:
                get_stats()
                for b in bolas[:]:
                    if b.get("pct_neto",0)>=CONFIG["TP_PCT"]: vender_bola(b["id"])
                if len(bolas)<CONFIG["BOLAS_MAX"]:
                    disp=[]
                    for m, on in MONEDAS.items():
                        if not on: continue
                        ocupado=False
                        for x in bolas:
                            if x["moneda"]==m: ocupado=True; break
                        if not ocupado: disp.append(m)
                    if disp: comprar_bola(random.choice(disp))
        except: print(traceback.format_exc(), flush=True)
        time.sleep(10)

threading.Thread(target=loop_auto, daemon=True).start()
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return '''
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>MAQUINA DE HACER DINERO</title>
<style>
body{background:#061126;color:#fff;font-family:Arial;padding:10px;margin:0}
.titulo{font-size:26px;text-align:center;color:#FFD700;margin:12px 0 4px 0;font-weight:900}
.subtitulo{font-size:9px;color:#8aa;text-align:center;letter-spacing:3px;margin-bottom:12px}
.card{background:#0c1e3a;border-radius:16px;padding:14px;margin:12px 0;border:1px solid #14365f}
.btn{padding:9px 14px;border-radius:10px;border:none;margin:4px;font-weight:bold;cursor:pointer}
.on{background:#0ea5e9;color:#fff}.off{background:#0f284a;color:#5a7aa5}.tp{background:#00e5ff;color:#000;font-weight:900}
.buy{background:#00ff88;color:#000;font-weight:900;font-size:11px}.sell{background:#ff3b30;color:#fff;font-weight:900;font-size:11px}
.circle-wrap{position:relative;width:270px;height:270px;margin:18px auto}
.bg{fill:none;stroke:#0f284a;stroke-width:14}.prog{fill:none;stroke:#FFD700;stroke-width:14;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}
.center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}
.mxn-big{font-size:44px;color:#00ff88;font-weight:900;line-height:1}.usd-small{font-size:11px;color:#5a7aa5;margin-top:4px}
.acum-mxn{font-size:48px;color:#00ff88;font-weight:900;text-align:center;line-height:1}.acum-usd{font-size:13px;color:#5a7aa5;text-align:center}
.table{width:100%;border-collapse:collapse;margin-top:10px;font-size:11px}
.table th{background:#0f284a;color:#FFD700;padding:8px 4px;text-align:center;font-size:9px}.table td{padding:7px 4px;border-bottom:1px solid #14365f;text-align:center}
.comp{background:#00ff88;color:#000;padding:12px;border-radius:12px;font-weight:900;text-align:center;margin:8px 0;font-size:16px}
.badge-mxn{color:#00ff88;font-weight:900}.scroll{overflow-x:auto}
.resumen{background:#102a4a;border:2px solid #FFD700;border-radius:16px;padding:14px;margin:14px 0}
</style></head><body>
<div class="titulo">MAQUINA DE HACER DINERO</div>
<div class="subtitulo">BASE 500 USD REAL + CONVERSION MXN - BOLA DE NIEVE ORIGINAL</div>
<div class="circle-wrap"><svg width="270" height="270"><circle class="bg" cx="135" cy="135" r="110"></circle><circle id="pc" class="prog" cx="135" cy="135" r="110" stroke-dasharray="691" stroke-dashoffset="691"></circle></svg>
<div class="center"><div style="font-size:9px;color:#8aa;letter-spacing:2px">BASE 500 USD + ACUM</div><div id="baseMxn" class="mxn-big">$0 MXN</div><div id="baseUsd" class="usd-small">$0 USD</div><div id="rateTxt" style="font-size:9px;color:#FFD700;margin-top:6px"></div><div id="diaTxt" style="font-size:10px;color:#5a7aa5;margin-top:2px"></div></div></div>
<div class="card" style="border:2px solid #00ff88"><div style="text-align:center;color:#8aa;font-size:9px;letter-spacing:3px">ACUMULADO NETO REAL</div><div id="acumMxn" class="acum-mxn">$0 MXN</div><div id="acumUsd" class="acum-usd">$0 USD</div><div id="totalLine" style="text-align:center;color:#5a7aa5;font-size:10px;margin-top:6px"></div><div id="costoLine" class="comp"></div><div id="costoUsdLine" style="text-align:center;color:#5a7aa5;font-size:10px"></div><div style="text-align:center;color:#FFD700;font-size:9px;margin-top:6px">BASE 500 USD FIJA + ACUM EN USD x RATE MXN = TOTAL - BOLA DE NIEVE ORIGINAL</div></div>
<div class="card" style="border:1px solid #00ff88"><b style="color:#00ff88">TP 0,3% NETO REAL</b><br><br>
<button class="btn tp" onclick="doTP(0.3)">0,3%</button><button class="btn tp" onclick="doTP(0.4)">0,4%</button><button class="btn tp" onclick="doTP(0.5)">0,5%</button><button class="btn tp" onclick="doTP(0.6)">0,6%</button>
<span id="tpActual" style="margin-left:8px;color:#FFD700"></span></div>
<div class="card">AUTO <button id="autoBtn" class="btn on" onclick="doApi('auto')">ENCENDIDO</button> <span id="autoSt"></span> | ENTRADAS<br><button class="btn off" onclick="doApi('max?val=2')">2</button><button class="btn off" onclick="doApi('max?val=4')">4</button><button class="btn off" onclick="doApi('max?val=6')">6</button><button class="btn off" onclick="doApi('max?val=8')">8</button><button class="btn off" onclick="doApi('max?val=10')">10</button><div id="ejemploDiv" style="font-size:10px;color:#00ff88;margin-top:8px"></div></div>
<div class="card" style="border:2px solid #FFD700"><b style="color:#FFD700">MONEDAS 8 - TU ELIGES</b><div id="mons" style="margin-top:8px"></div><div id="botonesCompra" style="margin-top:10px;border-top:1px solid #14365f;padding-top:8px"></div></div>
<div class="card"><b style="color:#00ff88">ABIERTAS</b><div id="bolas"></div></div>
<div class="resumen"><b style="color:#FFD700;font-size:16px">RESUMEN TOTAL DE TODAS LAS ENTRADAS</b><div id="resumenBox" style="margin-top:10px"></div></div>
<div class="card"><b style="color:#FFD700">TABLA POR MONEDA</b><div class="scroll"><table class="table"><thead><tr><th>MON</th><th>ENT</th><th>GAN</th><th>PERD</th><th>NETA MXN</th><th>WIN%</th></tr></thead><tbody id="tablaMon"></tbody></table></div></div>
<div class="card"><b style="color:#00ff88">HISTORIAL</b><div class="scroll"><table class="table"><thead><tr><th>FECHA</th><th>MON</th><th>NETA MXN</th><th>NETA USD</th><th>% NETO</th><th>RESULTADO</th></tr></thead><tbody id="hist"></tbody></table></div></div>
<script>
async function load(){
  let r=await fetch("/api/data"); let d=await r.json();
  document.getElementById("baseMxn").innerText="$"+d.total_mxn.toFixed(2)+" MXN";
  document.getElementById("baseUsd").innerText="$"+d.total_usd.toFixed(2)+" USD";
  document.getElementById("rateTxt").innerText="BASE 500 USD x $"+d.rate.toFixed(2)+" = $"+d.config.BASE_MXN.toFixed(2)+" MXN";
  document.getElementById("diaTxt").innerText="DIA "+new Date().getDate()+"/30 | "+d.bolas.length+"/"+d.config.BOLAS_MAX;
  document.getElementById("acumMxn").innerText="$"+d.config.ACUMULADO_MXN.toFixed(2)+" MXN";
  document.getElementById("acumUsd").innerText="$"+d.config.ACUMULADO_USD.toFixed(2)+" USD";
  document.getElementById("totalLine").innerText="BASE $"+d.config.BASE_MXN.toFixed(0)+" MXN (500 USD) + ACUM $"+d.config.ACUMULADO_MXN.toFixed(0);
  document.getElementById("costoLine").innerText="COSTO POR BOLA: $"+d.costo_mxn.toFixed(0)+" MXN";
  document.getElementById("costoUsdLine").innerText="$"+d.costo_usd.toFixed(2)+" USD c/u | ($"+d.config.BASE_MXN.toFixed(0)+"+$"+d.config.ACUMULADO_MXN.toFixed(0)+")/"+d.config.BOLAS_MAX;
  document.getElementById("ejemploDiv").innerText="Base fija 500 USD, conversion a MXN varia con dolar - bola de nieve original";
  document.getElementById("autoSt").innerText=d.config.AUTO?"AUTO ON":"AUTO OFF";
  document.getElementById("autoBtn").innerText=d.config.AUTO?"ENCENDIDO":"APAGADO";
  document.getElementById("autoBtn").className="btn "+(d.config.AUTO?"on":"off");
  document.getElementById("tpActual").innerText="TP: "+d.config.TP_PCT+"%";
  let circ=691-(691*d.progreso/100); document.getElementById("pc").style.strokeDashoffset=circ;
  let m=""; let cm="";
  for(let k in d.monedas){
    let cls=d.monedas[k]?"on":"off";
    m+='<button class="btn '+cls+'" onclick="doMoneda(\\''+k+'\\')">'+k+'</button> ';
    if(d.monedas[k]){
      let ocupada=false; for(let b of d.bolas){ if(b.moneda==k) ocupada=true; }
      if(!ocupada) cm+='<button class="btn buy" onclick="doComprar(\\''+k+'\\')">COMPRAR '+k+'</button> ';
    }
  }
  document.getElementById("mons").innerHTML=m;
  document.getElementById("botonesCompra").innerHTML=cm || "Todas abiertas";
  let b="";
  d.bolas.forEach(function(x){
    b+='<div style="padding:8px 0;border-bottom:1px solid #14365f"><b>'+x.moneda+'</b> '+x.compra.toFixed(4)+' -> '+x.actual.toFixed(4)+' ';
    b+='<button class="btn sell" onclick="doVender('+x.id+')">VENDER</button><br>';
    b+='<span class="badge-mxn">$'+(x.neta_mxn||0).toFixed(2)+' MXN</span> Neto '+(x.pct_neto||0).toFixed(3)+'%</div>';
  });
  document.getElementById("bolas").innerHTML=b||"Sin abiertas - AUTO comprara";
  let res=d.resumen;
  let resHtml='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px">';
  resHtml+='<div>Total Entradas: <b style="color:#FFD700">'+res.total_entradas+'</b></div>';
  resHtml+='<div>Ganadas: <b style="color:#00ff88">'+res.ganadas+'</b> | Perdidas: <b style="color:#ff3b30">'+res.perdidas+'</b></div>';
  resHtml+='<div>Total: <b class="badge-mxn">$'+res.total_mxn.toFixed(2)+' MXN</b></div>';
  resHtml+='<div>Mas entradas: <b style="color:#FFD700">'+res.mas_entradas+'</b></div>';
  resHtml+='</div>';
  document.getElementById("resumenBox").innerHTML=resHtml;
  let tm="";
  for(let mon in d.tabla){
    let s=d.tabla[mon]; let win=s.entradas?((s.ganadas/s.entradas)*100).toFixed(0):0;
    tm+="<tr><td><b>"+mon+"</b></td><td>"+s.entradas+"</td><td>"+s.ganadas+"</td><td>"+s.perdidas+"</td><td>$"+s.total_mxn.toFixed(2)+"</td><td>"+win+"%</td></tr>";
  }
  document.getElementById("tablaMon").innerHTML=tm||"<tr><td colspan=6>Desde cero Base 500 USD</td></tr>";
  let h="";
  d.historial.forEach(function(x){
    let res=x.neta_mxn>0?'GANO':'PERDIO';
    let col=x.neta_mxn>0?'#00ff88':'#ff3b30';
    h+="<tr><td>"+x.fecha+"</td><td><b>"+x.moneda+"</b></td><td><b style=color:"+col+">$"+x.neta_mxn+"</b></td><td>$"+x.neta_usd+"</td><td>"+x.pct_neto+"%</td><td style=color:"+col+">"+res+"</td></tr>";
  });
  document.getElementById("
