import os, json, time, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "123456:TEST"
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

COINS_CRIPTO = ["ADA","AVAX","BTC","DOGE","ETH","LINK","SOL","XRP"]
COINS_STOCKS = ["NVDA","TSLA"]
COINS_GOLD = ["XAUUSD"]
ALL_COINS = COINS_CRIPTO + COINS_STOCKS + COINS_GOLD
MAX_POS=10
MONTO_TRADE=500
SALDO_INICIAL=5000
DASH_URL="https://telegram-bot-cijp.onrender.com"

STOP_LOSS_PCT = -7.0
TP1_PCT = 1.8
TP2_PCT = 3.5
TRAILING_PCT = 0.8
BTC_CRASH_PCT = -3.0

MONTO_E1 = 1750
MONTO_E2 = 1750
FIRST_CANDLE = {}
LIQUIDEZ_DATA = {}

try:
    with open("data.json","r") as f: data=json.load(f)
    if data.get("b",0)<200 and len(data.get("pos",[]))==0: data["b"]=SALDO_INICIAL
except: data={"b":SALDO_INICIAL,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[],"last_report_date":""}
data["coins"]=ALL_COINS

def save():
    try:
        with open("data.json","w") as f: json.dump(data,f)
    except: pass

def tg(chat,txt,markup=None):
    try: bot.send_message(chat,txt,reply_markup=markup, disable_web_page_preview=True)
    except: pass

def get_price_robust(sym):
    for url in [f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT", f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT"]:
        try:
            r=requests.get(url,timeout=4).json()
            if 'price' in r and float(r['price'])>0: return float(r['price'])
        except: pass
    try:
        mp={"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XRP":"XRP-USD","DOGE":"DOGE-USD","AVAX":"AVAX-USD","LINK":"LINK-USD","ADA":"ADA-USD"}
        ysym=mp.get(sym)
        if ysym:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}",timeout=5, headers={"User-Agent":"Mozilla/5.0"}).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
    except: pass
    return 0

def P(sym):
    try:
        if sym=="XAUUSD":
            for _ in range(2):
                try:
                    r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
                    price=float(r['chart']['result'][0]['meta']['regularMarketPrice'])
                    if price>0: return price
                except: time.sleep(0.5)
            try:
                r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=5d&interval=1d",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
                return float([x for x in r['chart']['result'][0]['indicators']['quote'][0]['close'] if x][-1])
            except: return 0
        if sym in COINS_STOCKS:
            for _ in range(2):
                try:
                    r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
                    price=float(r['chart']['result'][0]['meta']['regularMarketPrice'])
                    if price>0: return price
                except: time.sleep(0.5)
            try:
                r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
                return float([x for x in r['chart']['result'][0]['indicators']['quote'][0]['close'] if x][-1])
            except: return 0
        return get_price_robust(sym)
    except: return 0

def get_klines_robust(sym):
    for url in [f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=5m&limit=100", f"https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=5m&limit=100"]:
        try:
            kl=requests.get(url,timeout=6).json()
            if isinstance(kl,list) and len(kl)>=20: return kl
        except: pass
    return []

def AN(sym):
    try:
        price=P(sym)
        if price==0: return 50,0,0,0
        if sym in COINS_STOCKS+COINS_GOLD:
            try:
                ysym="GC=F" if sym=="XAUUSD" else sym
                r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=1d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
                closes=[c for c in r['chart']['result'][0]['indicators']['quote'][0]['close'] if c]
                ema=sum(closes[-20:])/20 if len(closes)>=20 else price
            except: ema=price
            return 29.0, price, ema, 0
        kl=get_klines_robust(sym)
        if not kl: return 50, price, price*0.998, 0
        closes=[float(k[4]) for k in kl]
        ema=sum(closes[-20:])/20
        gains=[max(0, closes[i]-closes[i-1]) for i in range(1,len(closes))]
        losses=[max(0, closes[i-1]-closes[i]) for i in range(1,len(closes))]
        rg=sum(gains[-14:])/14 or 0.01
        rl=sum(losses[-14:])/14 or 0.01
        rsi=100-(100/(1+rg/rl))
        try:
            btc=requests.get("https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT",timeout=5).json()
            btc_change=float(btc.get('priceChangePercent',0))
        except: btc_change=0
        return rsi, price, ema, btc_change
    except: return 50,0,0,0

def get_btc_1h():
    try:
        kl=requests.get("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=2",timeout=5).json()
        if len(kl)>=2:
            open1h=float(kl[-2][4])
            now=float(kl[-1][4])
            return (now-open1h)/open1h*100
    except: return 0
    return 0

def totals():
    flot=0
    for p in data['pos']:
        pr=P(p["sym"])
        if pr==0: pr=p["precio_entry"]
        gan=(pr-p["precio_entry"])/p["precio_entry"]*p["monto"]
        p["gan"]=gan
        flot+=gan
    tot=data['b']+sum([p['monto'] for p in data['pos']])+flot
    return tot, flot

def kb():
    m=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=4)
    m.add("BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA","NVDA","TSLA","XAUUSD","DASHBOARD","AUTO ON","AUTO OFF","BALANCE","DUAL")
    return m

