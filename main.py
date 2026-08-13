# V41.0 MAQUINA - LA BUENA V36.1 + GRAFICAS VIVAS REALES + FIX
import os, requests, threading, time
from collections import deque
from flask import Flask, send_from_directory
import telebot
import yfinance as yf
from datetime import datetime
import pytz

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "AQUI_TU_TOKEN"
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["XAUUSD","BTC","NVDA","TSLA","ETH","SOL"]
MAP = {'BTC':'BTC-USD','ETH':'ETH-USD','SOL':'SOL-USD','XAUUSD':'GC=F','NVDA':'NVDA','TSLA':'TSLA'}

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)
try: bot.delete_webhook(drop_pending_updates=True)
except: pass

data={'b':5000,'pos':[],'auto':True,'gan_total':0,'com_total':0,'alert_users':[]}
prices={}; rsis={'BTC':38,'ETH':42,'SOL':43,'XAUUSD':40,'NVDA':52,'TSLA':51}
history={'time':deque(maxlen=100),'total':deque(maxlen=100),'flot':deque(maxlen=100)}

def P(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        if sym in mp:
            return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=4).json()["price"])
        return float(yf.Ticker(MAP.get(sym)).history(period='1d')['Close'].iloc[-1])
    except:
        try: return float(yf.Ticker(MAP.get(sym,sym)).fast_info.last_price)
        except: return prices.get(sym,0)

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10).json()
        data['b']=float(r.get('b',5000)); data['pos']=r.get('pos',[]); data['auto']=r.get('auto',True)
        data['gan_total']=float(r.get('gan_total',0)); data['alert_users']=r.get('alert_users',[])
    except: pass
def save():
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass
def totals():
    flot=0
    for p in data["pos"]:
        pr=prices.get(p["sym"], p.get("precio_entry", p.get("entry",0)))
        entry=p.get("precio_entry", p.get("entry",0))
        if entry==0: continue
        p["gan"]=((pr-entry)/entry)*p.get("monto",p.get("amt",600))
        p["price"]=pr; p["pct"]=((pr-entry)/entry*100)
        flot+=p["gan"]
    return data["b"]+sum([x.get("monto",x.get("amt",0)) for x in data["pos"]])+flot, flot

@app.route("/logo.png")
def logo(): return send_from_directory(".","logo.png")

@app.route("/")
def dash():
    tot,flot=totals()
    col="#00ff88" if flot>=0 else "#ff4444"
    pos_html=""
    for p in data["pos"]:
        sym=p["sym"]; pr=prices.get(sym,0); pct=p.get("pct",0)
        pos_html+=f"<div onclick=\"window.location='/chart/{sym}'\" style='display:flex;justify-content:space-between;padding:14px;border-bottom:1px solid #222;cursor:pointer'><div><b>{sym} N{p.get('nivel',1)} ${p.get('monto',p.get('amt',0))}</b> <span style='font-size:11px'>${p.get('precio_entry',p.get('entry',0)):.1f}→${pr:.1f} {pct:+.1f}%</span></div><span style='color:{col}'>{p.get('gan',0):+.2f}$</span></div>"
    if not pos_html: pos_html="<div style='padding:20px;text-align:center;opacity:.5'>Sin pos - esperando RSI<42<br>TOCÁ UNA MONEDA PARA VER GRAFICA VIVA</div>"
    coins=""
    for s in ALL_COINS:
        pr=prices.get(s,P(s)); rsi=rsis.get(s,40); count=sum(1 for x in data["pos"] if x["sym"]==s)
        c2="#ffcc00" if rsi<42 else "#444"
        coins+=f"<div onclick=\"window.location='/chart/{s}'\" style='background:#151515;border:2px solid {c2};border-radius:14px;padding:10px;cursor:pointer'><b>{s} {count}/2</b><br>${pr:.1f}<br>RSI {rsi:.0f}<br><small style='font-size:9px;color:#00ccff'>GRÁFICA VIVA ►</small></div>"
    return f"""<meta name=viewport content="width=device-width,initial-scale=1"><style>body{{background:#080808;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border-radius:20px;padding:16px;margin-bottom:12px;border:1px solid #222}}.gold{{color:#ffcc00;font-weight:800;font-size:12px}}.big{{font-size:34px;font-weight:900}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.logo{{width:90px;height:90px;border-radius:50%;border:3px solid #ffcc00}}</style>
    <div class=card style=text-align:center><img src="/logo.png" onerror="this.style.display='none'" class=logo><br><div class=gold>V41.0 MAQUINA DE HACER DINERO - GRAFICAS VIVAS</div><div class=big>${tot:.2f}</div>Saldo ${data['b']:.2f} <span style='color:{col}'>Flot {flot:+.2f}$</span> Pos {len(data["pos"])}/6 | Hist ${data.get('gan_total',0):.2f}</div>
    <div class=card><div class=gold>POSICIONES - TOCA PARA VER GRÁFICA VIVA</div>{pos_html}</div>
    <div class=card><div class=gold>6 MONEDAS - TOCA CUALQUIERA → GRÁFICA EN VIVO REAL</div><div class=grid>{coins}</div></div>
    <div class=card><div class=gold>Total NETO - Línea Verde</div><canvas id='c1'></canvas></div>
    <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
    <script>fetch('/api/history').then(r=>r.json()).then(d=>{{new Chart(document.getElementById('c1'),{{type:'line',data:{{labels:d.time,datasets:[{{label:'Total NETO',data:d.total,borderColor:'#22c55e',borderWidth:3,tension:0.4}}]}},options:{{responsive:true}}}});}}); setTimeout(()=>location.reload(),25000);</script>
    """

