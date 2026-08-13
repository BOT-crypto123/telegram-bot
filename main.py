import os, requests, threading, time
from datetime import datetime, timedelta
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "123456:TEST"
NPOINT_ID = "455c95667066c8b158d0"
ALL_COINS = ["NVDA","TSLA","BTC","XAUUSD","ETH","SOL"]
MAX_POS = 8
COMISION = 0.003

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)
LAST_PRICE = {"XAUUSD":3350,"BTC":63566,"ETH":2650,"SOL":145,"NVDA":183.5,"TSLA":248.2}
last_report_date = ""

def load():
    try:
        r=requests.get(f"https://api.npoint.io/{NPOINT_ID}",timeout=10)
        if r.status_code==200:
            d=r.json()
            if d.get("b",0) < 500 and len(d.get("pos",[]))==0: d["b"]=5000
            d.setdefault("pos",[]); d.setdefault("alert_users",[]); d.setdefault("auto",True); d.setdefault("gan_total",0); d.setdefault("com_total",0)
            return d
    except: pass
    return {"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0,"com_total":0}
data=load()

def P(sym):
    global LAST_PRICE
    try:
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XAUUSD":"pax-gold"}
        if sym in cg:
            r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg[sym]}&vs_currencies=usd",timeout=8).json()
            price=float(r[cg[sym]]["usd"])
            if price>0:
                last=LAST_PRICE.get(sym,price)
                if abs(price-last)/last<0.20: LAST_PRICE[sym]=price; return price
                else: return last
    except: pass
    try:
        mp={"XAUUSD":"PAXGUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT"}
        if sym in mp:
            r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp[sym]}",timeout=5).json()
            price=float(r["price"])
            if price>0:
                last=LAST_PRICE.get(sym,price)
                if abs(price-last)/last<0.20: LAST_PRICE[sym]=price; return price
                else: return last
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
            if abs(pr-p["precio_entry"])/p["precio_entry"]>0.25: continue
            bruto=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
            p["gan"]=bruto - p["monto"]*COMISION - pr/p["precio_entry"]*p["monto"]*COMISION
            if "max_price" not in p: p["max_price"]=pr
            if pr>p["max_price"]: p["max_price"]=pr
            flot+=p["gan"]
    return data["b"]+flot,flot

def get_monto(nivel): return 500 if nivel==1 else 750
def save():
    try: requests.post(f"https://api.npoint.io/{NPOINT_ID}",json=data,timeout=10)
    except: pass

