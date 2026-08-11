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
    btc1h = get_btc_1h()
    html=f"""<html><head><meta name='viewport' content='width=device-width'><style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
.card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:4px solid #00ff88}}
.card.neg{{border-left-color:#ff1744}}.card.pos{{border-left-color:#00ff88}}
.top{{border:2px solid #ffcc00;border-radius:15px;padding:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;background:#1a1500}}
.graf{{background:#ffcc00;color:#000;width:100%;padding:12px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}
.alert{{background:#ff1744;color:#fff;padding:8px;border-radius:8px;margin:8px 0;text-align:center;font-weight:bold}}
    </style></head><body>
    <div class='top'><div><b>🔥 V31.1 PRO DE CASERIA 🔥</b><br>{'🟢 CAZANDO' if data['auto_buy'] else '🔴 PAUSA'} | {len(data['pos'])}/{MAX_POS} | BTC 1h {btc1h:+.2f}%</div><div>Total ${tot:.2f}<br>Flot {flot:+.2f}</div></div>
    {f'<div class="alert">⚠️ BTC CRASH {btc1h:.2f}% - COMPRAS PAUSADAS</div>' if btc1h < BTC_CRASH_PCT else ''}
    <div style='display:flex;justify-content:space-between;margin:12px 0;flex-wrap:wrap'><span>Saldo ${data['b']:.2f}</span><span>Hoy ${data['gan_hoy']:.2f}</span><span>Total ${data['gan_total']:.2f}</span></div>"""
    for sym in ALL_COINS:
        try:
            rsi,price,ema20,btc_t=AN(sym)
            pos=next((x for x in data["pos"] if x["sym"]==sym), None)
            if pos:
                gan=(price-pos["precio_entry"])/pos["precio_entry"]*pos["monto"] if price else 0
                gan_pct=(price-pos["precio_entry"])/pos["precio_entry"]*100 if price else 0
                pos["gan"]=gan
                cls="pos" if gan>=0 else "neg"
                html+=f"<div class='card {cls}'><b>🎯 {sym} ${price:.4f} | {gan_pct:+.1f}%</b><br>Entrada ${pos['precio_entry']:.4f} | <b>{gan:+.2f}$</b> Monto ${pos['monto']}<br>SL {STOP_LOSS_PCT}% | TP1 {TP1_PCT}% | TP2 {TP2_PCT}%<br><a class='graf' href='/chart/{sym}'>📈 GRAFICA PRO</a></div>"
            else:
                html+=f"<div class='card'><b>{sym} ${price:.4f}</b> RSI {rsi:.1f} | EMA ${ema20:.2f}<br><a class='graf' href='/chart/{sym}'>📈 VER GRAFICA</a></div>"
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