def get_first_candle_ny(sym):
    try:
        if sym in COINS_CRIPTO: return None
        ysym="GC=F" if sym=="XAUUSD" else sym
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=2d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
        res=r['chart']['result'][0]
        stamps=res['timestamp']
        highs=res['indicators']['quote'][0]['high']
        lows=res['indicators']['quote'][0]['low']
        for i, ts in enumerate(stamps):
            dt=datetime.fromtimestamp(ts, ZoneInfo('America/New_York'))
            if dt.hour==9 and dt.minute==30:
                if dt.date()==datetime.now(ZoneInfo('America/New_York')).date():
                    if highs[i] and lows[i]:
                        return {"high": highs[i], "low": lows[i], "time": dt.strftime("%Y-%m-%d %H:%M NY")}
    except: pass
    return None

def detectar_liquidez(sym):
    try:
        if sym in COINS_CRIPTO: return None
        ysym="GC=F" if sym=="XAUUSD" else sym
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=5d&interval=15m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
        res=r['chart']['result'][0]
        closes=res['indicators']['quote'][0]['close']
        lows=res['indicators']['quote'][0]['low']
        highs=res['indicators']['quote'][0]['high']
        if len(closes)<50: return None
        for i in range(len(lows)-20, len(lows)-5):
            if lows[i] is None: continue
            similares = [j for j in range(i-10, i+5) if j>=0 and j<len(lows) and lows[j] and abs(lows[j]-lows[i])/lows[i]<0.003]
            if len(similares)>=3:
                for k in range(i+1, len(closes)-1):
                    if closes[k] and closes[k-1] and closes[k] < lows[i] and closes[k] < closes[k-1]*0.998:
                        ob_high = highs[k-1] if highs[k-1] else closes[k-1]
                        ob_low = lows[k-1] if lows[k-1] else closes[k-1]*0.99
                        return {"liquidez_en": lows[i], "quiebre_en": closes[k], "orderblock": (ob_low+ob_high)/2, "resistencia": lows[i], "target": lows[i]*0.92}
    except: pass
    return None

