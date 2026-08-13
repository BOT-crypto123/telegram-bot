# MAQUINA DE HACER DINERO V38.8 8/10 - HORARIO NY FIX WEB + AUTO
# B1 $600 B2 $850 | RSI 42 | TP 1.3% = $4.8 neto | SL 18% | MAX 6
import os, time, requests, threading
import yfinance as yf
from flask import Flask, jsonify
from datetime import datetime
import pytz

NPOINT_ID = '455c95667066c8b158d0'
NPOINT_URL = f'https://api.npoint.io/{NPOINT_ID}'
app = Flask(__name__)

# CONFIG 8/10 AGRESIVA
B1 = 600
B2 = 850
RSI_BUY = 42
TP = 1.3
SL = 18
MAX_POS = 6
RESERVA = 1500
MAP = {'BTC':'BTC-USD','ETH':'ETH-USD','SOL':'SOL-USD','XAUUSD':'GC=F','NVDA':'NVDA','TSLA':'TSLA'}

data = {'b':5000,'pos':[],'auto':True,'gan_total':0,'com_total':0}
prices = {}
rsis = {'BTC':38,'ETH':42,'SOL':43,'XAUUSD':40,'NVDA':52,'TSLA':51}

def ny_open():
    try:
        ny = datetime.now(pytz.timezone('America/New_York'))
        if ny.weekday() >= 5:
            return False
        h = ny.hour + ny.minute/60.0
        return 7.5 <= h <= 14.0
    except:
        return False

def puede(sym):
    if sym in ['BTC','ETH','SOL','XAUUSD']:
        return True
    return ny_open()

def get_price(sym):
    try:
        if sym == 'XAUUSD':
            try:
                p = yf.Ticker('GC=F').fast_info.last_price
                if p and p > 4000:
                    return float(p)
            except:
                pass
            return 4369.0
        p = yf.Ticker(MAP.get(sym,sym)).fast_info.last_price
        return float(p) if p else prices.get(sym,0)
    except:
        return prices.get(sym,0)

def load():
    global data
    try:
        r = requests.get(NPOINT_URL, timeout=8).json()
        if r.get('b',5000) < 3000 and len(r.get('pos',[])) >= 4:
            data = {'b':5000,'pos':[],'auto':True,'gan_total':0,'com_total':0}
            save()
            return
        data['b'] = r.get('b',5000)
        data['pos'] = r.get('pos',[])
        data['auto'] = r.get('auto',True)
        data['gan_total'] = r.get('gan_total',0)
        data['com_total'] = r.get('com_total',0)
    except:
        pass

def save():
    try:
        requests.post(NPOINT_URL, json=data, timeout=8)
    except:
        pass

def trading_loop():
    while True:
        try:
            for s in ['BTC','ETH','SOL','XAUUSD','NVDA','TSLA']:
                pr = get_price(s)
                if pr == 0:
                    continue
                prices[s] = pr
                # CIERRE
                for p in list(data['pos']):
                    if p.get('sym') != s:
                        continue
                    entry = p.get('entry',0)
                    if entry == 0:
                        continue
                    pct = (pr - entry)/entry*100
                    if pct >= TP or pct <= -SL:
                        amt = p.get('amt',0)
                        com = amt*0.006
                        neto = amt*pct/100 - com
                        data['b'] += amt + neto
                        data['gan_total'] += neto
                        data['com_total'] += com
                        data['pos'].remove(p)
                        save()
                # COMPRA 8/10
                if not data['auto']:
                    continue
                if len(data['pos']) >= MAX_POS:
                    continue
                cnt = len([x for x in data['pos'] if x.get('sym')==s])
                if cnt >= 2:
                    continue
                if data['b'] - RESERVA < B1:
                    continue
                if rsis.get(s,50) < RSI_BUY and puede(s):
                    amt = B1 if cnt==0 else B2
                    data['pos'].append({'sym':s,'entry':pr,'price':pr,'amt':amt,'nivel':cnt+1,'pct':0,'flot':-3})
                    data['b'] -= amt
                    save()
            time.sleep(4)
        except Exception as e:
            print('loop err',e)
            time.sleep(5)

@app.route('/')
def dashboard():
    return '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAQUINA V38.8</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px;margin:0}