@app.route("/")
def dash():
    return """<meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#080808;color:#fff;font-family:Arial;padding:10px;margin:0}.card{background:#111;border-radius:20px;padding:16px;margin-bottom:12px;border:1px solid #222}.gold{color:#ffcc00;font-weight:800;font-size:11px}.big{font-size:38px;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.coin{background:#151515;border:2px solid #333;border-radius:16px;padding:12px;text-align:center;cursor:pointer}.coin.hot{border-color:#ffcc00;background:#1a1a00}.pos{padding:14px;background:#151515;border-radius:12px;margin-bottom:8px;border-left:4px solid #00ff88;cursor:pointer;display:flex;justify-content:space-between}.logo{width:80px;height:80px;border-radius:50%;background:radial-gradient(circle at 30% 30%, #ffe87a, #ffcc00 40%, #b89600);border:3px solid #ffcc00;display:flex;align-items:center;justify-content:center;margin:0 auto;font-size:28px;font-weight:900;color:#000}</style><div class=card style=text-align:center;border:2px solid #ffcc00><div class=logo>$$</div><div style=font-size:11px;margin-top:10px;color:#ffcc00;font-weight:900>MAQUINA DE HACER DINERO V38.4 FINAL</div><div style=font-size:9px;color:#00ff88>● V34 CONCENTRADO + LINEAS VIVAS + NETO</div><div class=gold style=margin-top:12px>V34 $5029 + BOLA 15% + COM 0.6%</div><div class=big id=total>$----</div><div style=display:flex;justify-content:space-around;margin-top:10px;font-size:13px><div>Saldo<br><b id=saldo>$----</b></div><div>Flot NETO<br><b id=flot>----</b></div><div>Pos<br><b id=poscount>0/8</b></div></div><div style=margin-top:10px;font-size:10px'><div>Hist NETO <b id=hist style=color:#00ff88>$0</b> | Com <b id=com style=color:#ff4444>$0</b></div><div style=color:#aaa'>Bola N1 $500 N2 $750 | STOP -15% | +1.5% = Neto +0.9%</div><div style=color:#00ff88;font-weight:800'>LINEAS VERDE ENTRADA AZUL TP EN GRAFICA</div></div></div><div class=card><div class=gold>🔥 POSICIONES NETO - TOCA PARA VER LINEAS VIVAS</div><div id=poslist style=margin-top:10px>Cargando...</div></div><div class=card><div class=gold>📊 MERCADO - TOCA PARA GRAFICA CON LINEAS</div><div class=grid style=margin-top:10px><div class=coin id=c-BTC onclick="location='/chart/BTC'"><b>BTC</b><br><span id=p-BTC>$--</span><br><small>RSI <span id=r-BTC>--</span></small></div><div class=coin id=c-ETH onclick="location='/chart/ETH'"><b>ETH</b><br><span id=p-ETH>$--</span><br><small>RSI <span id=r-ETH>--</span></small></div><div class=coin id=c-SOL onclick="location='/chart/SOL'"><b>SOL</b><br><span id=p-SOL>$--</span><br><small>RSI <span id=r-SOL>--</span></small></div><div class=coin id=c-XAUUSD onclick="location='/chart/XAUUSD'"><b>XAUUSD</b><br><span id=p-XAUUSD>$--</span><br><small>RSI <span id=r-XAUUSD>--</span></small></div><div class=coin id=c-NVDA onclick="location='/chart/NVDA'"><b>NVDA</b><br><span id=p-NVDA>$--</span></div><div class=coin id=c-TSLA onclick="location='/chart/TSLA'"><b>TSLA</b><br><span id=p-TSLA>$--</span></div></div></div><script>async function loadDash(){try{let r=await fetch('https://api.npoint.io/455c95667066c8b158d0');let d=await r.json();let b=d.b||5000;let pos=d.pos||[];document.getElementById('saldo').innerText='$'+b.toFixed(2);document.getElementById('hist').innerText='$'+(d.gan_total||0).toFixed(2);document.getElementById('com').innerText='$'+(d.com_total||0).toFixed(2);document.getElementById('poscount').innerText=pos.length+'/8';let flot=0;let html='';for(let p of pos){let sym=p.sym;let entry=p.precio_entry;let monto=p.monto;let live=entry;try{let mp={'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT'};if(mp[sym]){let pr=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${mp[sym]}`).then(x=>x.json());live=parseFloat(pr.price);}}catch(e){live=entry;}if(Math.abs(live-entry)/entry>0.25)live=entry;let bruto=monto*(live-entry)/entry;let neto=bruto-monto*0.003-live/entry*monto*0.003;flot+=neto;let color=neto>=0?'#00ff88':'#ff4444';let pct=(live-entry)/entry*100;html+=`<div class=pos style='border-left-color:${color}' onclick="location='/chart/${sym}'"><div><b>${sym} N${p.nivel||1} $${monto}</b><br><small>$${entry.toFixed(2)}→$${live.toFixed(2)} ${pct.toFixed(1)}%</small><br><small>Bruto $${bruto.toFixed(2)} -Com $${(monto*0.003+live/entry*monto*0.003).toFixed(2)} = <b style='color:${color}'>NETO $${neto.toFixed(2)}</b></small><br><small style='color:#00ff88'>🟩 ENTRADA 🟦 TP + 📈 VIVA ►</small></div><div style='color:${color};font-weight:900'>${neto.toFixed(2)}$</div></div>`;}if(pos.length==0)html="<div style='padding:25px;text-align:center;opacity:.6;border:2px dashed #333;border-radius:14px'>🔥 V38.4 LISTA<br>Bola N1 $500 N2 $750<br>RSI<45 ABRE 4-6 HOY<br>GRAFICAS CON LINEAS VERDE/AZUL<br>NETO REAL</div>";document.getElementById('poslist').innerHTML=html;document.getElementById('total').innerText='$'+(b+flot).toFixed(2);document.getElementById('flot').innerText=(flot>=0?'+':'')+flot.toFixed(2)+'$';document.getElementById('flot').style.color=flot>=0?'#00ff88':'#ff4444';}catch(e){}}async function loadPrices(){const map={'BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT','XAUUSD':'PAXGUSDT'};for(let s in map){try{let pr=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${map[s]}`).then(x=>x.json());document.getElementById('p-'+s).innerText='$'+parseFloat(pr.price).toFixed(1);let kl=await fetch(`https://api.binance.com/api/v3/klines?symbol=${map[s]}&interval=1h&limit=20`).then(x=>x.json());let closes=kl.map(x=>+x[4]);let g=0,l=0;for(let i=1;i<15;i++){let d=closes[closes.length-i]-closes[closes.length-i-1];if(d>0)g+=d;else l+=-d;}let rsi=100-(100/(1+g/(l||1)));let re=document.getElementById('r-'+s);if(re){re.innerText=rsi.toFixed(0);if(rsi<45)document.getElementById('c-'+s).classList.add('hot');}}catch(e){}}}loadDash();loadPrices();setInterval(loadDash,10000);setInterval(loadPrices,15000);</script>"""

