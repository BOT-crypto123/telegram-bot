import os, json, time, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "123456:TEST"
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

COINS_PRO = ["XAUUSD","BTC"]
COINS_DUAL = ["NVDA","TSLA"]
ALL_COINS = ["XAUUSD","BTC","NVDA","TSLA"]
MAX_POS=6
SALDO_INICIAL=5000
DASH_URL="https://telegram-bot-cijp.onrender.com"

# NUEVOS MONTOS V34 CONCENTRADO
MONTO_PRO_XAU=1500
MONTO_PRO_BTC=500
MONTO_E1=750
MONTO_E2_STOCK=750
MONTO_E2_XAU=1500

def get_levels(sym, entry):
    if sym=="XAUUSD": return entry-30, entry+18, entry+40
    if sym in COINS_DUAL: return entry*0.98, entry*1.012, entry*1.025
    return entry*0.93, entry*1.018, entry*1.035

try:
    with open("data.json","r") as f: data=json.load(f)
    if data.get("b",0)<200 and len(data.get("pos",[]))==0: data["b"]=SALDO_INICIAL
except: data={"b":SALDO_INICIAL,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[],"last_report_date":"","last_apertura":""}
data["coins"]=ALL_COINS
if "last_apertura" not in data: data["last_apertura"]=""

def save():
    try:
        with open("data.json","w") as f: json.dump(data,f)
    except: pass

def tg(chat,txt,markup=None):
    try: bot.send_message(chat,txt,reply_markup=markup, disable_web_page_preview=True)
    except: pass

def P(sym):
    try:
        if sym=="XAUUSD":
            r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        if sym in COINS_DUAL:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",timeout=8, headers={"User-Agent":"Mozilla/5.0"}).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        for url in [f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT", f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT"]:
            try:
                rr=requests.get(url,timeout=4).json()
                if 'price' in rr and float(rr['price'])>0: return float(rr['price'])
            except: pass
    except: pass
    return 0

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
        if sym in COINS_DUAL+["XAUUSD"]:
            try:
                ysym="GC=F" if sym=="XAUUSD" else sym
                r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=1d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
                closes=[c for c in r['chart']['result'][0]['indicators']['quote'][0]['close'] if c]
                ema=sum(closes[-20:])/20 if len(closes)>=20 else price
            except: ema=price
            return 29.0 if sym!="BTC" else 50, price, ema, 0
        kl=get_klines_robust(sym)
        if not kl: return 50, price, price*0.998, 0
        closes=[float(k[4]) for k in kl]
        ema=sum(closes[-20:])/20
        gains=[max(0, closes[i]-closes[i-1]) for i in range(1,len(closes))]
        losses=[max(0, closes[i-1]-closes[i]) for i in range(1,len(closes))]
        rg=sum(gains[-14:])/14 or 0.01
        rl=sum(losses[-14:])/14 or 0.01
        rsi=100-(100/(1+rg/rl))
        return rsi, price, ema, 0
    except: return 50,0,0,0

def totals():
    flot=0
    for p in data['pos']:
        pr=P(p["sym"])
        if pr==0: pr=p["precio_entry"]
        p["gan"]=(pr-p["precio_entry"])/p["precio_entry"]*p["monto"]
        flot+=p["gan"]
    return data['b']+sum([p['monto'] for p in data['pos']])+flot, flot

def kb():
    m=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=4)
    m.add("XAUUSD","BTC","NVDA","TSLA","DASHBOARD","BALANCE","AUTO ON","AUTO OFF")
    return m

def get_first_candle_ny(sym):
    try:
        if sym=="BTC": return None
        ysym="GC=F" if sym=="XAUUSD" else sym
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=2d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
        res=r['chart']['result'][0]
        stamps=res['timestamp']; highs=res['indicators']['quote'][0]['high']; lows=res['indicators']['quote'][0]['low']
        for i, ts in enumerate(stamps):
            dt=datetime.fromtimestamp(ts, ZoneInfo('America/New_York'))
            if dt.hour==9 and dt.minute==30 and dt.date()==datetime.now(ZoneInfo('America/New_York')).date():
                if highs[i] and lows[i]: return {"high": highs[i], "low": lows[i]}
    except: pass
    return None

