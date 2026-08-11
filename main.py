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
    except Exception as e: print(f"TG Error {e}")

def get_price_robust(sym):
    try:
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT",timeout=4).json()
        if 'price' in r and float(r['price'])>0: return float(r['price'])
    except: pass
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT",timeout=4).json()
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
            r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        if sym in COINS_STOCKS:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
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

def totals():
    tot=data['b']+sum([p['monto']+p.get('gan',0) for p in data['pos']])
    flot=sum([p.get('gan',0) for p in data['pos']])
    return tot, flot

def kb():
    m=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=4)
    m.add("BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA","NVDA","TSLA","XAUUSD","DASHBOARD","AUTO ON","AUTO OFF","BALANCE")
    return m

@app.route("/")
def home():
    tot, flot = totals()
    html=f"""<html><head><meta name='viewport' content='width=device-width'><style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
 .card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:4px solid #00ff88}}
 .card.neg{{border-left-color:#ff1744}}.card.pos{{border-left-color:#00ff88}}
 .top{{border:1.5px solid #ffcc00;border-radius:15px;padding:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;background:#1a1500}}
 .graf{{background:#ffcc00;color:#000;width:100%;padding:12px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}
    </style></head><body>
    <div class='top'><div><b>🔥 V30.1 DE CASERIA 🔥</b><br>{'🟢 AUTO ON - CAZANDO' if data['auto_buy'] else '🔴 AUTO OFF'} | {len(data['pos'])}/{MAX_POS} presas</div><div>Total ${tot:.2f} | Flot {flot:+.2f}</div></div>
    <div style='display:flex;justify-content:space-between;margin:12px 0;flex-wrap:wrap'><span>Saldo ${data['b']:.2f}</span><span>Hoy ${data['gan_hoy']:.2f}</span><span>Total ${data['gan_total']:.2f}</span></div>"""
    for sym in ALL_COINS:
        rsi,price,ema20,btc_t=AN(sym)
        pos=next((x for x in data["pos"] if x["sym"]==sym), None)
        if pos:
            gan=(price-pos["precio_entry"])/pos["precio_entry"]*pos["monto"] if price else 0
            gan_pct=(price-pos["precio_entry"])/pos["precio_entry"]*100 if price else 0
            pos["gan"]=gan
            cls="pos" if gan>=0 else "neg"
            html+=f"<div class='card {cls}'><b>🎯 {sym} ${price:.4f} RSI {rsi:.1f}</b><br>Entrada ${pos['precio_entry']:.4f} | <b>{gan:+.2f}$ ({gan_pct:+.2f}%)</b><br>TP +1.8% = ${pos['precio_entry']*1.018:.4f}<br><a class='graf' href='/chart/{sym}'>📈 VER GRAFICA DE CASERIA</a></div>"
        else:
            html+=f"<div class='card'><b>{sym} ${price:.4f}</b> RSI {rsi:.1f} | EMA ${ema20:.2f}<br><a class='graf' href='/chart/{sym}'>📈 VER GRAFICA</a></div>"
    html+="</body></html>"
    return html

