# V40.0 MAQUINA DE HACER DINERO - CON GRAFICAS CON LINEAS + FIX 409
import os, time, requests, threading
from collections import deque
import yfinance as yf
from flask import Flask, jsonify
import telebot
from datetime import datetime
import pytz

TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN') or 'AQUI_TU_TOKEN'
NPOINT_ID = '455c95667066c8b158d0'
NPOINT_URL = f'https://api.npoint.io/{NPOINT_ID}'

B1=600; B2=850; RSI_BUY=42; TP=1.3; SL=18; MAX_POS=6; RESERVA=1500
MAP={'BTC':'BTC-USD','ETH':'ETH-USD','SOL':'SOL-USD','XAUUSD':'GC=F','NVDA':'NVDA','TSLA':'TSLA'}

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)
try: bot.delete_webhook(drop_pending_updates=True); print("WEBHOOK BORRADO")
except: pass

data={'b':5000,'pos':[],'auto':True,'gan_total':0,'com_total':0}
prices={}; rsis={'BTC':38,'ETH':42,'SOL':43,'XAUUSD':40,'NVDA':52,'TSLA':51}

# HISTORIAL PARA GRAFICAS
history = {'time': deque(maxlen=200), 'total': deque(maxlen=200), 'flot': deque(maxlen=200), 'BTC': deque(maxlen=200), 'XAUUSD': deque(maxlen=200), 'SOL': deque(maxlen=200)}

def ny_open():
    try:
        ny=datetime.now(pytz.timezone('America/New_York'))
        if ny.weekday()>=5: return False
        h=ny.hour+ny.minute/60.0; return 7.5 <= h <= 14.0
    except: return True

def puede(sym): return True if sym in ['BTC','ETH','SOL','XAUUSD'] else ny_open()

def get_price(sym):
    try:
        if sym=='XAUUSD':
            try:
                p=yf.Ticker('GC=F').fast_info.last_price
                if p and p>4000: return float(p)
            except: pass
            return 4414.0
        p=yf.Ticker(MAP.get(sym,sym)).fast_info.last_price
        return float(p) if p and p>0 else prices.get(sym,0)
    except: return prices.get(sym,0)

def load():
    try:
        r=requests.get(NPOINT_URL,timeout=10).json()
        data['b']=float(r.get('b',5000)); data['pos']=r.get('pos',[]); data['auto']=r.get('auto',True)
        data['gan_total']=float(r.get('gan_total',0)); data['com_total']=float(r.get('com_total',0))
    except: pass

def save():
    try: requests.post(NPOINT_URL,json=data,timeout=10)
    except: pass

def calc_flot():
    flot=0
    for p in data['pos']:
        pr=prices.get(p.get('sym'), p.get('entry',0)); entry=p.get('entry',0)
        if entry==0: continue
        p['price']=pr; p['pct']=(pr-entry)/entry*100; p['flot']=p.get('amt',0)*p['pct']/100 - p.get('amt',0)*0.006; flot+=p['flot']
    return flot

def get_texto():
    flot=calc_flot(); total=data['b']+sum([x.get('amt',0) for x in data['pos']])+flot
    if len(data['pos'])==0: total=data['b']
    ny="ABIERTO ✅" if ny_open() else "CERRADO ❌"; auto="ON ✅" if data['auto'] else "OFF ❌"
    return f"V40.0 GRAFICAS 🔥\n💰 Total NETO ${total:.2f}\nSaldo ${data['b']:.2f}\nFlot {flot:.2f}$\nPos {len(data['pos'])}/{MAX_POS}\nNY: {ny}\nAUTO {auto}\nHist NETO ${data.get('gan_total',0):.2f}\nhttps://telegram-bot-cijp.onrender.com"

def trading_loop():
    while True:
        try:
            for sym in ['BTC','ETH','SOL','XAUUSD','NVDA','TSLA']:
                pr=get_price(sym)
                if pr==0: continue
                prices[sym]=pr
                for p in list(data['pos']):
                    if p.get('sym')!=sym: continue
                    entry=p.get('entry',0)
                    if entry==0: continue
                    pct=(pr-entry)/entry*100
                    if pct>=TP or pct<=-SL:
                        amt=p.get('amt',0); com=amt*0.006; neto=amt*pct/100 - com
                        data['b']+=amt+neto; data['gan_total']+=neto; data['com_total']+=com; data['pos'].remove(p); save()
                if not data['auto'] or len(data['pos'])>=MAX_POS: continue
                cnt=len([x for x in data['pos'] if x.get('sym')==sym])
                if cnt>=2 or data['b']-RESERVA<B1: continue
                if rsis.get(sym,50)<RSI_BUY and puede(sym):
                    amt=B1 if cnt==0 else B2
                    data['pos'].append({'sym':sym,'entry':pr,'price':pr,'amt':amt,'nivel':cnt+1}); data['b']-=amt; save()
            # GUARDAR HISTORIAL PARA GRAFICA
            flot=calc_flot(); total=data['b']+sum([x.get('amt',0) for x in data['pos']])+flot
            if len(data['pos'])==0: total=data['b']
            history['time'].append(datetime.now().strftime("%H:%M"))
            history['total'].append(round(total,2)); history['flot'].append(round(flot,2))
            history['BTC'].append(prices.get('BTC',0)); history['XAUUSD'].append(prices.get('XAUUSD',0)); history['SOL'].append(prices.get('SOL',0))
            time.sleep(10)
        except: time.sleep(5)