@app.route("/chart/<sym>")
def chart(sym):
    sym=sym.upper()
    return f"""
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@3.8.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
body{{background:#080808;color:#fff;margin:0;font-family:Arial}}
.top{{padding:12px;background:#111;display:flex;justify-content:space-between;border-bottom:3px solid #ffcc00;position:sticky;top:0;z-index:10}}
.live{{background:#00ff88;color:#000;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:900;animation:blink 1s infinite}}
@keyframes blink{{0%{{opacity:1}}50%{{opacity:.3}}}}
#info{{padding:10px;background:#151515;display:flex;gap:8px;overflow:auto}}
.box{{background:#222;padding:8px 12px;border-radius:10px;white-space:nowrap;font-size:12px}}
button{{background:#ffcc00;padding:10px 16px;border:none;border-radius:10px;font-weight:900}}
#chart{{width:100%;height:78vh}}
</style>
</head><body>
<div class=top>
<div><b>{sym}</b> <span class=live>● VIVO 1M</span><br><small id=entryinfo style=color:#ffcc00>Cargando...</small></div>
<a href="/"><button>◀ DASH</button></a>
</div>
<div id=info>
<div class=box>Precio <b id=pv style=color:#ffcc00>--</b></div>
<div class=box>Bruto <b id=bruto>--</b></div>
<div class=box>NETO <b id=pnl>--</b></div>
<div class=box><b id=gan>--</b></div>
<div class=box style=border:1px solid #00ff88>🟩 Entrada <b id=line1 style=color:#00ff88>--</b></div>
<div class=box style=border:1px solid #00ccff>🟦 TP <b id=line2 style=color:#00ccff>--</b></div>
</div>
<div id=chart></div>
<div style=padding:8px;text-align:center;font-size:10px;color:#888'>🟩 VERDE = Tu entrada | 🟦 AZUL = TP +1.5% Venta rápida | Viva cada 3 seg - NETO ya menos 0.6%</div>
<script>
const SYM="{sym}";
const BINMAP={{'XAUUSD':'PAXGUSDT','BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT','NVDA':'BTCUSDT','TSLA':'BTCUSDT'}};
let binSym=BINMAP[SYM]||'BTCUSDT';
let entry=0,monto=500;
async function init(){{
  try{{
    let d=await fetch('https://api.npoint.io/455c95667066c8b158d0').then(r=>r.json());
    let p=d.pos.find(x=>x.sym==SYM);
    if(p){{entry=p.precio_entry; monto=p.monto;
      document.getElementById('entryinfo').innerText='Entrada $'+entry.toFixed(2)+' x $'+monto+' N'+(p.nivel||1);
      document.getElementById('line1').innerText='$'+entry.toFixed(2);
      document.getElementById('line2').innerText='$'+(entry*1.015).toFixed(2);
    }} else {{
      document.getElementById('entryinfo').innerText='SIN POSICION - Mercado vivo';
    }}
    let chart=LightweightCharts.createChart(document.getElementById('chart'),{{
      layout:{{backgroundColor:'#080808',textColor:'#ddd'}},
      grid:{{vertLines:{{color:'#1a1a1a'}},horzLines:{{color:'#1a1a1a'}}}},
      width: window.innerWidth,
      height: window.innerHeight*0.78
    }});
    let candleSeries=chart.addCandlestickSeries({{upColor:'#00ff88',downColor:'#ff4444',borderVisible:false,wickUpColor:'#00ff88',wickDownColor:'#ff4444'}});
    let kl=await fetch(`https://api.binance.com/api/v3/klines?symbol=${{binSym}}&interval=1m&limit=200`).then(r=>r.json());
    let data=kl.map(k=>({{time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4]}}));
    candleSeries.setData(data);
    if(entry>0){{
      candleSeries.createPriceLine({{color:'#00ff88',price:entry,lineWidth:2,lineStyle:2,axisLabelVisible:true,title:'ENTRADA'}});
      candleSeries.createPriceLine({{color:'#00ccff',price:entry*1.015,lineWidth:1,lineStyle:1,axisLabelVisible:true,title:'TP +1.5%'}});
    }}
    chart.timeScale().fitContent();
    let last=data[data.length-1];
    setInterval(async()=>{{
      try{{
        let pr=await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${{binSym}}`).then(r=>r.json());
        let price=+pr.price;
        let now=Math.floor(Date.now()/1000);
        let newC={{time:now,open:last.close,high:Math.max(last.high,price),low:Math.min(last.low,price),close:price}};
        candleSeries.update(newC);
        if(now-last.time>=60) last=newC;
        document.getElementById('pv').innerText='$'+price.toFixed(2);
        if(entry>0){{
          let pct=((price-entry)/entry*100).toFixed(2);
          let bruto=(monto*(price-entry)/entry);
          let neto=bruto - monto*0.003 - price/entry*monto*0.003;
          document.getElementById('gan').innerText=pct+'%';
          document.getElementById('bruto').innerText='$'+bruto.toFixed(2);
          document.getElementById('pnl').innerText='$'+neto.toFixed(2);
          document.getElementById('pnl').style.color=neto>=0?'#00ff88':'#ff4444';
        }}
      }}catch(e){{}}
    }},3000);
  }}catch(e){{ document.getElementById('entryinfo').innerText='Error, recarga'; }}
}}
init();
</script></body></html>
"""

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
        data["b"]=5000; data["pos"]=[]; data["gan_total"]=0; data["com_total"]=0; save()
        bot.send_message(uid,"✅ V38.4 FINAL $5000 - LINEAS VIVAS + BOLA + NETO", reply_markup=markup); return
    elif "RESET5K" in txt: bot.send_message(uid,"⚠️ Escribe RESET5K CONFIRMAR", reply_markup=markup); return
    if any(k in txt for k in ["DASH","BALANCE","SALDO","START","HOLA"]):
        tot,flot=totals()
        bot.send_message(uid,f"V38.4 FINAL 🔥\n💰 NETO ${tot:.2f}\nSaldo ${data['b']:.2f}\nFlot NETO {flot:+.2f}$\nPos {len(data['pos'])}/8\nAUTO {'ON' if data.get('auto') else 'OFF'}\nHist NETO ${data.get('gan_total',0):+.2f}\nCom ${data.get('com_total',0):.2f}\nBola $500/$750 + Lineas SI\nhttps://telegram-bot-cijp.onrender.com", reply_markup=markup)
    elif txt in ALL_COINS:
        if len(data["pos"])>=MAX_POS: bot.send_message(uid,"❌ Lleno 8/8", reply_markup=markup)
        else:
            nivel=sum(1 for x in data["pos"] if x["sym"]==txt)+1
            if nivel>2: bot.send_message(uid,f"❌ {txt} ya 2/2 bola", reply_markup=markup)
            else:
                monto=get_monto(nivel)
                if data["b"]<monto: bot.send_message(uid,f"❌ Saldo ${data['b']:.2f} necesita ${monto}", reply_markup=markup)
                else:
                    pr=P(txt)
                    if pr==0: bot.send_message(uid,"❌ Sin precio 5s", reply_markup=markup)
                    else:
                        data["pos"].append({"sym":txt,"monto":monto,"precio_entry":pr,"gan":0,"max_price":pr,"nivel":nivel}); data["b"]-=monto; save()
                        bot.send_message(uid,f"✅ BOLA N{nivel} {txt} ${pr:.2f} x ${monto}\n🟩 Entrada ${pr:.2f}\n🟦 TP ${pr*1.015:.2f}\nhttps://telegram-bot-cijp.onrender.com/chart/{txt}", reply_markup=markup)
    elif "AUTO ON" in txt: data["auto"]=True; save(); bot.send_message(uid,"AUTO V38.4 ON 🔥 LINEAS + BOLA", reply_markup=markup)
    elif "AUTO OFF" in txt: data["auto"]=False; save(); bot.send_message(uid,"AUTO OFF", reply_markup=markup)