@app.route("/chart/<sym>")
def chart(sym):
    sym=sym.upper(); entry=0; monto=0
    for p in data["pos"]:
        if p["sym"]==sym: entry=p.get("precio_entry",p.get("entry",0)); monto=p.get("monto",p.get("amt",0)); break
    tot,flot=totals()
    return f"""
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{{background:#080808;color:#fff;margin:0;font-family:Arial}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #ffcc00}}.live{{background:#00ff88;color:#000;padding:3px 8px;border-radius:12px;font-size:10px;font-weight:900;animation:blink 1s infinite}} @keyframes blink{{0%{{opacity:1}}50%{{opacity:.3}}100%{{opacity:1}}}} #info{{padding:10px;background:#151515;display:flex;gap:12px;overflow:auto}}.box{{background:#222;padding:8px 12px;border-radius:10px;white-space:nowrap}} button{{background:#ffcc00;padding:8px 14px;border:none;border-radius:8px;font-weight:800}}</style>
</head><body>
<div class=top><div><b>{sym} V41 VIVA</b> <span class=live>● VIVO</span><br><small style=color:#00ff88>Entrada ${entry:.2f} ${monto}</small></div><a href="/"><button>Volver</button></a></div>
<div id=info><div class=box>Precio: <b id=pv>--</b></div><div class=box>RSI: <b id=rsi>--</b></div><div class=box>Gan: <b id=gan>--</b></div><div class=box>Total: <b>${tot:.2f}</b></div></div>
<div id=chart style=width:100%;height:78vh></div>
<script>
const SYM="{sym}"; const ENTRY={entry};
const map={{'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT'}};
const binSym=map[SYM]||'BTCUSDT';
let chart,candleSeries,lastCandle;
async function init(){{
 const el=document.getElementById('chart');
 chart=LightweightCharts.createChart(el,{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});
 candleSeries=chart.addCandlestickSeries({{upColor:'#00ff88',downColor:'#ff4444',wickUpColor:'#00ff88',wickDownColor:'#ff4444'}});
 let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1m&limit=150`);
 let kl=await r.json(); let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));
 candleSeries.setData(data); lastCandle=data[data.length-1];
 if(ENTRY>0){{let l=chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); l.setData(data.map(x=>({{time:x.time,value:ENTRY}})));}}
 chart.timeScale().fitContent();
 setInterval(updateLive,3000);
}}
async function updateLive(){{
 try{{let r=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${{binSym}}`); let p=+(await r.json()).price; let now=Math.floor(Date.now()/1000);
 if(lastCandle){{let nc={{time:now,open:lastCandle.close,high:Math.max(lastCandle.high,p),low:Math.min(lastCandle.low,p),close:p}}; candleSeries.update(nc); if(now-lastCandle.time>=60) lastCandle=nc;}}
 document.getElementById('pv').innerText='$'+p.toFixed(2);
 if(ENTRY>0){{let pct=((p-ENTRY)/ENTRY*100).toFixed(2); let gan=({monto or 600}*(p-ENTRY)/ENTRY).toFixed(2); document.getElementById('gan').innerText=pct+'% $'+gan; document.getElementById('gan').style.color=p>=ENTRY?'#00ff88':'#ff4444';}}
 }}catch(e){{}}
}}
init();
</script></body></html>"""