def detectar_liquidez(sym):
    try:
        ysym="GC=F" if sym=="XAUUSD" else sym
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=5d&interval=15m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
        res=r['chart']['result'][0]
        closes=res['indicators']['quote'][0]['close']; lows=res['indicators']['quote'][0]['low']; highs=res['indicators']['quote'][0]['high']
        if len(closes)<50: return None
        for i in range(len(lows)-20, len(lows)-5):
            if lows[i] is None: continue
            similares = [j for j in range(i-10, i+5) if j>=0 and j<len(lows) and lows[j] and abs(lows[j]-lows[i])/lows[i]<0.003]
            if len(similares)>=3:
                for k in range(i+1, len(closes)-1):
                    if closes[k] and closes[k-1] and closes[k] < lows[i] and closes[k] < closes[k-1]*0.998:
                        ob_high = highs[k-1] if highs[k-1] else closes[k-1]
                        ob_low = lows[k-1] if lows[k-1] else closes[k-1]*0.99
                        return {"liquidez_en": lows[i], "quiebre_en": closes[k], "orderblock": (ob_low+ob_high)/2}
    except: pass
    return None

@app.route("/")
def home():
    tot, flot = totals()
    html = f"<html><head><meta name='viewport' content='width=device-width'><meta http-equiv='refresh' content='15'><style>body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}.top{{border:2px solid #ffcc00;border-radius:15px;padding:12px;background:#1a1500}}.card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:5px solid #555}}.vivo{{border-left-color:#00ff88;background:#0f1f15}}.e1{{border-left-color:#a855f7;background:#1a102a}}.e2{{border-left-color:#ff3b3b;background:#2a1010}}.graf{{background:#ffcc00;color:#000;width:100%;padding:10px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}.live{{background:#00ff88;color:#000;padding:2px 8px;border-radius:6px;font-size:11px}}</style></head><body><div class='top'><b>🔥 V34 CONCENTRADO 60/30/10 🔥</b><br>Total ${tot:.2f} | Flot {flot:+.2f}$<br>Saldo ${data['b']:.2f} | {len(data['pos'])}/6<br><small>XAU $3000 | NVDA/TSLA $1500 | BTC $500</small></div>"
    if data['pos']:
        html+=f"<h3>🎯 EN ENTRADA - {len(data['pos'])}:</h3>"
        for p in data['pos']:
            price=P(p['sym']); sl,tp1,tp2=get_levels(p['sym'],p['precio_entry'])
            tipo="E1" if p.get('es_dual')==1 else "E2" if p.get('es_dual')==2 else "PRO"
            clase="e1" if p.get('es_dual')==1 else "e2" if p.get('es_dual')==2 else "vivo"
            html+=f"<div class='card {clase}'><b>🎯 {p['sym']} {tipo} ${p['monto']} <span class='live'>EN ENTRADA</span></b><br>Ent ${p['precio_entry']:.2f} → ${price:.2f} = ${p.get('gan',0):+.2f}<br>SL ${sl:.2f} TP1 ${tp1:.2f} TP2 ${tp2:.2f}<br><a class='graf' href='/chart/{p['sym']}'>📈 VER LINEAS</a></div>"
    html+="<h3>👀 CAZANDO:</h3>"
    for sym in ALL_COINS:
        rsi,price,_,_=AN(sym)
        html+=f"<div class='card' style='border-left-color:#333'><b>{sym} ${price:.2f}</b> RSI {rsi:.1f} <a class='graf' href='/chart/{sym}'>GRAFICA</a></div>"
    return html+"</body></html>"

