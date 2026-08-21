import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter

os.environ['PYTHONUNBUFFERED']='1'
print("INICIANDO V144 ULTRA FIX CHR", flush=True)

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
    return {"pct_bruto":pct_bruto,"pct_neto":pct_neto,"neta_usd":neta_usd,"neta_mxn":neta_usd*rate}

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
            h={"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":b["moneda"],"entrada":b["compra"],"salida":b["actual"],"neta_mxn":round(b["neta_mxn"],2),"neta_usd":round(b["neta_usd"],4),"pct_neto":round(b["pct_neto"],3)}
            historial.insert(0,h); bolas.remove(b); return b
    return None

def resumen_total():
    if not historial: return {"total_entradas":0,"ganadas":0,"perdidas":0,"total_mxn":0,"total_usd":0,"mas_entradas":"-","mejor_moneda":"-","peor_moneda":"-"}
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
    return {"total_entradas":len(historial),"ganadas":ganadas,"perdidas":perdidas,"total_mxn":total_mxn,"total_usd":total_usd,"mas_entradas":mas_entradas,"mejor_moneda":mejor,"peor_moneda":peor}

def tabla_por_moneda():
    stats=defaultdict(lambda: {"entradas":0,"ganadas":0,"perdidas":0,"total_mxn":0.0})
    for h in historial:
        m=h["moneda"]; stats[m]["entradas"]+=1
        if h["neta_mxn"]>0: stats[m]["ganadas"]+=1
        else: stats[m]["perdidas"]+=1
        stats[m]["total_mxn"]+=h["neta_mxn"]
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
    o=chr(123); c=chr(125); h=chr(35)
    css = f"body{o}background:{h}061126;color:{h}fff;font-family:Arial;padding:10px;margin:0{c}.titulo{o}font-size:26px;text-align:center;color:{h}FFD700;font-weight:900{c}.card{o}background:{h}0c1e3a;border-radius:16px;padding:14px;margin:12px 0;border:1px solid {h}14365f{c}.btn{o}padding:9px 14px;border-radius:10px;border:none;margin:4px;font-weight:bold;cursor:pointer{c}.on{o}background:{h}0ea5e9;color:{h}fff{c}.off{o}background:{h}0f284a;color:{h}5a7aa5{c}.tp{o}background:{h}00e5ff;color:{h}000{c}.buy{o}background:{h}00ff88;color:{h}000{c}.sell{o}background:{h}ff3b30;color:{h}fff{c}.comp{o}background:{h}00ff88;color:{h}000;padding:12px;border-radius:12px;font-weight:900;text-align:center{c}.resumen{o}background:{h}102a4a;border:2px solid {h}FFD700;border-radius:16px;padding:14px{c}"
    html = f"<!DOCTYPE html><html><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>MAQUINA</title><style>{css}</style></head><body>"
    html += f"<div class=\"titulo\">MAQUINA DE HACER DINERO</div><div style=\"text-align:center;color:{h}8aa;font-size:10px\">BASE 500 USD REAL - BOLA DE NIEVE</div>"
    html += f"<div style=\"text-align:center;margin:20px\"><div id=\"baseMxn\" style=\"font-size:44px;color:{h}00ff88;font-weight:900\">$0 MXN</div><div id=\"baseUsd\" style=\"color:{h}5a7aa5\">$0 USD</div><div id=\"rateTxt\" style=\"color:{h}FFD700;font-size:10px\"></div><div id=\"diaTxt\" style=\"color:{h}5a7aa5\"></div></div>"
    html += f"<div class=\"card\" style=\"border:2px solid {h}00ff88\"><div id=\"acumMxn\" style=\"font-size:48px;color:{h}00ff88;font-weight:900;text-align:center\">$0</div><div id=\"acumUsd\" style=\"text-align:center;color:{h}5a7aa5\">$0</div><div id=\"totalLine\" style=\"text-align:center;color:{h}5a7aa5;font-size:10px\"></div><div id=\"costoLine\" class=\"comp\"></div></div>"
    html += f"<div class=\"card\"><b style=\"color:{h}00ff88\">TP NETO</b><br><button class=\"btn tp\" onclick=\"doTP(0.3)\">0,3%</button><button class=\"btn tp\" onclick=\"doTP(0.4)\">0,4%</button><button class=\"btn tp\" onclick=\"doTP(0.5)\">0,5%</button><button class=\"btn tp\" onclick=\"doTP(0.6)\">0,6%</button><span id=\"tpActual\" style=\"color:{h}FFD700;margin-left:8px\"></span></div>"
    html += f"<div class=\"card\">AUTO <button id=\"autoBtn\" class=\"btn on\" onclick=\"doApi('auto')\">ON</button> <span id=\"autoSt\"></span><br>ENTRADAS <button class=\"btn off\" onclick=\"doApi('max?val=2')\">2</button><button class=\"btn off\" onclick=\"doApi('max?val=4')\">4</button><button class=\"btn off\" onclick=\"doApi('max?val=6')\">6</button><button class=\"btn off\" onclick=\"doApi('max?val=8')\">8</button><button class=\"btn off\" onclick=\"doApi('max?val=10')\">10</button></div>"
    html += f"<div class=\"card\" style=\"border:2px solid {h}FFD700\"><b style=\"color:{h}FFD700\">MONEDAS 8 - TU ELIGES</b><div id=\"mons\" style=\"margin-top:8px\"></div><div id=\"botonesCompra\" style=\"margin-top:10px\"></div></div>"
    html += f"<div class=\"card\"><b style=\"color:{h}00ff88\">ABIERTAS</b><div id=\"bolas\"></div></div>"
    html += f"<div class=\"resumen\"><b style=\"color:{h}FFD700\">RESUMEN TOTAL ENTRADAS</b><div id=\"resumenBox\" style=\"margin-top:10px\"></div></div>"
    html += f"<div class=\"card\"><b style=\"color:{h}FFD700\">TABLA POR MONEDA</b><table style=\"width:100%;font-size:11px\"><thead><tr><th>MON</th><th>ENT</th><th>GAN</th><th>NETA MXN</th><th>WIN%</th></tr></thead><tbody id=\"tablaMon\"></tbody></table></div>"
    html += f"<div class=\"card\"><b style=\"color:{h}00ff88\">HISTORIAL</b><table style=\"width:100%;font-size:11px\"><thead><tr><th>FECHA</th><th>MON</th><th>NETA MXN</th><th>%</th><th>RES</th></tr></thead><tbody id=\"hist\"></tbody></table></div>"
    html += "<script>async function load(){let r=await fetch('/api/data');let d=await r.json();document.getElementById('baseMxn').innerText='$'+d.total_mxn.toFixed(2)+' MXN';document.getElementById('baseUsd').innerText='$'+d.total_usd.toFixed(2)+' USD';document.getElementById('rateTxt').innerText='500 USD x $'+d.rate.toFixed(2);document.getElementById('diaTxt').innerText=d.bolas.length+'/'+d.config.BOLAS_MAX;document.getElementById('acumMxn').innerText='$'+d.config.ACUMULADO_MXN.toFixed(2)+' MXN';document.getElementById('acumUsd').innerText='$'+d.config.ACUMULADO_USD.toFixed(2)+' USD';document.getElementById('totalLine').innerText='BASE $'+d.config.BASE_MXN.toFixed(0)+' + ACUM $'+d.config.ACUMULADO_MXN.toFixed(0);document.getElementById('costoLine').innerText='COSTO $'+d.costo_mxn.toFixed(0)+' MXN';document.getElementById('autoSt').innerText=d.config.AUTO?'AUTO ON':'OFF';document.getElementById('tpActual').innerText='TP '+d.config.TP_PCT+'%';let m='';let cm='';for(let k in d.monedas){let cls=d.monedas[k]?'on':'off';m+='<button class=\"btn '+cls+'\" onclick=\"doMoneda(\\''+k+'\\')\">'+k+'</button> ';if(d.monedas[k]){let oc=false;for(let b of d.bolas){if(b.moneda==k)oc=true;}if(!oc)cm+='<button class=\"btn buy\" onclick=\"doComprar(\\''+k+'\\')\">COMPRAR '+k+'</button> ';}}document.getElementById('mons').innerHTML=m;document.getElementById('botonesCompra').innerHTML=cm;let b='';d.bolas.forEach(function(x){b+='<div><b>'+x.moneda+'</b> '+x.compra.toFixed(4)+'->'+x.actual.toFixed(4)+' <button class=\"btn sell\" onclick=\"doVender('+x.id+')\">VENDER</button> $'+(x.neta_mxn||0).toFixed(2)+' MXN '+(x.pct_neto||0).toFixed(2)+'%</div>';});document.getElementById('bolas').innerHTML=b||'Sin abiertas';let res=d.resumen;document.getElementById('resumenBox').innerHTML='Total: '+res.total_entradas+' | Ganadas: '+res.ganadas+' | Perdidas: '+res.perdidas+' | Total MXN $'+res.total_mxn.toFixed(2)+' | Mas entradas: '+res.mas_entradas+' | Mejor: '+res.mejor_moneda+' | Peor: '+res.peor_moneda;let tm='';for(let mon in d.tabla){let s=d.tabla[mon];let win=s.entradas?((s.ganadas/s.entradas)*100).toFixed(0):0;tm+='<tr><td>'+mon+'</td><td>'+s.entradas+'</td><td>'+s.ganadas+'</td><td>$'+s.total_mxn.toFixed(2)+'</td><td>'+win+'%</td></tr>';}document.getElementById('tablaMon').innerHTML=tm;let hh='';d.historial.forEach(function(x){let c=x.neta_mxn>0?'#00ff88':'#ff3b30';hh+='<tr><td>'+x.fecha+'</td><td>'+x.moneda+'</td><td style=\"color:'+c+'\">$'+x.neta_mxn+'</td><td>'+x.pct_neto+'%</td><td style=\"color:'+c+'\">'+(x.neta_mxn>0?'GANO':'PERDIO')+'</td></tr>';});document.getElementById('hist').innerHTML=hh;}async function doApi(u){await fetch('/api/'+u);load();}async function doTP(v){await fetch('/api/tp?val='+