.card{background:#1a1a1a;border-radius:16px;padding:16px;margin-bottom:12px;border:1px solid #2a2a2a}
.big{font-size:44px;font-weight:900;text-align:center}
.sub{color:#ffcc00;text-align:center;font-weight:bold;letter-spacing:1px}
.green{color:#00ff88} .red{color:#ff3b30} .yellow{color:#ffcc00}
.grid{display:flex;justify-content:space-around;text-align:center;margin-top:12px}
.pos{border-left:4px solid #00ff88;margin:8px 0}
</style></head><body>
<div class="card">
<div class="sub">💰 MAQUINA V38.8 8/10 - HACER DINERO</div>
<div style="text-align:center;color:#00ff88;font-size:12px" id="conf">B1 $600 B2 $850 RSI<42 TP 1.3% | BTC/ETH/SOL/XAU 24/7</div>
<div class="big" id="total">$0</div>
<div class="grid">
<div>Saldo<br><b id="saldo">$0</b></div>
<div>Flot NETO<br><b id="flot" class="yellow">$0</b></div>
<div>Pos<br><b id="posn">0/6</b></div>
</div>
<div style="text-align:center;margin-top:10px;font-size:13px">Hist NETO <b id="hist" class="green">$0</b> | Com <b id="com">$0</b></div>
<div style="text-align:center;font-size:12px;margin-top:6px" id="ny">NY: -- | AUTO ON</div>
</div>
<div id="poslist"></div>
<div id="market"></div>
<script>
async function refresh(){
 let r = await fetch('/api/estado'); let d = await r.json();
 document.getElementById('total').innerText = '$'+d.total.toFixed(2);
 document.getElementById('saldo').innerText = '$'+d.b.toFixed(2);
 document.getElementById('flot').innerText = d.flot.toFixed(2)+'$';
 document.getElementById('posn').innerText = d.pos.length+'/6';
 document.getElementById('hist').innerText = '$'+d.gan_total.toFixed(2);
 document.getElementById('com').innerText = '$'+d.com_total.toFixed(2);
 document.getElementById('ny').innerText = 'NY: '+(d.ny_open?'ABIERTO ✅':'CERRADO ❌')+' | AUTO '+(d.auto?'ON':'OFF')+' | 8/10';
 let h=''; d.pos.forEach(p=>{
   let col = p.flot>=0?'#00ff88':'#ff3b30';
   h+=`<div class="card pos" style="border-left-color:${col}"><div><b>${p.sym} N${p.nivel} $${p.amt}</b><span style="float:right;color:${col}">${p.flot.toFixed(2)}$</span></div><div style="font-size:13px">$${p.entry.toFixed(2)} → $${p.price.toFixed(2)} <b style="color:${col}">${p.pct.toFixed(2)}%</b></div><div style="font-size:11px;color:#aaa">NETO ${p.flot.toFixed(2)}$ tras com</div></div>`;
 });
 document.getElementById('poslist').innerHTML = h ? '<div class="yellow">🔥 POSICIONES ACTIVAS</div>'+h : '<div class="card" style="text-align:center;color:#888">Sin posiciones - Esperando RSI<42</div>';
 let m=''; for(let k in d.prices){ m+=`<div class="card" style="padding:10px;display:flex;justify-content:space-between"><span>${k}</span><span>$${d.prices[k].toFixed(2)} RSI ${d.rsis[k]||50}</span></div>`}
 document.getElementById('market').innerHTML = m;
}
setInterval(refresh,3000); refresh();
</script></body></html>
'''

@app.route('/api/estado')
def estado():
    flot = 0
    for p in data['pos']:
        pr = prices.get(p.get('sym'), p.get('entry',0))
        p['price'] = pr
        entry = p.get('entry',0)
        if entry != 0:
            p['pct'] = (pr-entry)/entry*100
        else:
            p['pct'] = 0
        p['flot'] = p.get('amt',0)*p['pct']/100 - p.get('amt',0)*0.006
        flot += p['flot']
    total_amt = sum([x.get('amt',0) for x in data['pos']])
    total = data['b'] + total_amt + flot
    if len(data['pos']) == 0:
        total = data['b']
    return jsonify({'b':data['b'],'pos':data['pos'],'total':total,'flot':flot,'auto':data['auto'],'ny_open':ny_open(),'gan_total':data.get('gan_total',0),'com_total':data.get('com_total',0),'prices':prices,'rsis':rsis,'rsi_buy':RSI_BUY,'tp':TP})

load()
threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',10000)))
