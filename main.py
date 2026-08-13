# V42.1 FIX ERROR 500 - ANTI-CRASH + TP/SL TODAS + CUERPO COMPLETO
import os, requests, threading, time, traceback
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "AQUI_TU_TOKEN"
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["XAUUSD","BTC","NVDA","TSLA","ETH","SOL"]

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)
try: bot.delete_webhook(drop_pending_updates=True)
except: pass

data={"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0}
prices={}

def P(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        if sym in mp:
            r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=5)
            return float(r.json()["price"])
        return {"NVDA":183.5,"TSLA":248.0}.get(sym,100.0)
    except: return prices.get(sym,100.0)

def C(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={mp.get(sym,'BTCUSDT')}&interval=1h&limit=80",timeout=6).json()
        return [float(x[4]) for x in r]
    except: return []

def RSI(a):
    if len(a)<15: return 40
    g=l=0
    for i in range(1,15):
        d=a[-i]-a[-i-1]
        if d>0: g+=d
        else: l+=-d
    return 100-(100/(1+g/(l or 1))) if l!=0 else 70

def totals():
    flot=0
    for p in data["pos"]:
        pr=prices.get(p["sym"], p.get("precio_entry",0))
        if pr>0 and p.get("precio_entry",0)>0:
            p["gan"]=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
            if "max_price" not in p: p["max_price"]=pr
            if pr>p["max_price"]: p["max_price"]=pr
            flot+=p["gan"]
    return data["b"]+flot, flot

def get_monto(nivel=1):
    tot,_=totals()
    base=int(tot*0.10)
    if base<500: base=500
    if base>1500: base=1500
    mult={1:1,2:1.2,3:1.5}
    return int(base*mult.get(nivel,1))

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10)
        if r.status_code==200:
            d=r.json()
            if d.get("b",0)<1000 and len(d.get("pos",[]))==0: d["b"]=5000
            d.setdefault("pos",[]); d.setdefault("alert_users",[]); d.setdefault("auto",True); d.setdefault("gan_total",0)
            return d
    except: pass
    return {"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0}
data=load()

def save():
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass

@app.route("/")
def dash():
    try:
        tot,flot=totals()
        col="#00ff88" if flot>=0 else "#ff4444"
        pos_html=""
        for p in data["pos"]:
            pr=prices.get(p["sym"], p.get("precio_entry",0))
            pct=((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"] else 0
            tp=p["precio_entry"]*1.013; sl=p["precio_entry"]*0.82
            pos_html+=f"<div onclick=\"location='/chart/{p['sym']}'\" style='display:flex;justify-content:space-between;padding:14px;border-bottom:1px solid #222'><div><b>{p['sym']} N{p.get('nivel',1)} ${p['monto']}</b> {pct:+.1f}%<br><small>TP ${tp:.1f} SL ${sl:.1f}</small></div><span style='color:{col}'>{p.get('gan',0):+.2f}$</span></div>"
        if not pos_html: pos_html=f"<div style='padding:20px;text-align:center;opacity:.5'>Sin pos - N1 ${get_monto(1)} N2 ${get_monto(2)} N3 ${get_monto(3)}</div>"
        coins=""
        for s in ALL_COINS:
            try:
                pr=P(s); prices[s]=pr
                rsi=RSI(C(s)); count=sum(1 for x in data["pos"] if x["sym"]==s)
                c2="#ffcc00" if rsi<32 else "#333"
                coins+=f"<div onclick=\"location='/chart/{s}'\" style='background:#151515;border:2px solid {c2};border-radius:14px;padding:10px'><b>{s} {count}/3</b><br>${pr:.1f}<br>RSI {rsi:.0f}<br><small style='color:#00ccff'>TP/SL VIVO ►</small></div>"
            except: coins+=f"<div style='background:#151515;padding:10px;border-radius:14px'><b>{s}</b><br>--</div>"
        return f"""<meta name=viewport content="width=device-width,initial-scale=1"><style>body{{background:#080808;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border-radius:20px;padding:16px;margin-bottom:12px;border:1px solid #222}}.gold{{color:#ffcc00;font-weight:800}}.big{{font-size:32px;font-weight:900}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}</style>
        <div class=card style=text-align:center><div class=gold>V42.1 FIX ERROR 500 - CUERPO COMPLETO TP/SL</div><div class=big>${tot:.2f}</div>Saldo ${data['b']:.2f} <span style='color:{col}'>Flot {flot:+.2f}$</span> Pos {len(data['pos'])}/8<br><small>Bola 10% | N1 1x N2 1.2x N3 1.5x | Trailing 3% | TP 1.3% SL -18%</small></div>
        <div class=card><div class=gold>POSICIONES - TOCA PARA VER TP/SL</div>{pos_html}</div>
        <div class=card><div class=gold>6 MONEDAS - TP/SL VIVO</div><div class=grid>{coins}</div></div>"""
    except Exception as e:
        return f"<pre>ERROR FIX: {e}\n{traceback.format_exc()}</pre>"

@app.route("/chart/<sym>")
def chart(sym):
    sym=sym.upper(); entry=0; monto=0
    for p in data["pos"]:
        if p["sym"]==sym: entry=p.get("precio_entry",0); monto=p.get("monto",0); break
    tp=entry*1.013 if entry else 0; sl=entry*0.82 if entry else 0
    tot,_=totals()
    return f"""
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{{background:#080808;color:#fff;margin:0;font-family:Arial}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between;border-bottom:2px solid #ffcc00}}.live{{background:#00ff88;color:#000;padding:3px 8px;border-radius:12px;font-size:10px;font-weight:900}}.box{{background:#222;padding:8px 12px;border-radius:10px;font-size:12px}}button{{background:#ffcc00;padding:8px 14px;border:none;border-radius:8px;font-weight:800}}</style>
</head><body>
<div class=top><div><b>{sym} TP/SL VIVO</b> <span class=live>● VIVO</span><br><small>Entrada ${entry:.2f} | TP ${tp:.2f} +1.3% | SL ${sl:.2f} -18%</small></div><a href="/"><button>Volver</button></a></div>
<div style='padding:10px;background:#151515;display:flex;gap:6px;overflow:auto'><div class=box>Precio: <b id=pv>--</b></div><div class=box style='background:#002a00;color:#00ff88'>TP ${tp:.2f}</div><div class=box style='background:#2a0000;color:#ff4444'>SL ${sl:.2f}</div><div class=box>Gan: <b id=gan>--</b></div></div>
<div id=chart style=width:100%;height:80vh></div>
<script>
const ENTRY={entry}; const TP={tp}; const SL={sl};
const map={{'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT'}};
const binSym=map["{sym}"]||'BTCUSDT';
let chart,candleSeries,lastCandle;
async function init(){{
 const el=document.getElementById('chart');
 chart=LightweightCharts.createChart(el,{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});
 candleSeries=chart.addCandlestickSeries({{upColor:'#00ff88',downColor:'#ff4444'}});
 let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1m&limit=150`);
 let kl=await r.json(); let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));
 candleSeries.setData(data); lastCandle=data[data.length-1];
 if(ENTRY>0){{
   let e=chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); e.setData(data.map(x=>({{time:x.time,value:ENTRY}})));
   let t=chart.addLineSeries({{color:'#00ff88',lineWidth:3}}); t.setData(data.map(x=>({{time:x.time,value:TP}})));
   let s=chart.addLineSeries({{color:'#ff4444',lineWidth:2,lineStyle:2}}); s.setData(data.map(x=>({{time:x.time,value:SL}})));
 }}
 chart.timeScale().fitContent(); setInterval(updateLive,3000);
}}
async function updateLive(){{
 try{{let r=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${{binSym}}`); let p=+(await r.json()).price; let now=Math.floor(Date.now()/1000);
 if(lastCandle){{let nc={{time:now,open:lastCandle.close,high:Math.max(lastCandle.high,p),low:Math.min(lastCandle.low,p),close:p}}; candleSeries.update(nc);}}
 document.getElementById('pv').innerText='$'+p.toFixed(2);
 if(ENTRY>0){{let pct=((p-ENTRY)/ENTRY*100).toFixed(2); let gan=({monto or 500}*(p-ENTRY)/ENTRY).toFixed(2); document.getElementById('gan').innerText=pct+'% $'+gan;}}
 }}catch(e){{}}
}}
init();
</script></body></html>"""

@app.route("/logo.png")
def logo():
    return "",204

@app.route(f"/{TOKEN}", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    try: bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode("utf-8"))])
    except: pass
    return "ok"

@bot.message_handler(func=lambda m: True)
def h(m):
    txt=(m.text or "").upper().strip()
    if "RESET5K" in txt: data["b"]=5000; data["pos"]=[]; save()
    tot,flot=totals()
    bot.send_message(m.chat.id,f"V42.1 FIX 500 OK 🔥\nhttps://telegram-bot-cijp.onrender.com\nTotal ${tot:.2f} Flot {flot:+.2f}$\nN1 ${get_monto(1)} N2 ${get_monto(2)} N3 ${get_monto(3)}")

def auto_loop():
    while True:
        try:
            if data.get("auto"):
                for p in list(data["pos"]):
                    pr=P(p["sym"]); prices[p["sym"]]=pr
                    if pr==0: continue
                    pct=(pr-p["precio_entry"])/p["precio_entry"]*100
                    max_p=p.get("max_price",pr)
                    if pct>=1.3 or (pct>4 and pr < max_p*0.97) or pct<=-18:
                        gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        data["b"]+=p["monto"]+gan; data["gan_total"]+=gan; data["pos"].remove(p); save()
                for sym in ALL_COINS:
                    pr=P(sym); prices[sym]=pr
                    if pr==0: continue
                    closes=C(sym); rsi=RSI(closes)
                    count=sum(1 for x in data["pos"] if x["sym"]==sym)
                    if count>=3 or len(data["pos"])>=MAX_POS: continue
                    monto=get_monto(count+1)
                    if data["b"]<monto: continue
                    should=False
                    if count==0 and rsi<32: should=True
                    elif count>0:
                        avg=sum([x["precio_entry"] for x in data["pos"] if x["sym"]==sym])/count
                        if count==1 and rsi<28 and pr < avg*0.95: should=True
                        if count==2 and rsi<22 and pr < avg*0.90: should=True
                    if should:
                        data["pos"].append({"sym":sym,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":count+1}); data["b"]-=monto; save()
            time.sleep(60)
        except: time.sleep(20)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