def auto_loop():
    while True:
        try:
            if data.get("auto"):
                for p in list(data["pos"]):
                    pr=P(p["sym"])
                    if pr==0: continue
                    pct=(pr-p["precio_entry"])/p["precio_entry"]*100
                    if abs(pct)>25: continue
                    max_p=p.get("max_price",pr)
                    if pct <= -15:
                        bruto=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        com_total=p["monto"]*COMISION + (pr/p["precio_entry"]*p["monto"]*COMISION)
                        gan=bruto-com_total
                        data["b"]+=p["monto"]+gan; data["gan_total"]=data.get("gan_total",0)+gan; data["com_total"]=data.get("com_total",0)+com_total; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"🛑 STOP NETO {p['sym']} {pct:.1f}% Neto ${gan:.2f}")
                            except: pass
                    elif pct>1.5 and pr < max_p*0.99:
                        bruto=((pr-p["precio_entry"])/p["precio_entry"])*p["monto"]
                        com_total=p["monto"]*COMISION + (pr/p["precio_entry"]*p["monto"]*COMISION)
                        gan=bruto-com_total
                        data["b"]+=p["monto"]+gan; data["gan_total"]=data.get("gan_total",0)+gan; data["com_total"]=data.get("com_total",0)+com_total; data["pos"].remove(p); save()
                        for uid in data["alert_users"]:
                            try: bot.send_message(uid,f"💰 VENTA NETA {p['sym']} {pct:.1f}% Neto ${gan:.2f}")
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
                            try: bot.send_message(uid,f"🔥 BOLA N{nivel} {sym} ${pr:.2f} x ${monto} RSI {rsi:.0f}")
                            except: pass
            time.sleep(20)
        except: time.sleep(10)

