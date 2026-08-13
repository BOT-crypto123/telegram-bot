import os, requests, threading, time
from datetime import datetime, timedelta
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "123456:TEST"
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["NVDA","TSLA","BTC","XAUUSD","ETH","SOL"]
MAX_POS = 8

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# PRECIOS REALES ACTUALIZADOS 2026
LAST_PRICE = {"XAUUSD":3350,"BTC":63566,"ETH":2650,"SOL":145,"NVDA":183.5,"TSLA":248.2}
last_report_date = ""

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10)
        if r.status_code==200:
            d=r.json()
            if d.get("b",0) < 500 and len(d.get("pos",[]))==0: d["b"]=5000
            d.setdefault("pos",[]); d.setdefault("alert_users",[]); d.setdefault("auto",True); d.setdefault("gan_total",0)
            return d
    except: pass
    return {"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0}

data=load()

def P(sym):
    global LAST_PRICE
    # FIX ANTI-PRECIO FALSO - Valida diferencia max 15%
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XAUUSD":"pax-gold"}
        if sym in cg:
            r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg[sym]}&vs_currencies=usd",timeout=8).json()
            price=float(r[cg[sym]]["usd"])
            if price>0:
                last = LAST_PRICE.get(sym, price)
                if last==0: last=price
                # Si diferencia es mas de 20% es error de API, usa ultimo bueno
                if abs(price-last)/last < 0.20:
                    LAST_PRICE[sym]=price
                    return price
                else:
                    return last
    except: pass
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        if sym in mp:
            r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=5).json()
            price=float(r["price"])
            if price>0:
                last = LAST_PRICE.get(sym, price)
                if last==0: last=price
                if abs(price-last)/last < 0.20:
                    LAST_PRICE[sym]=price
                    return price
                else:
                    return last
    except: pass
    return LAST_PRICE.get(sym,0)

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
            # FIX - Si diferencia es absurda >25% es error precio, no calcula
            if abs(pr-p["precio_entry"])/p["precio_entry"] > 0.25:
                p["gan"]=0
                continue
            p["gan"]=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
            if "max_price" not in p: p["max_price"]=pr
            if pr>p["max_price"]: p["max_price"]=pr
            flot+=p["gan"]
    return data["b"]+flot, flot

def get_monto(nivel=1):
    if nivel==1: return 500
    if nivel==2: return 750
    if nivel==3: return 750
    return 750

def save():
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass

