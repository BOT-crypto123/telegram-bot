import os, requests, threading, time
from datetime import datetime, timedelta
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "123456:TEST"
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["NVDA","TSLA","BTC","XAUUSD","ETH","SOL"] # ORDEN CONCENTRADO COMO TU FOTO
MAX_POS = 8

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

LAST_PRICE = {"XAUUSD":3350,"BTC":108500,"ETH":2650,"SOL":145,"NVDA":183.5,"TSLA":248.2}
last_report_date = ""

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10)
        if r.status_code==200:
            d=r.json()
            if d.get("b",0) < 1000 and len(d.get("pos",[]))==0: d["b"]=5000
            d.setdefault("pos",[]); d.setdefault("alert_users",[]); d.setdefault("auto",True); d.setdefault("gan_total",0)
            return d
    except: pass
    return {"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0}

data=load()

def P(sym):
    global LAST_PRICE
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XAUUSD":"pax-gold"}
        if sym in cg:
            r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg[sym]}&vs_currencies=usd",timeout=5).json()
            price=float(r[cg[sym]]["usd"])
            if price>0: LAST_PRICE[sym]=price; return price
    except: pass
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        if sym in mp:
            r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=3).json()
            price=float(r["price"])
            if price>0: LAST_PRICE[sym]=price; return price
    except: pass
    return LAST_PRICE.get(sym,100)

def C(sym):
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        s=mp.get(sym)
        if not s: return []
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=80",timeout=5).json()
        return [float(x[4]) for x in r]
    except: return []