@app.route("/chart/<sym>")
def chart(sym):
    p=P(sym); rsi,_,ema,_=AN(sym)
    pos=next((x for x in data["pos"] if x["sym"]==sym), None)
    entry=pos["precio_entry"] if pos else 0
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}.h{{padding:10px;background:#111;display:flex;justify-content:space-between}} a{{color:#ffcc00;text-decoration:none;font-weight:bold}} #chart{{width:100%;height:75vh}}.info{{padding:8px;font-size:12px;background:#1a1a1a;display:flex;gap:10px;flex-wrap:wrap}}.dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}</style>
    </head><body>
    <div class="h"><a href="/">← PRO</a><b>🔥 {sym} ${p:.4f} RSI {rsi:.1f}</b></div>
    <div class="info"><span><i class="dot" style="background:#2962ff"></i> EMA20</span>
      {f'<span><i class="dot" style="background:#00ff88"></i> ENT ${entry:.4f}</span><span><i class="dot" style="background:#ffcc00"></i> TP1 +1.8%</span><span><i class="dot" style="background:#ff1744"></i> TP2 +3.5%</span><span><i class="dot" style="background:#ff0000"></i> SL -7%</span>' if entry else '<span>🎯 Cazando RSI&lt;32</span>'}
    </div>
    <div id="chart"></div>
    <script>
    async function load(){{
      const res = await fetch('/api/klines/{sym}'); const data = await res.json();
      const chart = LightweightCharts.createChart(document.getElementById('chart'), {{layout:{{background:{{color:'#000'}},textColor:'#fff'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}},timeScale:{{timeVisible:true}}}});
      const candle = chart.addCandlestickSeries(); candle.setData(data);
      let sum=0; const emaData=[];
      for(let i=0;i<data.length;i++){{ sum+=data[i].close; if(i>=19){{ if(i>19) sum-=data[i-20].close; emaData.push({{time:data[i].time,value:sum/20}}); }} }}
      const emaLine = chart.addLineSeries({{color:'#2962ff',lineWidth:1}}); emaLine.setData(emaData);
      const entry={entry};
      if(entry>0){{
        const eLine = chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}}); eLine.setData(data.map(d=>({{time:d.time,value:entry}})));
        const t1 = chart.addLineSeries({{color:'#ffcc00',lineWidth:1,lineStyle:1}}); t1.setData(data.map(d=>({{time:d.time,value:entry*1.018}})));
        const t2 = chart.addLineSeries({{color:'#ff1744',lineWidth:1,lineStyle:3}}); t2.setData(data.map(d=>({{time:d.time,value:entry*1.035}})));
        const sl = chart.addLineSeries({{color:'#ff0000',lineWidth:2,lineStyle:2}}); sl.setData(data.map(d=>({{time:d.time,value:entry*0.93}})));
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

# FIX 100% - BOTONES BLINDADOS ANTI-CRASH
@bot.message_handler(func=lambda m: True)
def all_msg(m):
    try:
        txt=m.text.upper().strip() if m.text else ""
        if m.chat.id not in data["alert_users"]:
            data["alert_users"].append(m.chat.id)
            save()

        if txt in ["/START","START","BALANCE","/BALANCE","B","/B"]:
            tot,flot=totals()
            det=""
            for p in data["pos"]:
                try:
                    pr=P(p["sym"])
                    g=(pr-p["precio_entry"])/p["precio_entry"]*100 if pr else 0
                    det+=f"{p['sym']}: {g:+.2f}% ${p.get('gan',0):+.2f}\n"
                except: det+=f"{p['sym']}:...\n"
            tg(m.chat.id, f"🔥 V31.1 PRO DE CASERIA 🔥\nTotal: ${tot:.2f} (Flot {flot:+.2f}$)\nSaldo: ${data['b']:.2f}\nGan Hoy: ${data['gan_hoy']:.2f}\nGan Total: ${data['gan_total']:.2f}\nPos: {len(data['pos'])}/{MAX_POS}\nSL -7% | TP 1.8%/3.5%\n\nP&L POR PRESA:\n{det if det else 'Sin presas - cazando...'}\n\nDashboard: {DASH_URL}", kb())
            return

        if txt=="DASHBOARD":
            tg(m.chat.id, f"📊 DASHBOARD PRO\n{DASH_URL}", kb())
            return

        if txt=="AUTO ON":
            data['auto_buy']=True; save()
            tg(m.chat.id, "🔥 AUTO ON - MODO DE CASERIA PRO ACTIVADO\nCazando RSI<32 + SL -7% + TP 1.8%/3.5%", kb())
            return

        if txt=="AUTO OFF":
            data['auto_buy']=False; save()
            tg(m.chat.id, "⏸️ PAUSA - CASERIA DETENIDA", kb())
            return

        if txt in ALL_COINS:
            try:
                rsi,price,ema,btc_t=AN(txt)
                btc1h=get_btc_1h()
                pos=next((x for x in data["pos"] if x["sym"]==txt), None)
                if pos:
                    gan_pct=(price-pos["precio_entry"])/pos["precio_entry"]*100 if price else 0
                    msg=f"🎯 {txt} ${price:.4f}\nRSI {rsi:.1f} | Gan {gan_pct:+.2f}% ${pos.get('gan',0):+.2f}\nEntrada ${pos['precio_entry']:.4f}\nMonto ${pos['monto']} | Max ${pos.get('max_price',price):.4f}\nSL ${pos['precio_entry']*0.93:.4f} | TP1 ${pos['precio_entry']*1.018:.4f} | TP2 ${pos['precio_entry']*1.035:.4f}\nBTC 1h {btc1h:+.2f}%\n\nGrafica: {DASH_URL}/chart/{txt}"
                else:
                    msg=f"🎯 {txt} ${price:.4f}\nRSI {rsi:.1f} | EMA ${ema:.2f}\nBTC 24h {btc_t:+.2f}% | BTC 1h {btc1h:+.2f}%\nSin pos - cazando RSI<32\n\nGrafica: {DASH_URL}/chart/{txt}"
                tg(m.chat.id, msg, kb())
            except Exception as e:
                tg(m.chat.id, f"🎯 {txt} - consultando precio...\nAPI ocupada, toca de nuevo en 2s\n{DASH_URL}/chart/{txt}", kb())
            return

        tg(m.chat.id, f"🔥 V31.1 PRO activo\nUsa los botones de abajo 👇\n{DASH_URL}", kb())

    except Exception as e:
        print(f"Error handler {e}")
        try: tg(m.chat.id, f"🔥 Bot PRO activo - {len(data['pos'])}/{MAX_POS} pos\n{DASH_URL}\nUsa BALANCE", kb())
        except: pass

def auto_loop():
    while True:
        try:
            now=datetime.now(ZoneInfo('America/Mexico_City'))
            if now.hour==22 and now.minute<4 and data.get("last_report_date")!=now.strftime("%Y-%m-%d"):
                tot,flot=totals()
                msg=f"📊 RESUMEN 10 PM PRO DE CASERIA 🔥\nTotal ${tot:.2f}\nSaldo ${data['b']:.2f}\nFlot ${flot:+.2f}\nGan Hoy ${data['gan_hoy']:+.2f}\nTotal ${data['gan_total']:+.2f}\nTrades {data['trades_hoy']}\n{DASH_URL}"
                for u in data["alert_users"]: tg(u,msg)
                data["last_report_date"]=now.strftime("%Y-%m-%d"); save()

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
                            data["b"]+=p["monto"]+loss
                            data["gan_total"]+=loss
                            data["gan_hoy"]+=loss
                            data["pos"].remove(p); save()
                            for u in data["alert_users"]: tg(u,f"🛑 STOP LOSS {sym} {gan_pct:.2f}% {loss:.2f}$\nEntrada ${p['precio_entry']:.4f} -> {price:.4f}\n{DASH_URL}/chart/{sym}")
                            continue

                        if not p.get("tp1_done") and gan_pct >= TP1_PCT:
                            if p["monto"]>=400:
                                profit_half=(price-p["precio_entry"])/p["precio_entry"]*(p["monto"]/2)
                                data["b"]+=p["monto"]/2 + profit_half
                                data["gan_total"]+=profit_half
                                data["gan_hoy"]+=profit_half
                                p["monto"]=p["monto"]/2
                                p["tp1_done"]=True
                                save()
                                for u in data["alert_users"]: tg(u,f"💰 TP1 {sym} +{gan_pct:.2f}% +${profit_half:.2f} (50% vendido)\nDeja correr resto a +3.5%\n{DASH_URL}/chart/{sym}")
                            else:
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                                data["b"]+=p["monto"]+profit
                                data["gan_total"]+=profit
                                data["gan_hoy"]+=profit
                                data["pos"].remove(p); save()
                                for u in data["alert_users"]: tg(u,f"💰 VENTA TP1 FINAL {sym} +{gan_pct:.2f}% +${profit:.2f}\n{DASH_URL}/chart/{sym}")
                            continue

                        if p.get("tp1_done"):
                            if gan_pct >= TP2_PCT or (p["max_price"]>p["precio_entry"]*1.02 and price < p["max_price"]*(1-TRAILING_PCT/100)):
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                                data["b"]+=p["monto"]+profit
                                data["gan_total"]+=profit
                                data["gan_hoy"]+=profit
                                data["pos"].remove(p); save()
                                for u in data["alert_users"]: tg(u,f"🚀 TP2/TRAILING {sym} +{gan_pct:.2f}% +${profit:.2f}\nEntrada ${p['precio_entry']:.4f} -> {price:.4f}\n{DASH_URL}/chart/{sym}")

                    if btc_1h < BTC_CRASH_PCT: continue

                    if rsi<32 and price>ema20*0.995 and btc_t>-1.5:
                        if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(pp['sym']==sym for pp in data["pos"]):
                            if data["b"]<MONTO_TRADE: continue
                            data["pos"].append({"sym":sym,"monto":MONTO_TRADE,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False})
                            data["b"]-=MONTO_TRADE; data["trades_hoy"]+=1; save()
                            for u in data["alert_users"]: tg(u,f"🔥 CASERIA PRO {sym} ATRAPADO ${price:.4f} RSI {rsi:.1f} x ${MONTO_TRADE}\nSL -7% | TP 1.8%/3.5%\n{DASH_URL}/chart/{sym}")
                except: continue
                time.sleep(1.5)
            time.sleep(40)
        except Exception as e:
            print(f"Loop error {e}"); time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