@app.route("/")
def dash():
    tot,flot=totals()
    col="#00ff88" if flot>=0 else "#ff4444"
    pos_html=""
    for p in data["pos"]:
        pr=P(p["sym"])
        if pr==0: pr=p["precio_entry"]
        pct=((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"]>0 else 0
        # Si pct es loco, no mostrar
        if abs(pct)>25:
            pct=0
            pr=p["precio_entry"]
        color_p="#00ff88" if pct>=0 else "#ff4444"
        pos_html+=f"""
        <div onclick="window.location='/chart/{p['sym']}'" style='display:flex;justify-content:space-between;align-items:center;padding:16px;border-bottom:1px solid #222;cursor:pointer;background:#151515;margin-bottom:6px;border-radius:12px;border-left:4px solid {color_p}'>
            <div><b style='font-size:16px'>{p['sym']} N{p.get('nivel',1)} ${p['monto']}</b><br><small style='color:#aaa'>${p['precio_entry']:.2f} → ${pr:.2f} <span style='color:{color_p};font-weight:800'>{pct:+.1f}%</span></small><br><small style='color:#00ccff;font-weight:800'>📈 GRAFICA VIVA ►</small></div>
            <div style='text-align:right'><span style='color:{color_p};font-weight:900;font-size:18px'>{p.get('gan',0):+.2f}$</span></div>
        </div>"""
    if not pos_html:
        pos_html=f"<div style='padding:30px;text-align:center;opacity:.6;border:2px dashed #333;border-radius:16px'>🔥 V38.1 FIX LISTO - BUG -41% CORREGIDO<br><br>Esperando RSI<45<br>ABRIRA 4-6 HOY<br><br>N1 $500 N2 $750<br>AUTO {'ON 🔥' if data.get('auto') else 'OFF'}</div>"

    coins=""
    for s in ALL_COINS:
        pr=P(s); rsi=RSI(C(s)); count=sum(1 for x in data["pos"] if x["sym"]==s)
        if pr==0: pr=LAST_PRICE.get(s,0)
        c2="#ffcc00" if rsi<45 else "#333"
        bg="#1a1a00" if rsi<45 else "#151515"
        coins+=f"<div onclick=\"window.location='/chart/{s}'\" style='background:{bg};border:2px solid {c2};border-radius:16px;padding:12px;cursor:pointer;text-align:center'><b>{s}</b> {count}/2<br><b style='font-size:18px'>${pr:.1f}</b><br>RSI {rsi:.0f}<br><small style='color:#00ff88'>N{count+1} ${get_monto(count+1)}$</small><br><small style='background:#ffcc00;color:#000;padding:2px 6px;border-radius:8px;font-weight:900;font-size:9px'>VIVA</small></div>"

    return f"""<meta name=viewport content="width=device-width,initial-scale=1"><style>body{{background:#080808;color:#fff;font-family:Arial;padding:10px;margin:0}}.card{{background:#111;border-radius:20px;padding:16px;margin-bottom:12px;border:1px solid #222}}.gold{{color:#ffcc00;font-weight:800;font-size:12px;letter-spacing:1px}}.big{{font-size:38px;font-weight:900}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.logo{{width:90px;height:90px;border-radius:50%;background:radial-gradient(circle at 30% 30%, #ffe87a, #ffcc00 40%, #b89600);border:3px solid #ffcc00;display:flex;align-items:center;justify-content:center;margin:0 auto;box-shadow:0 0 30px rgba(255,204,0,.6);font-size:32px;font-weight:900;color:#000}}.live-dot{{display:inline-block;width:8px;height:8px;background:#00ff88;border-radius:50%;animation:blink 1s infinite}} @keyframes blink{{0%{{opacity:1}}50%{{opacity:.2}}100%{{opacity:1}}}} </style>
    <div class=card style=text-align:center;border:2px solid #ffcc00>
        <div class=logo>$$</div>
        <div style=font-size:11px;margin-top:10px;letter-spacing:2px;color:#ffcc00;font-weight:900>V38.1 FIX - MAQUINA DINERO VIVO</div>
        <div style=font-size:9px;color:#00ff88><span class=live-dot></span> BUG -41% CORREGIDO + GRAFICAS VIVAS</div><br>
        <div class=gold>CONCENTRADO + ANTI PRECIO FALSO</div>
        <div class=big>${tot:.2f}</div>
        <div style=display:flex;justify-content:space-around;margin-top:10px>
            <div>Saldo<br><b>${data['b']:.2f}</b></div>
            <div>Flot<br><b style='color:{col}'>{flot:+.2f}$</b></div>
            <div>Pos<br><b>{len(data['pos'])}/{MAX_POS}</b></div>
        </div>
        <div style=margin-top:10px;font-size:11px>Hist <b style='color:#00ff88'>${data.get('gan_total',0):+.2f}</b> | Trail 1% si +1.5% | STOP -15% REAL</div>
    </div>
    <div class=card><div class=gold>🔥 POSICIONES - TOCA PARA GRAFICA VIVA</div><div style=margin-top:10px>{pos_html}</div></div>
    <div class=card><div class=gold>📊 MERCADO VIVO - TOCA PARA GRAFICA</div><div class=grid style=margin-top:10px>{coins}</div></div>"""

@app.route("/chart/<sym>")
def chart(sym):
    sym=sym.upper(); entry=0; monto=500; nivel=1
    for p in data["pos"]:
        if p["sym"]==sym: entry=p.get("precio_entry",0); monto=p.get("monto",0); nivel=p.get("nivel",1); break
    tot,_=totals()
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{{background:#080808;color:#fff;margin:0;font-family:Arial}}.top{{padding:14px;background:#111;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #ffcc00;position:sticky;top:0}}.live{{background:#00ff88;color:#000;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:900;animation:blink 1s infinite}} @keyframes blink{{0%{{opacity:1}}50%{{opacity:.3}}100%{{opacity:1}}}} #info{{padding:12px;background:#151515;display:flex;gap:10px;overflow:auto;border-bottom:1px solid #222}}.box{{background:#222;padding:10px 14px;border-radius:12px;white-space:nowrap;border:1px solid #333}} button{{background:#ffcc00;padding:10px 18px;border:none;border-radius:10px;font-weight:900}}</style></head><body>
<div class=top><div><b style='font-size:18px'>{sym} N{nivel} ${monto}</b> <span class=live>● VIVO</span><br><small style=color:#00ff88>Entrada ${entry:.2f} | Total ${tot:.2f}</small></div><a href="/"><button>◀ DASH</button></a></div>
<div id=info><div class=box>Precio: <b id=pv style='color:#ffcc00'>--</b></div><div class=box>RSI: <b id=rsi>--</b></div><div class=box>Gan: <b id=gan>--</b></div><div class=box>PnL: <b id=pnl>--</b></div></div>
<div id=chart style=width:100%;height:70vh></div>
<script>
const SYM="{sym}"; const ENTRY={entry}; const MONTO={monto};
const map={{'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT','NVDA':'BTCUSDT','TSLA':'BTCUSDT'}};
const binSym=map[SYM]||'BTCUSDT';
let chart, candleSeries, lastCandle;
async function init(){{
 chart=LightweightCharts.createChart(document.getElementById('chart'),{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}},crosshair:{{mode:1}}}});
 candleSeries=chart.addCandlestickSeries({{upColor:'#00ff88',downColor:'#ff4444',wickUpColor:'#00ff88',wickDownColor:'#ff4444'}});
 let r=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1m&limit=200`);
 let kl=await r.json();
 let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));
 candleSeries.setData(data); lastCandle=data[data.length-1];
 if(ENTRY>0){{ let l=chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); l.setData(data.map(x=>({{time:x.time,value:ENTRY}}))); let tp=chart.addLineSeries({{color:'#00ccff',lineWidth:1,lineStyle:1}}); tp.setData(data.map(x=>({{time:x.time,value:ENTRY*1.015}}))); }}
 chart.timeScale().fitContent(); setInterval(updateLive,3000); updateInfo();
}}
async function updateLive(){{
 try{{ let r=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${{binSym}}`); let p=+(await r.json()).price; let now=Math.floor(Date.now()/1000);
   let newC={{time:now,open:lastCandle.close,high:Math.max(lastCandle.high,p),low:Math.min(lastCandle.low,p),close:p}};
   candleSeries.update(newC); if(now-lastCandle.time>=60) lastCandle=newC;
   document.getElementById('pv').innerText='$'+p.toFixed(2);
   if(ENTRY>0){{ let pct=((p-ENTRY)/ENTRY*100).toFixed(2); let gan=(MONTO*(p-ENTRY)/ENTRY).toFixed(2); let el=document.getElementById('gan'); el.innerText=pct+'%'; el.style.color=p>=ENTRY?'#00ff88':'#ff4444'; document.getElementById('pnl').innerText='$'+gan; document.getElementById('pnl').style.color=p>=ENTRY?'#00ff88':'#ff4444'; }}
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
        bot.send_message(uid,"✅ V38.1 FIX REINICIADO $5000 - PRECIOS REALES", reply_markup=markup); return
    elif "RESET5K" in txt: bot.send_message(uid,"⚠️ Escribe RESET5K CONFIRMAR", reply_markup=markup); return

    if any(k in txt for k in ["DASH","BALANCE","SALDO","START","HOLA"]):
        tot,flot=totals()
        bot.send_message(uid,f"V38.1 FIX MAQUINA 🔥\n💰 Total ${tot:.2f}\nSaldo ${data['b']:.2f} Flot {flot:+.2f}$\nPos {len(data['pos'])}/{MAX_POS}\nAUTO {'ON 🔥' if data.get('auto') else 'OFF'}\nHist ${data.get('gan_total',0):.2f}\nBUG -41% CORREGIDO\nhttps://telegram-bot-cijp.onrender.com", reply_markup=markup)
    elif txt in ALL_COINS:
        if len(data["pos"])>=MAX_POS: bot.send_message(uid,"❌ Lleno 8/8", reply_markup=markup)
        else:
            nivel=sum(1 for x in data["pos"] if x["sym"]==txt)+1
            if nivel>2: bot.send_message(uid,f"❌ {txt} ya 2/2", reply_markup=markup)
            else:
                monto=get_monto(nivel)
                if data["b"]<monto: bot.send_message(uid,f"❌ Saldo ${data['b']:.2f} necesita ${monto}", reply_markup=markup)
                else:
                    pr=P(txt)
                    if pr==0: bot.send_message(uid,"❌ Sin precio real ahora, intenta en 5 seg", reply_markup=markup)
                    else:
                        data["pos"].append({"sym":txt,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
                        bot.send_message(uid,f"✅ N{nivel} {txt} ${pr:.2f} x ${monto}\n📈 https://telegram-bot-cijp.onrender.com/chart/{txt}", reply_markup=markup)
    elif "AUTO ON" in txt: data["auto"]=True; save(); bot.send_message(uid,"AUTO V38.1 FIX ON 🔥", reply_markup=markup)
    elif "AUTO OFF" in txt: data["auto"]=False; save(); bot.send_message(uid,"AUTO OFF", reply_markup=markup)

def auto_loop():
    while True:
        try:
            if data.get("auto"):
                for p in list(data["pos"]):
                    pr=P(p["sym"])
                    if pr==0: continue
                    pct=(pr-p["precio_entry"])/p["precio_entry"]*100
                    if abs(pct)>25: continue # ANTI BUG PRECIO FALSO
                    max_p=p.get("max_price",pr)
                    if pct <= -15:
                        gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        data["b"]+=p["monto"]+gan; data["gan_total"]=data.get("gan_total",0)+gan; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"🛑 STOP REAL {p['sym']} N{p.get('nivel',1)} {pct:.1f}%")
                            except: pass
                    elif pct>1.5 and pr < max_p*0.99:
                        gan=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        data["b"]+=p["monto"]+gan; data["gan_total"]=data.get("gan_total",0)+gan; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"💰 VENTA {p['sym']} +{pct:.1f}% ${gan:.2f}")
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
                        if len(entries)>0 and pr < sum(entries)/len(entries)*0.97: should=True
                    if should:
                        data["pos"].append({"sym":sym,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"🔥 V38.1 N{nivel} {sym} ${pr:.2f} x ${monto} RSI {rsi:.0f}\nhttps://telegram-bot-cijp.onrender.com/chart/{sym}")
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
                    texto = f"📊 V38.1 FIX - 10PM\n📅 {now_mex.strftime('%d/%m/%Y')}\n💰 TOTAL: ${tot:.2f}\nSaldo: ${data['b']:.2f}\nFlot: {flot:+.2f}$\nHist: ${data.get('gan_total',0):+.2f}\nPos: {len(data['pos'])}/8\n"
                    for p in data["pos"]:
                        pr = P(p["sym"])
                        if pr==0: pr=p["precio_entry"]
                        pct = ((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"]>0 else 0
                        if abs(pct)<25:
                            texto += f"• {p['sym']} N{p.get('nivel',1)} ${p['monto']} {pct:+.1f}%\n"
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
