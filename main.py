# MAQUINA V38.8 HORARIO NY FIX WEB + AUTO
import os, json, time, requests, threading
from flask import Flask, jsonify
from datetime import datetime
import pytz

NPOINT_ID = "455c95667066c8b158d0"
NPOINT_URL = f"https://api.npoint.io/{NPOINT_ID}"
app = Flask(__name__)

data = {"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0,"com_total":0}

def ny_open():
    try:
        ny = datetime.now(pytz.timezone('America/New_York'))
        if ny.weekday() >= 5: return False
        return 7.5 <= ny.hour + ny.minute/60 <= 14.0
    except: return False

def load():
    global data
    try:
        r = requests.get(NPOINT_URL, timeout=8)
        d = r.json()
        # AUTO-FIX BUG $2000 + 6 posiciones
        b = d.get("b",5000)
        pos = d.get("pos",[])
        if b < 3000 and len(pos) >= 4:
            print("BUG DETECTADO, RESETEANDO A $5000")
            data = {"b":5000,"pos":[],"alert_users":d.get("alert_users",[]),"auto":True,"gan_total":0,"com_total":0}
            save()
            return
        data = {
            "b": d.get("b",5000),
            "pos": d.get("pos",[]),
            "alert_users": d.get("alert_users",[]),
            "auto": d.get("auto",True),
            "gan_total": d.get("gan_total",0),
            "com_total": d.get("com_total",0)
        }
        # Si venía en $2000, corrige
        if data["b"] < 3000 and len(data["pos"])==0:
            data["b"]=5000
            save()
    except Exception as e:
        print("load err",e)

def save():
    try:
        requests.post(NPOINT_URL, json=data, timeout=8)
    except Exception as e:
        print("save err",e)

@app.route("/")
def dashboard():
    # V38.8 HTML lee de /api/estado no de npoint
    return """
<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}
.card{background:#1a1a1a;border-radius:15px;padding:15px;margin-bottom:15px}
.pos{border-left:4px solid #ff3b30;padding-left:10px;margin:10px 0}
</style></head><body>
<div id='main' class='card'>Cargando...</div>
<div id='pos'></div>
<script>
async function refresh(){
  let r = await fetch('/api/estado'); let d = await r.json();
  document.getElementById('main').innerHTML = `
  <div style='text-align:center'>
    <div style='color:#ffcc00'>💰 MAQUINA V38.8 HORARIO NY</div>
    <div style='color:#00ff88;font-size:12px'>BTC/ETH/SOL/XAU 24/7 | NVDA/TSLA 7:30am-2pm Lun-Vie</div>
    <div style='font-size:42px;font-weight:bold'>$${d.total.toFixed(2)}</div>
    <div style='display:flex;justify-content:space-around;margin-top:10px'>
      <div>Saldo<br>$${d.b.toFixed(2)}</div>
      <div>Flot NETO<br>${d.flot.toFixed(2)}$</div>
      <div>Pos<br>${d.pos.length}/6</div>
    </div>
    <div>Hist NETO $${d.gan_total.toFixed(2)} | Com $${d.com_total.toFixed(2)}</div>
    <div>NY: ${d.ny_open?'ABIERTO ✅':'CERRADO ❌'} | AUTO ${d.auto?'ON':'OFF'}</div>
  </div>`;
  let h=''; d.pos.forEach(p=>{
    h+=`<div class='card pos'><div><b>${p.sym} N${p.nivel||1} $${p.amt}</b> <span style='float:right;color:#ff3b30'>${p.flot||-3}$</span></div>
    <div>$${p.entry}→$${p.price} ${p.pct||0}%</div><div>NETO $${p.flot||-3}</div></div>`
  });
  document.getElementById('pos').innerHTML='<div style="color:#ffcc00">🔥 POSICIONES - TOCA GRAFICA</div>'+h;
}
setInterval(refresh,3000); refresh();
</script></body></html>
"""

@app.route("/api/estado")
def estado():
    # Calcula flot real si tienes precios, aquí simplificado
    flot = sum([p.get("flot",0) for p in data["pos"]])
    total = data["b"] + sum([p.get("amt",500) for p in data["pos"]]) + flot
    # Si no hay pos, total = b
    if len(data["pos"])==0: total = data["b"]
    return jsonify({
        "b": data["b"],
        "pos": data["pos"],
        "total": total,
        "flot": flot,
        "auto": data["auto"],
        "ny_open": ny_open(),
        "gan_total": data.get("gan_total",0),
        "com_total": data.get("com_total",0)
    })