@bot.message_handler(commands=['start','balance','b','dashboard'])
def cmd_bal(m): bot.send_message(m.chat.id, get_texto())

@bot.message_handler(func=lambda m: True)
def all_h(m):
    t=m.text.strip().upper()
    if t in ['DASHBOARD','BALANCE','B']: bot.send_message(m.chat.id, get_texto())
    elif t in MAP: bot.send_message(m.chat.id, f"{t} ${prices.get(t,get_price(t)):.2f}")
    elif t=='AUTO ON': data['auto']=True; save(); bot.send_message(m.chat.id,"AUTO ON ✅")
    elif t=='AUTO OFF': data['auto']=False; save(); bot.send_message(m.chat.id,"AUTO OFF ❌")
    elif 'RESET' in t: data['b']=5000; data['pos']=[]; data['gan_total']=0; data['com_total']=0; save(); bot.send_message(m.chat.id,"RESETEADO $5000 ✅\n"+get_texto())
    else: bot.send_message(m.chat.id, get_texto())

def tg_polling():
    try: bot.delete_webhook(drop_pending_updates=True)
    except: pass
    while True:
        try: bot.infinity_polling(timeout=20, long_polling_timeout=30)
        except: time.sleep(5);
        try: bot.delete_webhook(drop_pending_updates=True)
        except: pass

# --- WEB CON GRAFICAS ---
@app.route('/')
def home():
    flot=calc_flot(); total=data['b']+sum([x.get('amt',0) for x in data['pos']])+flot
    if len(data['pos'])==0: total=data['b']
    # HTML CON CHART.JS
    html = f"""
    <html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V40 GRAFICAS</title>
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <style>body{{background:#0f172a;color:white;font-family:Arial;padding:10px}}.card{{background:#1e293b;padding:15px;border-radius:12px;margin:10px 0}} h2{{color:#38bdf8}}</style>
    </head><body>
    <h2>V40.0 MAQUINA DE HACER DINERO - GRAFICAS</h2>
    <div class='card'><b>Total NETO:</b> ${total:.2f} | <b>Saldo:</b> ${data['b']:.2f} | <b>Flot:</b> {flot:.2f}$ | <b>Pos:</b> {len(data['pos'])}/6 | Hist ${data.get('gan_total',0):.2f}</div>
    <div class='card'><canvas id='c1'></canvas></div>
    <div class='card'><canvas id='c2'></canvas></div>
    <div class='card'><h3>Posiciones</h3><pre>{data['pos']}</pre></div>
    <div class='card'><h3>Precios</h3><pre>BTC ${prices.get('BTC',0):.2f} | XAU ${prices.get('XAUUSD',0):.2f} | SOL ${prices.get('SOL',0):.2f}</pre></div>
    <script>
    fetch('/api/history').then(r=>r.json()).then(d=>{{
      new Chart(document.getElementById('c1'),{{type:'line',data:{{labels:d.time,datasets:[{{label:'Total NETO $',data:d.total,borderColor:'#22c55e',tension:0.4}},{{label:'Flot $',data:d.flot,borderColor:'#f59e0b',tension:0.4}}]}},options:{{responsive:true}}}});
      new Chart(document.getElementById('c2'),{{type:'line',data:{{labels:d.time,datasets:[{{label:'BTC',data:d.BTC,borderColor:'#f97316',tension:0.4}},{{label:'XAUUSD',data:d.XAUUSD,borderColor:'#eab308',tension:0.4}},{{label:'SOL',data:d.SOL,borderColor:'#a855f7',tension:0.4}}]}},options:{{responsive:true}}}});
    }});
    setTimeout(()=>location.reload(),30000);
    </script></body></html>
    """
    return html

@app.route('/api/history')
def api_history():
    return jsonify({k:list(v) for k,v in history.items()})

@app.route('/api/estado')
def estado():
    flot=calc_flot(); total=data['b']+sum([x.get('amt',0) for x in data['pos']])+flot
    if len(data['pos'])==0: total=data['b']
    return jsonify({'b':data['b'],'pos':data['pos'],'total':total,'flot':flot,'gan_total':data.get('gan_total',0),'prices':prices,'auto':data['auto'],'ny_open':ny_open()})

@app.route('/reset')
def reset_route():
    data['b']=5000; data['pos']=[]; data['gan_total']=0; data['com_total']=0; data['auto']=True; save()
    return jsonify({'status':'RESETEADO $5000'})

load()
threading.Thread(target=trading_loop,daemon=True).start()
threading.Thread(target=tg_polling,daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT',10000)))