def RSI(a):
    if len(a)<15: return 40
    g=l=0
    for i in range(1,15):
        d=a[-i]-a[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 70
    return 100-(100/(1+g/l))

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

# V34 CONCENTRADO - MONTO FIJO GRANDE
def get_monto(nivel=1):
    if nivel==1: return 500
    if nivel==2: return 750
    if nivel==3: return 750
    return 750

def save():
    if len(data["pos"])==0 and data["b"]<4000: data["b"]=5000
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass

@app.route("/")
def dash():
    tot,flot=totals()
    col="#00ff88" if flot>=0 else "#ff4444"
    pos_html=""
    for p in data["pos"]:
        pr=P(p["sym"])
        pct=((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"]>0 else 0
        pos_html+=f"<div onclick=\"window.location='/chart/{p['sym']}'\" style='display:flex;justify-content:space-between;padding:14px;border-bottom:1px solid #222;cursor:pointer'><div><b>{p['sym']} N{p.get('nivel',1)} ${p['monto']}</b> ${p['precio_entry']:.1f}→${pr:.1f} {pct:+.1f}%</div><span style='color:{col}'>{p.get('gan',0):+.2f}$</span></div>"
    if not pos_html: pos_html=f"<div style='padding:20px;text-align:center;opacity:.5'>V37 CONCENTRADO LISTO<br>Esperando RSI<45 - ABRIRA 6 HOY<br>N1 $500 N2 $750 N3 $750<br>AUTO {'ON 🔥' if data.get('auto') else 'OFF'}</div>"
    coins=""
    for s in ALL_COINS:
        pr=P(s); rsi=RSI(C(s)); count=sum(1 for x in data["pos"] if x["sym"]==s)
        c2="#ffcc00" if rsi<45 else "#333"
        coins+=f"<div onclick=\"window.location='/chart/{s}'\" style='background:#151515;border:2px solid {c2};border-radius:14px;padding:10px;cursor:pointer'><b>{s} {count}/2</b><br>${pr:.1f}<br>RSI {rsi:.0f}<br><small style='color:#00ff88'>N{count+1} ${get_monto(count+1)}$</small></div>"
    return f"""<meta name=viewport content="width=device-width,initial-scale=1"><style>body{{background:#080808;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border-radius:20px;padding:16px;margin-bottom:12px;border:1px solid #222}}.gold{{color:#ffcc00;font-weight:800;font-size:12px}}.big{{font-size:34px;font-weight:900}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}</style>
    <div class=card style=text-align:center><div style=font-size:12px;color:#ffcc00;font-weight:900>V37 CONCENTRADO DINERO VIVO 🔥</div><div class=gold>V34 LOGICA + STOP + TRAILING 1%</div><div class=big>${tot:.2f}</div>Saldo ${data['b']:.2f} <span style='color:{col}'>Flot {flot:+.2f}$</span> Pos {len(data['pos'])}/{MAX_POS}</div>
    <div class=card><div class=gold>POSICIONES - TOCA PARA GRAFICA</div>{pos_html}</div>
    <div class=card><div class=gold>6 MEJORES - MAX 2 POR MONEDA</div><div class=grid>{coins}</div></div>"""

@app.route("/chart/<sym>")
def chart(sym):
    sym=sym.upper(); entry=0; monto=500
    for p in data["pos"]:
        if p["sym"]==sym: entry=p.get("precio_entry",0); monto=p.get("monto",0); break
    tot,_=totals()
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{{background:#080808;color:#fff;margin:0;font-family:Arial}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between;border-bottom:2px solid #ffcc00}}.live{{background:#00ff88;color:#000;padding:3px 8px;border-radius:12px;font-size:10px;font-weight:900}} #info{{padding:10px;background:#151515;display:flex;gap:12px;overflow:auto}}.box{{background:#222;padding:8px 12px;border-radius:10px;white-space:nowrap}} button{{background:#ffcc00;padding:8px 14px;border:none;border-radius:8px;font-weight:800}}</style></head><body>
<div class=top><div><b>{sym} V37</b> <span class=live>● VIVO</span><br><small>Ent ${entry:.2f} ${monto}</small></div><a href="/"><button>Volver</button></a></div>
<div id=info><div class=box>Precio: <b id=pv>--</b></div><div class=box>RSI: <b id=rsi>--</b></div><div class=box>Gan: <b id=gan>--</b></div><div class=box>Total: <b>${tot:.2f}</b></div></div>
<div id=chart style=width:100%;height:75vh></div>
<script>
const SYM="{sym}"; const ENTRY={entry}; const MONTO={monto};
const map={{'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT'}};
const binSym=map[SYM]||'BTCUSDT';
let chart, candleSeries, lastCandle;
async function init(){{
 chart=LightweightCharts.createChart(document.getElementById('chart'),{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}},crosshair:{{mode:1}}}});
 candleSeries=chart.addCandlestickSeries({{upColor:'#00ff88',downColor:'#ff4444',wickUpColor:'#00ff88',wickDownColor:'#ff4444'}});
 let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1m&limit=150`);
 let kl=await r.json();
 let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));
 candleSeries.setData(data); lastCandle=data[data.length-1];
 if(ENTRY>0){{ let l=chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); l.setData(data.map(x=>({{time:x.time,value:ENTRY}}))) }}
 chart.timeScale().fitContent(); setInterval(updateLive,3000); updateInfo();
}}
async function updateLive(){{
 try{{ let r=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${{binSym}}`); let p=+(await r.json()).price; let now=Math.floor(Date.now()/1000);
   let newC={{time:now,open:lastCandle.close,high:Math.max(lastCandle.high,p),low:Math.min(lastCandle.low,p),close:p}};
   candleSeries.update(newC); if(now-lastCandle.time>=60) lastCandle=newC;
   document.getElementById('pv').innerText='$'+p.toFixed(2);
   if(ENTRY>0){{ let pct=((p-ENTRY)/ENTRY*100).toFixed(2); let gan=(MONTO*(p-ENTRY)/ENTRY).toFixed(2); let el=document.getElementById('gan'); el.innerText=pct+'% $'+gan; el.style.color=p>=ENTRY?'#00ff88':'#ff4444'; }}
 }}catch(e){{}}
}}
async function updateInfo(){{ try{{ let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1h&limit=20`); let kl=await r.json(); let closes=kl.map(x=>+x[4]); let g=0,l=0; for(let i=1;i<15;i++){{ let d=closes[closes.length-i]-closes[closes.length-i-1]; if(d>0) g+=d; else l+=-d; }} let rsi=100-(100/(1+g/(l||1))); document.getElementById('rsi').innerText=rsi.toFixed(0); }}catch(e){{}} }}
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
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("BTC","ETH","SOL")
    markup.row("XAUUSD","NVDA","TSLA")
    markup.row("DASHBOARD","AUTO ON","AUTO OFF")

    if "RESET5K CONFIRMAR" in txt:
        data["b"]=5000; data["pos"]=[]; data["gan_total"]=0; save()
        bot.send_message(uid,"✅ DEMO $5000 REINICIADO V37", reply_markup=markup); return
    elif "RESET5K" in txt: bot.send_message(uid,"⚠️ Escribe RESET5K CONFIRMAR", reply_markup=markup); return

    if any(k in txt for k in ["DASH","BALANCE","SALDO","START","HOLA"]):
        tot,flot=totals()
        bot.send_message(uid,f"V37 CONCENTRADO DINERO VIVO 🔥\n💰 Total ${tot:.2f}\nSaldo ${data['b']:.2f} Flot {flot:+.2f}$\nPos {len(data['pos'])}/{MAX_POS}\nAUTO {'ON 🔥' if data.get('auto') else 'OFF'}\nGan Hist ${data.get('gan_total',0):.2f}\nN1 $500 N2 $750 N3 $750\nResumen 10pm ON\nhttps://telegram-bot-cijp.onrender.com", reply_markup=markup)
    elif txt in ALL_COINS:
        if len(data["pos"])>=MAX_POS: bot.send_message(uid,"❌ Lleno 8/8", reply_markup=markup)
        else:
            nivel=sum(1 for x in data["pos"] if x["sym"]==txt)+1
            if nivel>2: bot.send_message(uid,f"❌ {txt} ya 2/2 CONCENTRADO", reply_markup=markup)
            else:
                monto=get_monto(nivel)
                if data["b"]<monto: bot.send_message(uid,f"❌ Saldo ${data['b']:.2f} necesita ${monto}", reply_markup=markup)
                else:
                    pr=P(txt); data["pos"].append({"sym":txt,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
                    bot.send_message(uid,f"✅ N{nivel} {txt} ${pr:.2f} x ${monto}\nhttps://telegram-bot-cijp.onrender.com/chart/{txt}", reply_markup=markup)
    elif "AUTO ON" in txt: data["auto"]=True; save(); bot.send_message(uid,"AUTO V37 CONCENTRADO ON 🔥 RSI<45", reply_markup=markup)
    elif "AUTO OFF" in txt: data["auto"]=False; save(); bot.send_message(uid,"AUTO OFF", reply_markup=markup)

def auto_loop():
    while True:
        try:
            if data.get("auto"):
                for p in list(data["pos"]):
                    pr=P(p["sym"])
                    if pr==0: continue
                    pct=(pr-p["precio_entry"])/p["precio_entry"]*100
                    max_p=p.get("max_price",pr)
                    if pct <= -15:
                        gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        data["b"]+=p["monto"]+gan; data["gan_total"]=data.get("gan_total",0)+gan; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"🛑 STOP {p['sym']} N{p.get('nivel',1)} {pct:.1f}%")
                            except: pass
                    elif pct>1.5 and pr < max_p*0.99:
                        gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        data["b"]+=p["monto"]+gan; data["gan_total"]=data.get("gan_total",0)+gan; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"💰 V37 RAPIDA {p['sym']} N{p.get('nivel',1)} +{pct:.1f}% Gan ${gan:.2f}")
                            except: pass
                for sym in ALL_COINS:
                    closes=C(sym); rsi=RSI(closes); pr=P(sym)
                    if pr==0: continue
                    count=sum(1 for x in data["pos"] if x["sym"]==sym)
                    if count>=2 or len(data["pos"])>=MAX_POS: continue
                    nivel=count+1; monto=get_monto(nivel)
                    if data["b"]<monto: continue
                    should=False
                    if count==0 and rsi<45: should=True
                    elif count==1:
                        entries=[x["precio_entry"] for x in data["pos"] if x["sym"]==sym]
                        if len(entries)>0:
                            avg=sum(entries)/len(entries)
                            if pr < avg*0.97: should=True
                    if should:
                        data["pos"].append({"sym":sym,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"🔥 V37 CONC N{nivel} {sym} ${pr:.2f} x ${monto} RSI {rsi:.0f}")
                            except: pass
            time.sleep(20)
        except: time.sleep(10)

def resumen_diario():
    global last_report_date
    while True:
        try:
            now_utc = datetime.utcnow()
            now_mex = now_utc - timedelta(hours=6)
            if now_mex.hour == 22 and now_mex.minute == 0:
                today_str = now_mex.strftime("%Y-%m-%d")
                if last_report_date!= today_str:
                    tot, flot = totals()
                    gan_hist = data.get("gan_total",0)
                    texto = f"📊 RESUMEN V37 CONCENTRADO - 10PM\n📅 {now_mex.strftime('%d/%m/%Y')}\n💰 TOTAL: ${tot:.2f}\n💵 Saldo: ${data['b']:.2f}\n📈 Flotante: {flot:+.2f}$\n🏆 Gan Hist: ${gan_hist:+.2f}\n📌 Pos: {len(data['pos'])}/{MAX_POS}\n\n"
                    if len(data["pos"]) > 0:
                        texto += "🔹 ENTRADAS:\n"
                        for p in data["pos"]:
                            pr = P(p["sym"])
                            pct = ((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"]>0 else 0
                            texto += f"• {p['sym']} N{p.get('nivel',1)} ${p['monto']} {pct:+.1f}% ${p.get('gan',0):+.2f}\n"
                    else:
                        texto += "Sin posiciones\n"
                    texto += f"\nhttps://telegram-bot-cijp.onrender.com"
                    for uid in data["alert_users"]:
                        try: bot.send_message(uid, texto)
                        except: pass
                    last_report_date = today_str
            time.sleep(60)
        except: time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
threading.Thread(target=resumen_diario,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