@app.route("/")
def home():
    tot, flot = totals()
    btc1h = get_btc_1h()
    html=f"""<html><head><meta name='viewport' content='width=device-width'><meta http-equiv='refresh' content='30'><style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
.card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:4px solid #00ff88}}
.card.neg{{border-left-color:#ff1744}}.card.pos{{border-left-color:#00ff88}}
.top{{border:2px solid #ffcc00;border-radius:15px;padding:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;background:#1a1500}}
.graf{{background:#ffcc00;color:#000;width:100%;padding:12px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}
.alert{{background:#ff1744;color:#fff;padding:8px;border-radius:8px;margin:8px 0;text-align:center;font-weight:bold}}
.live{{background:#00ff88;color:#000;padding:2px 8px;border-radius:10px;font-size:10px;animation:blink 1s infinite}}@keyframes blink{{0%{{opacity:1}}50%{{opacity:0.3}}}}
.dual{{background:linear-gradient(90deg,#a855f7,#ffcc00);color:#000;padding:12px;border-radius:10px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin:10px 0}}
    </style></head><body>
    <div class='top'><div><b>🔥 V32.2 DUAL FINAL 🔥 <span class='live'>● VIVO</span></b><br>{'🟢 CAZANDO' if data['auto_buy'] else '🔴 PAUSA'} | {len(data['pos'])}/{MAX_POS} | BTC 1h {btc1h:+.2f}%</div><div>Total ${tot:.2f}<br>Flot {flot:+.2f}</div></div>
    <a class='dual' href='/dual/NVDA'>🔥 DUAL $3500 → E1 AUTO $1750 + E2 CONFIRMA $1750</a>
    {f'<div class="alert">⚠️ BTC CRASH {btc1h:.2f}% - PAUSA</div>' if btc1h < BTC_CRASH_PCT else ''}
    <div style='display:flex;justify-content:space-between;margin:12px 0;flex-wrap:wrap'><span>Saldo ${data['b']:.2f}</span><span>Hoy ${data['gan_hoy']:.2f}</span><span>Total ${data['gan_total']:.2f}</span></div>"""
    for sym in ALL_COINS:
        try:
            rsi,price,ema20,btc_t=AN(sym)
            pos=next((x for x in data["pos"] if x["sym"]==sym), None)
            if pos:
                gan=pos.get('gan',0)
                gan_pct=(price-pos["precio_entry"])/pos["precio_entry"]*100 if price else 0
                cls="pos" if gan>=0 else "neg"
                html+=f"<div class='card {cls}'><b>🎯 {sym} ${price:.4f} | {gan_pct:+.2f}% <span class='live'>VIVO</span></b><br>Entrada ${pos['precio_entry']:.4f} | <b>{gan:+.2f}$</b> Monto ${pos['monto']} {'(E1)' if pos.get('es_dual')==1 else '(E2)' if pos.get('es_dual')==2 else ''}<br><a class='graf' href='/chart/{sym}'>📈 GRAFICA VIVO</a> <a class='graf' style='background:#a855f7;color:#fff;margin-top:5px' href='/dual/{sym}'>🔥 DUAL</a></div>"
            else:
                html+=f"<div class='card'><b>{sym} ${price:.4f} <span class='live'>VIVO</span></b> RSI {rsi:.1f} | EMA ${ema20:.2f}<br><a class='graf' href='/chart/{sym}'>📈 VER VIVO</a> <a class='graf' style='background:#a855f7;color:#fff;margin-top:5px' href='/dual/{sym}'>🔥 DUAL</a></div>"
        except: html+=f"<div class='card'><b>{sym} consultando...</b></div>"
    html+="</body></html>"
    return html