@app.route("/api/klines/<sym>")
def api_klines(sym):
    try:
        if sym in ["NVDA","TSLA","XAUUSD"]:
            ysym="GC=F" if sym=="XAUUSD" else sym
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=2d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
            res=r['chart']['result'][0]
            closes=res['indicators']['quote'][0]['close']; opens=res['indicators']['quote'][0]['open']; highs=res['indicators']['quote'][0]['high']; lows=res['indicators']['quote'][0]['low']; vols=res['indicators']['quote'][0]['volume']; stamps=res['timestamp']
            out=[]
            for i in range(len(stamps)):
                if closes[i] is None: continue
                out.append({"time":stamps[i],"open":opens[i],"high":highs[i],"low":lows[i],"close":closes[i],"volume":vols[i] or 0})
            return out[-200:]
        kl=get_klines_robust(sym)
        out=[]
        for k in kl: out.append({"time":int(k[0]/1000),"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4]),"volume":float(k[5])})
        return out
    except: return []

@app.route("/chart/<sym>")
def chart(sym):
    p=P(sym); rsi,_,ema,_=AN(sym)
    pos=next((x for x in data["pos"] if x["sym"]==sym), None)
    entry=pos["precio_entry"] if pos else 0
    tp1=entry*1.018 if entry else 0
    tp2=entry*1.03 if entry else 0
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}.h{{padding:10px;background:#111;display:flex;justify-content:space-between}} a{{color:#ffcc00;text-decoration:none;font-weight:bold}} #chart{{width:100%;height:75vh}}.info{{padding:8px;font-size:12px;background:#1a1a1a;display:flex;gap:10px;flex-wrap:wrap}}.dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}</style>
    </head><body>
    <div class="h"><a href="/">← DE CASERIA</a><b>🔥 {sym} ${p:.4f} RSI {rsi:.1f}</b></div>
    <div class="info"><span><i class="dot" style="background:#2962ff"></i> EMA20</span>
      {f'<span><i class="dot" style="background:#00ff88"></i> ENTRADA ${entry:.4f}</span><span><i class="dot" style="background:#ffcc00"></i> TP +1.8% ${tp1:.4f}</span><span><i class="dot" style="background:#ff1744"></i> TP +3% ${tp2:.4f}</span>' if entry else '<span>🎯 Sin presa - cazando RSI&lt;32</span>'}
    </div>
    <div id="chart"></div>
    <script>
    async function load(){{
      const res = await fetch('/api/klines/{sym}'); const data = await res.json();
      const chart = LightweightCharts.createChart(document.getElementById('chart'), {{layout:{{background:{{color:'#000'}},textColor:'#fff'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}},timeScale:{{timeVisible:true}}}});
      const candle = chart.addCandlestickSeries(); candle.setData(data.map(d=>({{time:d.time,open:d.open,high:d.high,low:d.low,close:d.close}})));
      let sum=0; const emaData=[];
      for(let i=0;i<data.length;i++){{ sum+=data[i].close; if(i>=19){{ if(i>19) sum-=data[i-20].close; emaData.push({{time:data[i].time,value:sum/20}}); }} }}
      const emaLine = chart.addLineSeries({{color:'#2962ff',lineWidth:1}}); emaLine.setData(emaData);
      const entry={entry};
      if(entry>0){{
        const eLine = chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); eLine.setData(data.map(d=>({{time:d.time,value:entry}})));
        const t1 = chart.addLineSeries({{color:'#ffcc00',lineWidth:1,lineStyle:1}}); t1.setData(data.map(d=>({{time:d.time,value:{tp1}}})));
        const t2 = chart.addLineSeries({{color:'#ff1744',lineWidth:1,lineStyle:3}}); t2.setData(data.map(d=>({{time:d.time,value:{tp2}}})));
      }}
      chart.timeScale().fitContent();
    }} load();
    </script></body></html>
    '''

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
    txt=m.text.upper().strip() if m.text else ""
    if m.chat.id not in data["alert_users"]: data["alert_users"].append(m.chat.id); save()
    if txt in ["/START","START","BALANCE","/BALANCE","B","/B"]:
        tot,flot=totals()
        det=""
        for p in data["pos"]:
            pr=P(p["sym"])
            if pr==0: continue
            g=(pr-p["precio_entry"])/p["precio_entry"]*100
            det+=f"{p['sym']}: {g:+.2f}% ${p.get('gan',0):+.2f}\n"
        tg(m.chat.id, f"🔥 V30.1 DE CASERIA 🔥\nTotal: ${tot:.2f} (Flot {flot:+.2f}$)\nSaldo: ${data['b']:.2f}\nGan Hoy: ${data['gan_hoy']:.2f}\nGan Total: ${data['gan_total']:.2f}\nPos: {len(data['pos'])}/{MAX_POS}\n\nP&L POR PRESA:\n{det if det else 'Sin presas - cazando...'}\n\nDashboard: {DASH_URL}", kb())
        return
    if txt=="DASHBOARD": tg(m.chat.id, f"📊 {DASH_URL}", kb()); return
    if txt=="AUTO ON": data['auto_buy']=True; save(); tg(m.chat.id, "🔥 AUTO ON - MODO DE CASERIA ACTIVADO", kb()); return
    if txt=="AUTO OFF": data['auto_buy']=False; save(); tg(m.chat.id, "⏸️ PAUSA CASERIA", kb()); return
    if txt in ALL_COINS:
        rsi,price,ema,btc_t=AN(txt)
        pos=next((x for x in data["pos"] if x["sym"]==txt), None)
        extra=f"\nEntrada ${pos['precio_entry']:.4f} Gan {pos.get('gan',0):+.2f}$" if pos else ""
        tg(m.chat.id, f"🎯 {txt} RSI {rsi:.1f} ${price:.4f}\nEMA ${ema:.2f} BTC {btc_t:.2f}%{extra}\nGrafica: {DASH_URL}/chart/{txt}", kb())
        return

def auto_loop():
    while True:
        try:
            now=datetime.now(ZoneInfo('America/Mexico_City'))
            if now.hour==22 and now.minute<4 and data.get("last_report_date")!=now.strftime("%Y-%m-%d"):
                tot,flot=totals()
                det=""
                for p in data["pos"]:
                    pr=P(p["sym"])
                    if pr==0: continue
                    g=(pr-p["precio_entry"])/p["precio_entry"]*100
                    det+=f"{p['sym']} {g:+.1f}% | "
                msg=f"📊 RESUMEN 10 PM DE CASERIA 🔥\nTotal ${tot:.2f}\nSaldo ${data['b']:.2f}\nFlotante ${flot:+.2f}\nGan Hoy ${data['gan_hoy']:+.2f}\nGan Total ${data['gan_total']:+.2f}\nTrades Hoy {data['trades_hoy']}\nPresas {len(data['pos'])}/{MAX_POS}\n{det}\n{DASH_URL}"
                for u in data["alert_users"]: tg(u,msg)
                data["last_report_date"]=now.strftime("%Y-%m-%d"); save()

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
                        if gan_pct>=1.8 or (p["max_price"]>p["precio_entry"]*1.01 and price < p["max_price"]*0.995):
                            profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                            data["b"]+=p["monto"]+profit
                            data["gan_total"]+=profit
                            data["gan_hoy"]+=profit
                            data["pos"].remove(p); save()
                            for u in data["alert_users"]:
                                tg(u,f"💰 VENTA DE CASERIA {sym} {gan_pct:+.2f}% +${profit:.2f}\nEntrada ${p['precio_entry']:.4f} -> {price:.4f}\nNuevo Saldo ${data['b']:.2f}\n{DASH_URL}/chart/{sym}")
                    if rsi<32 and price>ema20*0.995 and btc_t>-1.5:
                        if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(pp['sym']==sym for pp in data["pos"]):
                            if data["b"]<MONTO_TRADE: continue
                            data["pos"].append({"sym":sym,"monto":MONTO_TRADE,"gan":0,"precio_entry":price,"max_price":price})
                            data["b"]-=MONTO_TRADE; data["trades_hoy"]+=1; save()
                            for u in data["alert_users"]: tg(u,f"🔥 CASERIA {sym} ATRAPADO ${price:.4f} RSI {rsi:.1f} x ${MONTO_TRADE}\n{DASH_URL}/chart/{sym}")
                except: continue
                time.sleep(1.5)
            time.sleep(45)
        except Exception as e:
            print(f"Loop error {e}"); time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
