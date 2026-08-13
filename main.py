# V42.0 CUERPO COMPLETO RESTAURADO - V36.1 PODEROSA + TP/SL TODAS
import os, requests, threading, time
from flask import Flask, request, send_from_directory
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "AQUI_TU_TOKEN"
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["XAUUSD","BTC","NVDA","TSLA","ETH","SOL"]
SALDO_INICIAL = 5000
MAX_POS = 8

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10)
        if r.status_code==200:
            d=r.json()
            if d.get("b",0) < 1000 and len(d.get("pos",[]))==0: d["b"]=5000
            d.setdefault("pos",[]); d.setdefault("alert_users",[]); d.setdefault("auto",True); d.setdefault("gan_total",0)
            return d
    except: pass
    return {"b":SALDO_INICIAL,"pos":[],"alert_users":[],"auto":True,"gan_total":0}
data=load()

def P(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        if sym in mp:
            return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=4).json()["price"])
        import yfinance as yf
        return float(yf.Ticker({"NVDA":"NVDA","TSLA":"TSLA"}.get(sym,sym)).history(period='1d')['Close'].iloc[-1])
    except: return 0

def C(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={mp.get(sym,'BTCUSDT')}&interval=1h&limit=80",timeout=5).json()
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
        pr=P(p["sym"])
        if pr>0:
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
    mult={1:1, 2:1.2, 3:1.5}
    return int(base*mult.get(nivel,1))

def save():
    if len(data["pos"])==0 and data["b"]<4000: data["b"]=5000
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass

@app.route("/logo.png")
def logo(): return send_from_directory(".","logo.png")

@app.route("/")
def dash():
    tot,flot=totals()
    col="#00ff88" if flot>=0 else "#ff4444"
    pos_html=""
    for p in data["pos"]:
        pr=P(p["sym"]); pct=((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"]>0 else 0
        tp=p["precio_entry"]*1.013; sl=p["precio_entry"]*0.82
        trail=f"<br><small style='color:#00ccff'>TRAILING max ${p.get('max_price',pr):.1f} | TP ${tp:.1f} SL ${sl:.1f}</small>" if pct>1 else f"<br><small>TP ${tp:.1f} SL ${sl:.1f}</small>"
        pos_html+=f"<div onclick=\"window.location='/chart/{p['sym']}'\" style='display:flex;justify-content:space-between;padding:14px;border-bottom:1px solid #222;cursor:pointer'><div><b>{p['sym']} N{p.get('nivel',1)} ${p['monto']}</b> <span style='font-size:11px'>${p['precio_entry']:.1f}→${pr:.1f} {pct:+.1f}%</span>{trail}</div><span style='color:{col}'>{p.get('gan',0):+.2f}$</span></div>"
    if not pos_html: pos_html=f"<div style='padding:20px;text-align:center;opacity:.5'>Sin pos - esperando RSI<32<br>N1 ${get_monto(1)} N2 ${get_monto(2)} N3 ${get_monto(3)}</div>"
    coins=""
    for s in ALL_COINS:
        pr=P(s); rsi=RSI(C(s)); count=sum(1 for x in data["pos"] if x["sym"]==s)
        c2="#ffcc00" if rsi<32 else "#444"
        coins+=f"<div onclick=\"window.location='/chart/{s}'\" style='background:#151515;border:2px solid {c2};border-radius:14px;padding:10px;cursor:pointer'><b>{s} {count}/3</b><br>${pr:.1f}<br>RSI {rsi:.0f}<br><small style='color:#00ff88'>N1 {get_monto(1)}$</small><br><small style='font-size:9px;color:#00ccff'>TP/SL VIVO ►</small></div>"
    return f"""<meta name=viewport content="width=device-width,initial-scale=1"><style>body{{background:#080808;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border-radius:20px;padding:16px;margin-bottom:12px;border:1px solid #222}}.gold{{color:#ffcc00;font-weight:800;font-size:12px}}.big{{font-size:34px;font-weight:900}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.power{{background:linear-gradient(90deg,#ffcc00,#ff4400);color:#000;padding:5px 12px;border-radius:20px;font-weight:900;font-size:11px}}.logo{{width:110px;height:110px;border-radius:50%;border:3px solid #ffcc00;box-shadow:0 0 25px rgba(255,204,0,.4)}}</style>
    <div class=card style=text-align:center><img src="/logo.png" onerror="this.style.display='none'" class=logo><br><br><div class=gold>V42.0 PODEROSA CUERPO COMPLETO <span class=power>🔥 TP/SL EN TODAS</span></div><div class=big>${tot:.2f}</div>Saldo ${data['b']:.2f} <span style='color:{col}'>Flot {flot:+.2f}$</span> Pos {len(data['pos'])}/{MAX_POS}<br><small>Bola 10% | Pirámide N1 1x N2 1.2x N3 1.5x | Trailing 3% | TP 1.3% SL -18%</small></div>
    <div class=card><div class=gold>POSICIONES - TOCA PARA VER GRÁFICA VIVA CON TP/SL</div>{pos_html}</div>
    <div class=card><div class=gold>6 MONEDAS - TOCA CUALQUIERA → GRÁFICA VIVA CON TP/SL</div><div class=grid>{coins}</div></div>"""

@app.route("/chart/<sym>")
def chart(sym):
    sym=sym.upper(); entry=0; nivel=1; monto=0
    for p in data["pos"]:
        if p["sym"]==sym: entry=p.get("precio_entry",0); nivel=p.get("nivel",1); monto=p.get("monto",0); break
    tp=entry*1.013 if entry else 0; sl=entry*0.82 if entry else 0
    tot,flot=totals()
    return f"""
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{{background:#080808;color:#fff;margin:0;font-family:Arial}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between;border-bottom:2px solid #ffcc00}}.live{{background:#00ff88;color:#000;padding:3px 8px;border-radius:12px;font-size:10px;font-weight:900;animation:blink 1s infinite}}@keyframes blink{{0%{{opacity:1}}50%{{opacity:.3}}100%{{opacity:1}}}}#info{{padding:10px;background:#151515;display:flex;gap:6px;overflow:auto;flex-wrap:wrap}}.box{{background:#222;padding:8px 12px;border-radius:10px;font-size:12px}}button{{background:#ffcc00;padding:8px 14px;border:none;border-radius:8px;font-weight:800}}</style>
</head><body>
<div class=top><div><b>{sym} V42 TP/SL VIVO</b> <span class=live>● VIVO</span><br><small style=color:#00ff88>Entrada ${entry:.2f} N{nivel} ${monto} | TP ${tp:.2f} +1.3% | SL ${sl:.2f} -18%</small></div><a href="/"><button>Volver</button></a></div>
<div id=info><div class=box>Precio: <b id=pv>--</b></div><div class=box style='background:#002a00;color:#00ff88;border:1px solid #00ff88'>TP: <b>${tp:.2f}</b></div><div class=box style='background:#2a0000;color:#ff4444;border:1px solid #ff4444'>SL: <b>${sl:.2f}</b></div><div class=box>RSI: <b id=rsi>--</b></div><div class=box>Gan: <b id=gan>--</b></div><div class=box>Total: <b>${tot:.2f}</b></div></div>
<div id=chart style=width:100%;height:75vh></div>
<script>
const SYM="{sym}"; const ENTRY={entry}; const TP={tp}; const SL={sl};
const map={{'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT'}};
const binSym=map[SYM]||'BTCUSDT';
let chart,candleSeries,lastCandle;
async function init(){{
 const el=document.getElementById('chart');
 chart=LightweightCharts.createChart(el,{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});
 candleSeries=chart.addCandlestickSeries({{upColor:'#00ff88',downColor:'#ff4444'}});
 let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1m&limit=150`);
 let kl=await r.json(); let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));
 candleSeries.setData(data); lastCandle=data[data.length-1];
 if(ENTRY>0){{
   let e=chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2,title:'ENTRADA'}}); e.setData(data.map(x=>({{time:x.time,value:ENTRY}})));
   let t=chart.addLineSeries({{color:'#00ff88',lineWidth:3,lineStyle:0,title:'TP 1.3%'}}); t.setData(data.map(x=>({{time:x.time,value:TP}})));
   let s=chart.addLineSeries({{color:'#ff4444',lineWidth:2,lineStyle:2,title:'SL -18%'}}); s.setData(data.map(x=>({{time:x.time,value:SL}})));
 }}
 chart.timeScale().fitContent();
 updateInfo(); setInterval(updateLive,3000);
}}
async function updateLive(){{
 try{{let r=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${{binSym}}`); let p=+(await r.json()).price; let now=Math.floor(Date.now()/1000);
 if(lastCandle){{let nc={{time:now,open:lastCandle.close,high:Math.max(lastCandle.high,p),low:Math.min(lastCandle.low,p),close:p}}; candleSeries.update(nc); if(now-lastCandle.time>=60) lastCandle=nc;}}
 document.getElementById('pv').innerText='$'+p.toFixed(2);
 if(ENTRY>0){{let pct=((p-ENTRY)/ENTRY*100).toFixed(2); let gan=({monto or 500}*(p-ENTRY)/ENTRY).toFixed(2); document.getElementById('gan').innerText=pct+'% $'+gan;}}
 }}catch(e){{}}
}}
async function updateInfo(){{
 try{{let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1h&limit=20`); let kl=await r.json(); let closes=kl.map(x=>+x[4]); let g=0,l=0; for(let i=1;i<15;i++){{let d=closes[closes.length-i]-closes[closes.length-i-1]; if(d>0) g+=d; else l+=-d;}} let rsi=100-(100/(1+g/(l||1))); document.getElementById('rsi').innerText=rsi.toFixed(0);}}catch(e){{}}
}}
init();
</script></body></html>"""

@app.route(f"/{TOKEN}", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode("utf-8"))]); return "ok"

@bot.message_handler(func=lambda m: True)
def h(m):
    txt=(m.text or "").upper().strip(); uid=m.chat.id
    if uid not in data["alert_users"]: data["alert_users"].append(uid)
    if "RESET5K" in txt:
        data["b"]=5000; data["pos"]=[]; save(); bot.send_message(uid,"✅ V42.0 CUERPO COMPLETO RESTAURADO + TP/SL TODAS $5000")
    elif any(k in txt for k in ["DASH","BALANCE","SALDO","START","HOLA","B"]):
        tot,flot=totals(); bot.send_message(uid,f"V42.0 PODEROSA CUERPO COMPLETO 🔥 TP/SL\nhttps://telegram-bot-cijp.onrender.com\nTotal ${tot:.2f} Saldo ${data['b']:.2f} Flot {flot:+.2f}$\nPos {len(data['pos'])}/{MAX_POS}\nN1 ${get_monto(1)} N2 ${get_monto(2)} N3 ${get_monto(3)}\nToca moneda para grafica viva con TP/SL")
    elif txt in ALL_COINS:
        if len(data["pos"])>=MAX_POS: bot.send_message(uid,"❌ Lleno 8/8")
        else:
            nivel=sum(1 for x in data["pos"] if x["sym"]==txt)+1
            if nivel>3: bot.send_message(uid,f"❌ {txt} ya 3/3 niveles")
            else:
                monto=get_monto(nivel)
                if data["b"]<monto: bot.send_message(uid,f"❌ Saldo ${data['b']:.2f} necesita ${monto} N{nivel}")
                else:
                    pr=P(txt); data["pos"].append({"sym":txt,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
                    bot.send_message(uid,f"✅ V42 N{nivel} {txt} ${pr:.2f} x ${monto}\nTP ${pr*1.013:.2f} SL ${pr*0.82:.2f}\nGrafica: https://telegram-bot-cijp.onrender.com/chart/{txt}")

def auto_loop():
    while True:
        try:
            if data.get("auto"):
                tot,flot=totals()
                for p in list(data["pos"]):
                    pr=P(p["sym"])
                    if pr==0: continue
                    pct=(pr-p["precio_entry"])/p["precio_entry"]*100
                    max_p=p.get("max_price",pr)
                    # TP 1.3% o Trailing 3% despues de +4%
                    if pct>=1.3 or (pct>4 and pr < max_p*0.97) or pct<=-18:
                        gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        data["b"]+=p["monto"]+gan; data["gan_total"]+=gan; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"💰 CIERRE {p['sym']} N{p.get('nivel',1)} {pct:+.1f}% Gan ${gan:.2f} | TP ${p['precio_entry']*1.013:.1f}")
                            except: pass
                for sym in ALL_COINS:
                    closes=C(sym); rsi=RSI(closes); pr=P(sym)
                    if pr==0: continue
                    count=sum(1 for x in data["pos"] if x["sym"]==sym)
                    if count>=3 or len(data["pos"])>=MAX_POS: continue
                    nivel=count+1; monto=get_monto(nivel)
                    if data["b"]<monto: continue
                    should=False
                    if count==0 and rsi<32: should=True
                    elif count>0:
                        entries=[x["precio_entry"] for x in data["pos"] if x["sym"]==sym]
                        avg=sum(entries)/len(entries)
                        if count==1 and rsi<28 and pr < avg*0.95: should=True
                        if count==2 and rsi<22 and pr < avg*0.90: should=True
                    if should:
                        data["pos"].append({"sym":sym,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
            time.sleep(60)
        except: time.sleep(20)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