@app.route("/api/klines/<sym>")
def api_klines(sym):
    try:
        if sym in ["NVDA","TSLA","XAUUSD"]:
            ysym="GC=F" if sym=="XAUUSD" else sym
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=2d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
            res=r['chart']['result'][0]
            closes=res['indicators']['quote'][0]['close']; opens=res['indicators']['quote'][0]['open']; highs=res['indicators']['quote'][0]['high']; lows=res['indicators']['quote'][0]['low']; stamps=res['timestamp']
            out=[]
            for i in range(len(stamps)):
                if closes[i] is None: continue
                out.append({"time":stamps[i],"open":opens[i],"high":highs[i],"low":lows[i],"close":closes[i]})
            return out[-200:]
        kl=get_klines_robust(sym)
        out=[]
        for k in kl: out.append({"time":int(k[0]/1000),"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4])})
        return out
    except: return []

@app.route("/api/price/<sym>")
def api_price(sym):
    try: return {"price": P(sym), "time": int(time.time())}
    except: return {"price": 0, "time": int(time.time())}

@app.route("/chart/<sym>")
def chart(sym):
    p=P(sym); rsi,_,ema,_=AN(sym)
    pos=next((x for x in data["pos"] if x["sym"]==sym), None)
    entry=pos["precio_entry"] if pos else 0
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}.h{{padding:10px;background:#111;display:flex;justify-content:space-between;align-items:center}} a{{color:#ffcc00;text-decoration:none;font-weight:bold}} #chart{{width:100%;height:78vh}}.info{{padding:8px;font-size:12px;background:#1a1a1a;display:flex;gap:10px;flex-wrap:wrap;align-items:center}}.dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}.live{{background:#00ff88;color:#000;padding:2px 8px;border-radius:10px;font-weight:bold;animation:blink 1s infinite}}@keyframes blink{{0%{{opacity:1}}50%{{opacity:0.3}}}}</style>
    </head><body>
    <div class="h"><a href="/">← PRO</a><b id="title">🔥 {sym} ${p:.4f} RSI {rsi:.1f}</b><span class="live">● EN VIVO</span></div>
    <div class="info"><span><i class="dot" style="background:#2962ff"></i> EMA20</span>
      {f'<span><i class="dot" style="background:#00ff88"></i> ENT ${entry:.4f}</span><span><i class="dot" style="background:#ffcc00"></i> TP1</span><span><i class="dot" style="background:#ff1744"></i> TP2</span><span><i class="dot" style="background:#ff0000"></i> SL</span>' if entry else '<span>🎯 Cazando</span>'}
      <span id="lastupdate" style="color:#00ff88;margin-left:auto"></span>
    </div>
    <div id="chart"></div>
    <script>
    let chart, candle, emaLine; let lastData=[];
    async function loadInitial(){{
      const res = await fetch('/api/klines/{sym}'); const data = await res.json();
      lastData=data;
      chart = LightweightCharts.createChart(document.getElementById('chart'), {{layout:{{background:{{color:'#000'}},textColor:'#fff'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}},timeScale:{{timeVisible:true, secondsVisible:true}}}});
      candle = chart.addCandlestickSeries(); candle.setData(data);
      let sum=0; const emaData=[];
      for(let i=0;i<data.length;i++){{ sum+=data[i].close; if(i>=19){{ if(i>19) sum-=data[i-20].close; emaData.push({{time:data[i].time,value:sum/20}}); }} }}
      emaLine = chart.addLineSeries({{color:'#2962ff',lineWidth:1}}); emaLine.setData(emaData);
      const entry={entry};
      if(entry>0){{
        const eLine = chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); eLine.setData(data.map(d=>({{time:d.time,value:entry}})));
        const t1 = chart.addLineSeries({{color:'#ffcc00',lineWidth:1,lineStyle:1}}); t1.setData(data.map(d=>({{time:d.time,value:entry*1.018}})));
        const t2 = chart.addLineSeries({{color:'#ff1744',lineWidth:1,lineStyle:3}}); t2.setData(data.map(d=>({{time:d.time,value:entry*1.035}})));
        const sl = chart.addLineSeries({{color:'#ff0000',lineWidth:2,lineStyle:2}}); sl.setData(data.map(d=>({{time:d.time,value:entry*0.93}})));
      }}
      chart.timeScale().fitContent();
    }}
    async function liveUpdate(){{
      try{{
        const res = await fetch('/api/price/{sym}'); const j = await res.json();
        const price = j.price; if(!price || price==0) return;
        document.getElementById('title').innerText = '🔥 {sym} $'+price.toFixed(4)+' VIVO';
        document.getElementById('lastupdate').innerText = '● '+new Date().toLocaleTimeString()+' $'+price.toFixed(4);
        if(lastData.length>0){{
          const lastCandle = lastData[lastData.length-1];
          const now = Math.floor(Date.now()/1000);
          if(now - lastCandle.time < 300){{
            lastCandle.close = price; lastCandle.high = Math.max(lastCandle.high, price); lastCandle.low = Math.min(lastCandle.low, price);
            candle.update(lastCandle);
          }} else {{
            const newCandle = {{time: now, open: price, high: price, low: price, close: price}};
            lastData.push(newCandle); candle.update(newCandle);
          }}
        }}
      }}catch(e){{}}
    }}
    loadInitial().then(()=>{{ setInterval(liveUpdate, 3000); }});
    </script></body></html>
    '''

@app.route("/dual/<sym>")
def dual(sym):
    sym=sym.upper()
    fc=get_first_candle_ny(sym)
    liq=detectar_liquidez(sym)
    return f"""
    <html><head><meta name='viewport' content='width=device-width'><style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
 .card{{background:#1a1a1a;padding:14px;border-radius:15px;margin:10px 0;border-left:4px solid #00ff88}}
 .card.purple{{border-left-color:#a855f7}}.card.red{{border-left-color:#ff1744}}
 .tag{{padding:4px 10px;border-radius:20px;font-size:11px;font-weight:bold}}
 .tag.vivo{{background:#00ff88;color:#000}}.tag.wait{{background:#ffcc00;color:#000}}
    </style></head><body>
    <a href='/' style='color:#ffcc00;text-decoration:none'>← PRO V32.2</a>
    <h2>🔥 DUAL {sym} - $3500</h2>
    <div class='card purple'>
    <span class='tag vivo'>E1 AUTO 1 VELA $1750</span><br><br>
    {f"<b>HIGH 9:30 NY:</b> ${fc['high']:.2f}<br><b>LOW:</b> ${fc['low']:.2f}<br><b>{fc['time']}</b><br><br>Entra AUTO si rompe HIGH*1.0015 o LOW*0.9985 7:35-9AM" if fc else "Esperando apertura 7:30 AM Nogales"}
    </div>
    <div class='card red'>
    <span class='tag wait'>E2 CONFIRMA $1750</span><br><br>
    {f"Triple ${liq['liquidez_en']:.2f}<br>OB ${liq['orderblock']:.2f}<br>Res ${liq['resistencia']:.2f}<br>Target ${liq['target']:.2f}<br><br>Escribe en TG: <b>SI {sym}</b> para entrar" if liq else "Escaneando triple minimo..."}
    </div>
    <iframe src='/chart/{sym}' style='width:100%;height:55vh;border:none;border-radius:10px'></iframe>
    </body></html>
    """

@app.route("/webhook", methods=['POST'])
def webhook():
    if request.data:
        update=telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
    return "ok",200

@app.route("/setwebhook")
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{DASH_URL}/webhook")
    return "webhook set OK"

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    try:
        txt=m.text.upper().strip() if m.text else ""
        if m.chat.id not in data["alert_users"]:
            data["alert_users"].append(m.chat.id)
            save()
        # CONFIRMA E2
        if txt.startswith("SI "):
            sym = txt.split(" ")[1]
            if sym in ALL_COINS:
                liq = detectar_liquidez(sym)
                price=P(sym)
                if data['b']>=MONTO_E2 and len(data['pos'])<MAX_POS and price>0:
                    data['pos'].append({"sym":sym,"monto":MONTO_E2,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False,"es_dual":2,"tipo":"LIQUIDEZ"})
                    data['b']-=MONTO_E2; save()
                    tg(m.chat.id, f"✅ E2 CONFIRMADO {sym} ${price:.4f} $1750 MXN\nOB ${liq['orderblock']:.2f} SL arriba\nTarget ${liq['target']:.2f}\n{DASH_URL}/chart/{sym}", kb())
                    return
                else:
                    tg(m.chat.id, f"❌ Saldo insuficiente o sin precio", kb()); return
        if txt in ["/START","START","BALANCE","/BALANCE","B","/B"]:
            tot,flot=totals()
            det=""
            for p in data["pos"]:
                try:
                    pr=P(p["sym"])
                    if pr==0: pr=p["precio_entry"]
                    g=(pr-p["precio_entry"])/pr*100
                    det+=f"{p['sym']} {g:+.2f}% ${p.get('gan',0):+.2f} {'E1' if p.get('es_dual')==1 else 'E2' if p.get('es_dual')==2 else ''}\n"
                except: pass
            tg(m.chat.id, f"🔥 V32.2 DUAL FINAL 🔥\nTotal: ${tot:.2f} Flot {flot:+.2f}$\nSaldo: ${data['b']:.2f}\nGan Hoy: ${data['gan_hoy']:.2f}\nTotal: ${data['gan_total']:.2f}\nPos: {len(data['pos'])}/{MAX_POS}\n\n{det if det else 'Sin presas'}\n\nDUAL: /dual/NVDA\n{DASH_URL}", kb())
            return
        if txt=="DASHBOARD": tg(m.chat.id, f"📊 {DASH_URL}\nDUAL {DASH_URL}/dual/NVDA", kb()); return
        if txt=="DUAL": tg(m.chat.id, f"🔥 DUAL $3500\nE1 AUTO $1750 7:35-9AM\nE2 CONFIRMA $1750 Escribe SI NVDA\n{DASH_URL}/dual/NVDA\n{DASH_URL}/dual/TSLA", kb()); return
        if txt=="AUTO ON": data['auto_buy']=True; save(); tg(m.chat.id, "🔥 V32.2 ON - Motor RSI + E1 AUTO + E2 ALERTA", kb()); return
        if txt=="AUTO OFF": data['auto_buy']=False; save(); tg(m.chat.id, "⏸️ PAUSA", kb()); return
        if txt in ALL_COINS:
            try:
                rsi,price,ema,btc_t=AN(txt)
                if price==0:
                    pos=next((x for x in data["pos"] if x["sym"]==txt), None)
                    if pos: price=pos["precio_entry"]
                btc1h=get_btc_1h()
                pos=next((x for x in data["pos"] if x["sym"]==txt), None)
                if pos:
                    gan_pct=(price-pos["precio_entry"])/pos["precio_entry"]*100 if price else 0
                    msg=f"🎯 {txt} ${price:.4f} VIVO\nRSI {rsi:.1f} Gan {gan_pct:+.2f}% ${pos.get('gan',0):+.2f}\nEnt ${pos['precio_entry']:.4f}\n{DASH_URL}/chart/{txt}"
                else:
                    msg=f"🎯 {txt} ${price:.4f} VIVO\nRSI {rsi:.1f} EMA ${ema:.2f}\nBTC 1h {btc1h:+.2f}%\n{DASH_URL}/chart/{txt}\nDUAL {DASH_URL}/dual/{txt}"
                tg(m.chat.id, msg, kb())
            except: tg(m.chat.id, f"🎯 {txt} VIVO\n{DASH_URL}/chart/{txt}", kb())
            return
        tg(m.chat.id, f"🔥 V32.2 DUAL FINAL\nMotor $5k + DUAL $3500\n{DASH_URL}\nDUAL {DASH_URL}/dual/NVDA", kb())
    except Exception as e:
        print(f"Error {e}")
        try: tg(m.chat.id, f"🔥 V32.2 {len(data['pos'])}/{MAX_POS}\n{DASH_URL}", kb())
        except: pass

def auto_loop():
    while True:
        try:
            now=datetime.now(ZoneInfo('America/Mexico_City'))
            ny_now = datetime.now(ZoneInfo('America/New_York'))
            if now.hour==22 and now.minute<4 and data.get("last_report_date")!=now.strftime("%Y-%m-%d"):
                tot,flot=totals()
                msg=f"📊 RESUMEN 10 PM V32.2 🔥\nTotal ${tot:.2f}\nSaldo ${data['b']:.2f}\nFlot ${flot:+.2f}\nGan Hoy ${data['gan_hoy']:+.2f}\nTotal ${data['gan_total']:+.2f}\nE1 AUTO + E2 LISTOS\n{DASH_URL}"
                for u in data["alert_users"]: tg(u,msg)
                data["last_report_date"]=now.strftime("%Y-%m-%d"); save()

            # E1 AUTO + E2 ALERTA
            try:
                if ny_now.weekday()<5 and 9<=ny_now.hour<=10 and data.get('auto_buy'):
                    for sym in ["NVDA","TSLA"]:
                        fc=get_first_candle_ny(sym)
                        if not fc: continue
                        price=P(sym)
                        if price==0: continue
                        ya_dual=any(p.get('es_dual')==1 and p['sym']==sym for p in data['pos'])
                        if ya_dual: continue
                        if price > fc['high']*1.0015 or price < fc['low']*0.9985:
                            if data['b']>=MONTO_E1 and len(data['pos'])<MAX_POS:
                                data['pos'].append({"sym":sym,"monto":MONTO_E1,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False,"es_dual":1,"tipo":"1VELA"})
                                data['b']-=MONTO_E1; save()
                                for u in data["alert_users"]: tg(u,f"🔥 E1 AUTO 1 VELA {sym} ${price:.4f}\nRompe {'HIGH' if price>fc['high'] else 'LOW'} ${fc['high']:.2f}/{fc['low']:.2f}\n$1750 MXN\n{DASH_URL}/chart/{sym}")
                if ny_now.weekday()<5 and data.get('auto_buy'):
                    for sym in ["NVDA","TSLA"]:
                        liq=detectar_liquidez(sym)
                        if liq and sym not in LIQUIDEZ_DATA:
                            LIQUIDEZ_DATA[sym]=liq
                            for u in data["alert_users"]: tg(u,f"🎯 E2 LIQUIDEZ {sym}\nTriple ${liq['liquidez_en']:.2f}\nOB ${liq['orderblock']:.2f}\nTarget ${liq['target']:.2f} RR 1:4.5\nEscribe SI {sym} para entrar $1750\n{DASH_URL}/dual/{sym}")
                        elif not liq and sym in LIQUIDEZ_DATA: del LIQUIDEZ_DATA[sym]
            except: pass

            btc_1h = get_btc_1h()
            for sym in data["coins"][:]:
                try:
                    if sym in COINS_STOCKS and not (8 <= now.hour <= 15): continue
                    rsi,price,ema20,btc_t=AN(sym)
                    if price==0: continue
                    for p in data["pos"][:]:
                        if p["sym"]!=sym: continue
                        gan_pct=(price-p["precio_entry"])/p["precio_entry"]*100
                        p["max_price"]=max(p.get("max_price",0), price)
                        p["gan"]=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                        if gan_pct <= STOP_LOSS_PCT:
                            loss=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                            data["b"]+=p["monto"]+loss; data["gan_total"]+=loss; data["gan_hoy"]+=loss; data["pos"].remove(p); save()
                            for u in data["alert_users"]: tg(u,f"🛑 STOP {sym} {gan_pct:.2f}% {loss:.2f}$")
                            continue
                        if not p.get("tp1_done") and gan_pct >= TP1_PCT:
                            if p["monto"]>=400:
                                profit_half=(price-p["precio_entry"])/p["precio_entry"]*(p["monto"]/2)
                                data["b"]+=p["monto"]/2 + profit_half; data["gan_total"]+=profit_half; data["gan_hoy"]+=profit_half; p["monto"]=p["monto"]/2; p["tp1_done"]=True; save()
                                for u in data["alert_users"]: tg(u,f"💰 TP1 {sym} +{gan_pct:.2f}% +${profit_half:.2f}")
                            else:
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]; data["b"]+=p["monto"]+profit; data["gan_total"]+=profit; data["gan_hoy"]+=profit; data["pos"].remove(p); save()
                                for u in data["alert_users"]: tg(u,f"💰 TP1 {sym} +{gan_pct:.2f}% +${profit:.2f}")
                            continue
                        if p.get("tp1_done"):
                            if gan_pct >= TP2_PCT or (p["max_price"]>p["precio_entry"]*1.02 and price < p["max_price"]*(1-TRAILING_PCT/100)):
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]; data["b"]+=p["monto"]+profit; data["gan_total"]+=profit; data["gan_hoy"]+=profit; data["pos"].remove(p); save()
                                for u in data["alert_users"]: tg(u,f"🚀 TP2/TRAIL {sym} +{gan_pct:.2f}% +${profit:.2f}")
                    if btc_1h < BTC_CRASH_PCT: continue
                    if rsi<32 and price>ema20*0.995 and btc_t>-1.5:
                        if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(pp['sym']==sym for pp in data["pos"] if not pp.get('es_dual')):
                            if data["b"]<MONTO_TRADE: continue
                            data["pos"].append({"sym":sym,"monto":MONTO_TRADE,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False})
                            data["b"]-=MONTO_TRADE; data["trades_hoy"]+=1; save()
                            for u in data["alert_users"]: tg(u,f"🔥 CASERIA V32.2 {sym} ${price:.4f} RSI {rsi:.1f} x ${MONTO_TRADE}\n{DASH_URL}/chart/{sym}")
                except: continue
                time.sleep(1.5)
            time.sleep(40)
        except Exception as e:
            print(f"Loop err {e}"); time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