def resumen_diario():
    global last_report_date
    while True:
        try:
            now_utc=datetime.utcnow(); now_mex=now_utc - timedelta(hours=6)
            if now_mex.hour==22 and now_mex.minute==0:
                today_str=now_mex.strftime("%Y-%m-%d")
                if last_report_date!=today_str:
                    tot,flot=totals()
                    texto=f"📊 V38.4 FINAL - 10PM\n📅 {now_mex.strftime('%d/%m/%Y')}\n💰 TOTAL NETO: ${tot:.2f}\nSaldo: ${data['b']:.2f}\nFlot NETO: {flot:+.2f}$\nHist NETO: ${data.get('gan_total',0):+.2f}\nCom: ${data.get('com_total',0):.2f}\nPos: {len(data['pos'])}/8 BOLA ON\n"
                    for p in data["pos"]:
                        pr=P(p["sym"]);
                        if pr==0: pr=p["precio_entry"]
                        pct=((pr-p["precio_entry"])/p["precio_entry"]*100) if p["precio_entry"]>0 else 0
                        if abs(pct)<25: texto+=f"• {p['sym']} N{p.get('nivel',1)} Neto ${p.get('gan',0):+.2f}\n"
                    texto+=f"\nhttps://telegram-bot-cijp.onrender.com"
                    for uid in data["alert_users"]:
                        try: bot.send_message(uid,texto)
                        except: pass
                    last_report_date=today_str
            time.sleep(60)
        except: time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
threading.Thread(target=resumen_diario,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