@app.route("/api/klines/<sym>")
def api_klines(sym):
    try:
        if sym in ["NVDA","TSLA","XAUUSD"]:
            ysym="GC=F" if sym=="XAUUSD" else sym
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=2d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
            res=r['chart']['result'][0]
            closes=res['indicators']['quote'][0]['close']; opens=res['indicators']['quote'][0]['open']; highs=res['indicators']['quote'][0]['high']; lows=res['indicators']['quote'][0]['low']; stamps=res['timestamp']
            return [{"time":stamps[i],"open":opens[i],"high":highs[i],"low":lows[i],"close":closes[i]} for i in range(len(stamps)) if closes[i] is not None][-200:]
        kl=get_klines_robust(sym)
        return [{"time":int(k[0]/1000),"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4])} for k in kl]
    except: return []

@app.route("/api/price/<sym>")
def api_price(sym): return {"price": P(sym)}

@app.route("/chart/<sym>")
def chart(sym):
    price=P(sym); rsi,_,ema,_=AN(sym)
    pos=next((p for p in data['pos'] if p['sym']==sym), None)
    entry=pos['precio_entry'] if pos else price
    sl,tp1,tp2=get_levels(sym,entry) if pos else (0,0,0)
    fc=get_first_candle_ny(sym)
    fc_h=fc['high'] if fc else 0; fc_l=fc['low'] if fc else 0
    es_stock=sym in COINS_DUAL+["XAUUSD"]
    extra=f"<span style='color:#a855f7'>HIGH 9:30 ${fc_h:.2f}</span> | <span style='color:#00aaff'>LOW ${fc_l:.2f}</span>" if es_stock and fc else f"EMA ${ema:.2f}" if ema else ""
    return f"""<html><head><meta name="viewport" content="width=device-width"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script><style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}a{{color:#ffcc00}}#chart{{width:100%;height:78vh}}.info{{padding:8px;font-size:12px;background:#111}}</style></head><body><div class="info"><a href="/">ATRAS</a> <b>{sym} ${price:.2f} RSI {rsi:.1f}</b><br>{f'Ent <span style="color:#00ff88">${entry:.2f}</span> TP1 ${tp1:.2f} TP2 ${tp2:.2f} SL <span style="color:#ff3b3b">${sl:.2f}</span><br>' if pos else ''}{extra}</div><div id="chart"></div><script>const ENTRY={entry if pos else 0},TP1={tp1 if pos else 0},TP2={tp2 if pos else 0},SL={sl if pos else 0},FC_H={fc_h},FC_L={fc_l},ES={str(es_stock).lower()},SYM="{sym}";async function load(){{const res=await fetch("/api/klines/"+SYM);const data=await res.json();const chart=LightweightCharts.createChart(document.getElementById("chart"),{{layout:{{background:{{color:"#000"}},textColor:"#fff"}},grid:{{vertLines:{{color:"#1a1a1a"}},horzLines:{{color:"#1a1a1a"}}}}}});const candle=chart.addCandlestickSeries();candle.setData(data);if(ENTRY>0){{candle.createPriceLine({{price:ENTRY,color:"#00ff88",lineWidth:2,title:"ENTRADA"}});candle.createPriceLine({{price:TP1,color:"#ffcc00",lineWidth:2,lineStyle:2,title:"TP1"}});candle.createPriceLine({{price:TP2,color:"#00ff88",lineWidth:1,lineStyle:2,title:"TP2"}});candle.createPriceLine({{price:SL,color:"#ff3b3b",lineWidth:2,lineStyle:2,title:"SL"}});}}if(ES && FC_H>0){{candle.createPriceLine({{price:FC_H,color:"#a855f7",lineWidth:2,title:"HIGH 9:30"}});candle.createPriceLine({{price:FC_L,color:"#00aaff",lineWidth:2,title:"LOW 9:30"}});}}chart.timeScale().fitContent();setInterval(async()=>{{const r=await fetch("/api/price/"+SYM);const j=await r.json();if(j.price>0){{const last=data[data.length-1];last.close=j.price;candle.update(last);}}}},3000);}}load();</script></body></html>"""

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
        if m.chat.id not in data["alert_users"]: data["alert_users"].append(m.chat.id); save()
        if txt in ["/START","START","BALANCE","B"]:
            tot,flot=totals()
            msg=f"V34 CONCENTRADO\nTotal ${tot:.2f} Flot {flot:+.2f}$ Saldo ${data['b']:.2f}\n"
            for p in data['pos']: msg+=f"{p['sym']} ${p['monto']} Ent ${p['precio_entry']:.2f}\n"
            tg(m.chat.id, msg, kb()); return
        tg(m.chat.id, f"V34 CONCENTRADO\n{DASH_URL}", kb())
    except: pass

def auto_loop():
    while True:
        try:
            now=datetime.now(ZoneInfo('America/Mexico_City'))
            ny_now=datetime.now(ZoneInfo('America/New_York'))
            # E1 AUTO NVDA/TSLA $750
            try:
                if ny_now.weekday()<5 and 9<=ny_now.hour<=10 and data.get('auto_buy'):
                    for sym in COINS_DUAL:
                        fc=get_first_candle_ny(sym)
                        if not fc: continue
                        price=P(sym)
                        if price==0 or any(p.get('es_dual')==1 and p['sym']==sym for p in data['pos']): continue
                        if price > fc['high']*1.0015 or price < fc['low']*0.9985:
                            if data['b']>=MONTO_E1 and len(data['pos'])<MAX_POS:
                                data['pos'].append({"sym":sym,"monto":MONTO_E1,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False,"es_dual":1})
                                data['b']-=MONTO_E1; save()
                                for u in data["alert_users"]: tg(u,f"🔥 E1 AUTO {sym} ${price:.2f} $750")
            except: pass
            # E2 AUTO
            try:
                if ny_now.weekday()<5 and data.get('auto_buy'):
                    for sym in ["NVDA","TSLA","XAUUSD"]:
                        if any(p.get('es_dual')==2 and p['sym']==sym for p in data['pos']): continue
                        liq=detectar_liquidez(sym)
                        if liq:
                            price=P(sym)
                            monto=MONTO_E2_XAU if sym=="XAUUSD" else MONTO_E2_STOCK
                            if price and data['b']>=monto and len(data['pos'])<MAX_POS:
                                data['pos'].append({"sym":sym,"monto":monto,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False,"es_dual":2})
                                data['b']-=monto; save()
                                for u in data["alert_users"]: tg(u,f"💧 E2 AUTO {sym} ${price:.2f} ${monto} Triple ${liq['liquidez_en']:.2f}")
            except: pass
            # PRO XAU $1500 + BTC $500
            for sym in COINS_PRO[:]:
                try:
                    if sym in COINS_DUAL and not (8 <= now.hour <= 15): continue
                    rsi,price,ema20,_=AN(sym)
                    if price==0: continue
                    for p in data["pos"][:]:
                        if p["sym"]!=sym: continue
                        p["max_price"]=max(p.get("max_price",0), price)
                        p["gan"]=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                        sl,tp1,tp2=get_levels(p["sym"], p["precio_entry"])
                        if price <= sl or price >= tp2:
                            profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                            data["b"]+=p["monto"]+profit; data["gan_total"]+=profit; data["pos"].remove(p); save()
                            for u in data["alert_users"]: tg(u,f"{'🛑 STOP' if price<=sl else '✅ TP2'} {sym} ${price:.2f} ${profit:+.2f}")
                            continue
                        if not p.get("tp1_done") and price >= tp1:
                            if p["monto"]<600:
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]
                                data["b"]+=p["monto"]+profit; data["pos"].remove(p)
                            else:
                                profit_half=(price-p["precio_entry"])/p["precio_entry"]*(p["monto"]/2)
                                data["b"]+=p["monto"]/2 + profit_half; p["monto"]=p["monto"]/2; p["tp1_done"]=True
                            save()
                            for u in data["alert_users"]: tg(u,f"💰 TP1 {sym} ${price:.2f}")
                    monto_pro=MONTO_PRO_XAU if sym=="XAUUSD" else MONTO_PRO_BTC
                    if rsi<32 and price>ema20*0.995 and data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(pp['sym']==sym and not pp.get('es_dual') for pp in data["pos"]):
                        if data["b"]>=monto_pro:
                            data["pos"].append({"sym":sym,"monto":monto_pro,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False})
                            data["b"]-=monto_pro; save()
                            for u in data["alert_users"]: tg(u,f"🎯 PRO {sym} ${price:.2f} ${monto_pro} RSI {rsi:.1f}")
                except: continue
                time.sleep(1)
            time.sleep(30)
        except Exception as e:
            print(f"Loop err {e}"); time.sleep(30)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