@app.route("/api/history")
def api_h(): return jsonify({k:list(v) for k,v in history.items()})
@app.route("/api/estado")
def estado(): tot,flot=totals(); return jsonify({'b':data['b'],'pos':data['pos'],'total':tot,'flot':flot,'prices':prices})
@app.route("/reset")
def reset_route(): data['b']=5000; data['pos']=[]; data['gan_total']=0; save(); return jsonify({'status':'RESET'})

def auto_loop():
    while True:
        try:
            for sym in ALL_COINS:
                pr=P(sym)
                if pr==0: continue
                prices[sym]=pr
                for p in list(data["pos"]):
                    if p["sym"]!=sym: continue
                    entry=p.get("precio_entry",p.get("entry",0)); pct=(pr-entry)/entry*100 if entry else 0
                    if pct>=1.3 or pct<=-18:
                        amt=p.get("monto",p.get("amt",0)); com=amt*0.006; neto=amt*pct/100-com
                        data["b"]+=amt+neto; data["gan_total"]+=neto; data["pos"].remove(p); save()
                if not data.get("auto") or len(data["pos"])>=6: continue
                cnt=sum(1 for x in data["pos"] if x["sym"]==sym)
                if cnt>=2 or data["b"]-1500<600: continue
                if rsis.get(sym,50)<42:
                    amt=600 if cnt==0 else 850
                    data["pos"].append({"sym":sym,"monto":amt,"precio_entry":pr,"entry":pr,"nivel":cnt+1}); data["b"]-=amt; save()
            tot,flot=totals()
            history['time'].append(datetime.now().strftime("%H:%M:%S")); history['total'].append(round(tot,2)); history['flot'].append(round(flot,2))
            time.sleep(10)
        except: time.sleep(5)

@bot.message_handler(commands=['start','balance','b','dashboard'])
def cmd_bal(m): tot,flot=totals(); bot.send_message(m.chat.id,f"V41.0 GRAFICAS VIVAS 🔥\nTotal ${tot:.2f}\nSaldo ${data['b']:.2f} Flot {flot:+.2f}$\nhttps://telegram-bot-cijp.onrender.com")

@bot.message_handler(func=lambda m: True)
def all_h(m):
    t=m.text.strip().upper()
    if t in ALL_COINS or "RESET" in t or "AUTO" in t:
        if "RESET" in t: data['b']=5000; data['pos']=[]; data['gan_total']=0; save(); bot.send_message(m.chat.id,"RESETEADO $5000")
        elif t=="AUTO ON": data['auto']=True; save()
        elif t=="AUTO OFF": data['auto']=False; save()
    tot,flot=totals(); bot.send_message(m.chat.id,f"V41.0 GRAFICAS VIVAS 🔥\nhttps://telegram-bot-cijp.onrender.com\nTotal ${tot:.2f} Saldo ${data['b']:.2f} Flot {flot:+.2f}$")

def tg_polling():
    while True:
        try: bot.infinity_polling(timeout=20, long_polling_timeout=30)
        except: time.sleep(5)

load()
threading.Thread(target=auto_loop,daemon=True).start()
threading.Thread(target=tg_polling,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
