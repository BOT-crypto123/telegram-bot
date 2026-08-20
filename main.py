import os, time, requests
from flask import Flask, jsonify, request
app = Flask(__name__)
BOT_TOKEN = "8805451290:AAFie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M"

CONFIG = {
    "VERSION": "V76 10K MXN SIN ML FIX",
    "MAX": 6,
    "TRAIL_PCT": 0.2,
    "RETAIL_PCT": 0.2,
    "BALANCE": 10000,
    "FEES": 0.1,
    "AUTO": True,
    "bolas": [],
    "last_price": 2050000,
    "cache": 0,
    "high": {}
}

def get_price():
    try: 
        return float(requests.get("https://api.coinbase.com/v2/prices/BTC-MXN/spot",timeout=5).json()["data"]["amount"])
    except: 
        return CONFIG["last_price"]

def calc():
    price=get_price()
    if time.time()-CONFIG["cache"]>15:
        CONFIG["last_price"]=price
        CONFIG["cache"]=time.time()
    else:
        price=CONFIG["last_price"]

    costo=CONFIG["BALANCE"]/CONFIG["MAX"]
    rows=""; tb=tf=tn=0

    for b in CONFIG["bolas"]:
        if b["id"] not in CONFIG["high"]:
            CONFIG["high"][b["id"]]=b["entry"]
        if price > CONFIG["high"][b["id"]]:
            CONFIG["high"][b["id"]]=price
        high=CONFIG["high"][b["id"]]
        dd=(high-price)/high*100 if high>0 else 0

        pct=(price-b["entry"])/b["entry"]*100
        bruto=costo*pct/100
        fees=costo*CONFIG["FEES"]/100*2
        neto=bruto-fees

        tb+=bruto; tf+=fees; tn+=neto
        vender = pct >= CONFIG["RETAIL_PCT"] and dd >= CONFIG["TRAIL_PCT"]
        estado = "VENDER" if vender else f"{dd:.2f}% DD"
        color = "lime" if neto>0 else "red"
        rows+=f"<tr><td>{b['id']}</td><td>${b['entry']:,.0f}</td><td>{pct:+.3f}%</td><td>${bruto:.2f}</td><td>${fees:.2f}</td><td style='color:{color}'><b>${neto:.2f}</b></td><td>{estado}</td></tr>"
    return price,costo,rows,tb,tf,tn

@app.route("/")
def dash():
    price,costo,rows,tb,tf,tn=calc()
    max_opts=[2,3,4,5,6]
    opts=[0.1,0.2,0.3,0.4,0.5,0.6]

    max_b="".join([f"<a href='/set_max/{i}' style='margin:3px;padding:10px 16px;background:{'#00c853' if i==CONFIG['MAX'] else '#333'};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{i}</a>" for i in max_opts])
    retail_b="".join([f"<a href='/set_retail/{r}' style='margin:3px;padding:10px 12px;background:{'#ff9800' if r==CONFIG['RETAIL_PCT'] else '#333'};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{r}%</a>" for r in opts])
    trail_b="".join([f"<a href='/set_trail/{p}' style='margin:3px;padding:10px 12px;background:{'#00c853' if p==CONFIG['TRAIL_PCT'] else '#333'};color:#fff;text-decoration:none;border-radius:6px;display:inline-block'>{p}%</a>" for p in opts])

    html = f"""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"></head>
    <body style="font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:12px">
    <h3 style="color:#0f0">{CONFIG['VERSION']} | {len(CONFIG['bolas'])}/{CONFIG['MAX']} | FLOAT ${tn:.2f} MXN</h3>
    <div style="background:#1a1a1a;padding:12px;border-left:4px solid #0f0">
    BTC ${price:,.0f} MXN | Por bola ${costo:.0f} MXN<br>
    <b>BRUTO ${tb:.2f} - FEES ${tf:.2f} = NETO ${tn:.2f} MXN</b>
    </div>
    <div style="background:#111;padding:12px;margin:10px 0;text-align:center">
    <a href='/toggle_auto' style='padding:12px 24px;background:{'#00c853' if CONFIG['AUTO'] else '#ff3d00'};color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>AUTO: {'ON COMPRA SOLO' if CONFIG['AUTO'] else 'OFF SOLO ALERTA ENTRADA'}</a>
    </div>
    <div style="background:#111;padding:12px;margin:8px 0"><b>MAX ABIERTAS 2-6:</b><br><br>{max_b}</div>
    <div style="background:#111;padding:12px;margin:8px 0"><b>TRAIL % 0.1-0.6:</b><br><br>{trail_b} Actual {CONFIG['TRAIL_PCT']}%</div>
    <div style="background:#111;padding:12px;margin:8px 0;border:1px solid orange"><b>RETAIL % 0.1-0.6:</b><br><br>{retail_b} Actual {CONFIG['RETAIL_PCT']}% = ${costo*CONFIG['RETAIL_PCT']/100:.2f}
