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
LIQUIDEZ_DATA = {}

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
            return (float(kl[-1][4])-float(kl[-2][4]))/float(kl[-2][4])*100
    except: return 0
    return 0

def totals():
    flot=0
    for p in data['pos']:
        pr=P(p["sym"])
        if pr==0: pr=p["precio_entry"]
        p["gan"]=(pr-p["precio_entry"])/p["precio_entry"]*p["monto"]
        flot+=p["gan"]
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
        stamps=res['timestamp']; highs=res['indicators']['quote'][0]['high']; lows=res['indicators']['quote'][0]['low']
        for i, ts in enumerate(stamps):
            dt=datetime.fromtimestamp(ts, ZoneInfo('America/New_York'))
            if dt.hour==9 and dt.minute==30 and dt.date()==datetime.now(ZoneInfo('America/New_York')).date():
                if highs[i] and lows[i]: return {"high": highs[i], "low": lows[i]}
    except: pass
    return None

def detectar_liquidez(sym):
    try:
        if sym in COINS_CRIPTO: return None
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
    btc1h = get_btc_1h()
    pos_normal = [p for p in data['pos'] if not p.get('es_dual')]
    pos_e1 = [p for p in data['pos'] if p.get('es_dual')==1]
    pos_e2 = [p for p in data['pos'] if p.get('es_dual')==2]

    html_head = """
    <html><head><meta name='viewport' content='width=device-width'><meta http-equiv='refresh' content='15'>
    <style>
    body{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}
   .top{border:2px solid #ffcc00;border-radius:15px;padding:12px;background:#1a1500;margin-bottom:10px}
   .card{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:5px solid #555}
   .vivo{border-left-color:#00ff88;background:#0f1f15}
   .e1{border-left-color:#a855f7;background:#1a102a}
   .e2{border-left-color:#ff3b3b;background:#2a1010}
   .cazando{border-left-color:#333}
   .desglose{background:#222;border:1px solid #ffcc00;border-radius:12px;padding:12px;margin:10px 0}
   .graf{background:#ffcc00;color:#000;width:100%;padding:10px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}
   .live{background:#00ff88;color:#000;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:bold}
   .dualbtn{background:linear-gradient(90deg,#a855f7,#ffcc00);color:#000;padding:12px;border-radius:10px;display:block;text-align:center;text-decoration:none;font-weight:bold;margin:10px 0}
    </style></head><body>
    """
    html = html_head
    html += f"<div class='top'><b>🔥 V32.4 PRESAS CLARAS 🔥</b><br>Total ${tot:.2f} | Flot {flot:+.2f}$ | BTC 1h {btc1h:+.2f}%<br>Saldo ${data['b']:.2f} | Hoy ${data['gan_hoy']:.2f} | {len(data['pos'])}/10</div>"
    html += f"<div class='desglose'><b>💰 $5000 MXN:</b> PRO ${sum([p['monto'] for p in pos_normal]):.2f} ({len(pos_normal)}) | E1 ${sum([p['monto'] for p in pos_e1]):.2f} ({len(pos_e1)}) | E2 ${sum([p['monto'] for p in pos_e2]):.2f} ({len(pos_e2)}) | Libre ${data['b']:.2f}</div>"
    html += f"<a class='dualbtn' href='/dual/NVDA'>🔥 DUAL NVDA $3500</a>"

    if data['pos']:
        html += f"<h3>🎯 EN ENTRADA AHORA - {len(data['pos'])} PRESAS:</h3>"
        for p in data['pos']:
            price = P(p['sym'])
            if price==0: price=p['precio_entry']
            gan_pct = (price-p['precio_entry'])/p['precio_entry']*100
            gan_usd = p.get('gan',0)
            tipo = "E1 AUTO $1750" if p.get('es_dual')==1 else "E2 LIQ $1750" if p.get('es_dual')==2 else "PRO RSI $500"
            clase = "e1" if p.get('es_dual')==1 else "e2" if p.get('es_dual')==2 else "vivo"
            html += f"<div class='card {clase}'><b>🎯 {p['sym']} - {tipo} <span class='live'>EN ENTRADA</span></b><br>Entrada ${p['precio_entry']:.4f} → Ahora ${price:.4f}<br>Result: {gan_pct:+.2f}% = ${gan_usd:+.2f} | Invertido ${p['monto']}<br><a class='graf' href='/chart/{p['sym']}'>📈 VER GRAFICA VIVA</a></div>"
    else:
        html += "<div class='card'><b>Sin entradas ahora - cazando...</b></div>"

    html += "<h3>👀 CAZANDO (sin entrada):</h3>"
    for sym in ALL_COINS:
        if any(pp['sym']==sym for pp in data['pos']): continue
        rsi,price,ema,_=AN(sym)
        html += f"<div class='card cazando'><b>{sym} ${price:.4f}</b> RSI {rsi:.1f} | EMA ${ema:.2f}<br><a class='graf' href='/chart/{sym}'>VER GRAFICA</a></div>"

    html += "</body></html>"
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
        return [{"time":int(k[0]/1000),"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4])} for k in kl]
    except: return []

@app.route("/api/price/<sym>")
def api_price(sym):
    try: return {"price": P(sym), "time": int(time.time())}
    except: return {"price": 0, "time": int(time.time())}

@app.route("/chart/<sym>")
def chart(sym):
    price = P(sym)
    rsi,_,_,_ = AN(sym)
    page = """
    <html><head><meta name="viewport" content="width=device-width">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>body{margin:0;background:#000;color:#fff} a{color:#ffcc00} #chart{width:100%;height:85vh}</style>
    </head><body>
    <div style="padding:10px"><a href="/">ATRAS</a> SYM_TXT PRICE_TXT RSI_TXT</div>
    <div id="chart"></div>
    <script>
    const SYM="SYM_TXT";
    async function load(){
      const res=await fetch("/api/klines/"+SYM);
      const data=await res.json();
      const chart=LightweightCharts.createChart(document.getElementById("chart"),{layout:{background:{color:"#000"},textColor:"#fff"},grid:{vertLines:{color:"#222"},horzLines:{color:"#222"}}});
      const candle=chart.addCandlestickSeries(); candle.setData(data); chart.timeScale().fitContent();
      setInterval(async()=>{const r=await fetch("/api/price/"+SYM); const j=await r.json(); if(j.price>0){const last=data[data.length-1]; last.close=j.price; candle.update(last);}},3000);
    } load();
    </script></body></html>
    """
    page = page.replace("SYM_TXT", sym).replace("PRICE_TXT", f"${price:.4f}").replace("RSI_TXT", f"RSI {rsi:.1f}")
    return page

@app.route("/dual/<sym>")
def dual_page(sym):
    sym=sym.upper()
    fc=get_first_candle_ny(sym)
    liq=detectar_liquidez(sym)
    pos_e1 = [p for p in data['pos'] if p.get('es_dual')==1 and p['sym']==sym]
    pos_e2 = [p for p in data['pos'] if p.get('es_dual')==2 and p['sym']==sym]
    fc_txt = f"HIGH ${fc['high']:.2f} LOW ${fc['low']:.2f}" if fc else "Esperando 7:30 AM NY"
    liq_txt = f"Triple ${liq['liquidez_en']:.2f} OB ${liq['orderblock']:.2f}" if liq else "Escaneando liquidez..."
    return f"<html><head><meta name='viewport' content='width=device-width'><style>body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}.card{{background:#1a1a1a;padding:14px;border-radius:15px;margin:10px 0;border-left:4px solid #00ff88}}</style></head><body><a href='/' style='color:#ffcc00'>ATRAS</a><h2>DUAL {sym} $3500</h2><div style='background:#222;border:1px solid #ffcc00;border-radius:10px;padding:10px'>PRO {len([p for p in data['pos'] if not p.get('es_dual')])} + E1 {len(pos_e1)} + E2 {len(pos_e2)} + Saldo ${data['b']:.2f}</div><div class='card'><b>E1 AUTO $1750</b><br>{fc_txt}</div><div class='card'><b>E2 CONFIRMA $1750</b><br>{liq_txt} -> SI {sym}</div><iframe src='/chart/{sym}' style='width:100%;height:60vh;border:none;border-radius:10px'></iframe></body></html>"

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
            data["alert_users"].append(m.chat.id); save()
        if txt.startswith("SI "):
            sym = txt.split(" ")[1]
            if sym in ALL_COINS and data['b']>=MONTO_E2 and len(data['pos'])<MAX_POS:
                price=P(sym)
                if price>0:
                    data['pos'].append({"sym":sym,"monto":MONTO_E2,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False,"es_dual":2,"tipo":"LIQUIDEZ"})
                    data['b']-=MONTO_E2; save()
                    tg(m.chat.id, f"✅ E2 CONFIRMADO {sym} ${price:.4f} $1750", kb())
                    return
        if txt in ["/START","START","BALANCE","/BALANCE","B","/B"]:
            tot,flot=totals()
            pos_normal = [p for p in data['pos'] if not p.get('es_dual')]
            pos_e1 = [p for p in data['pos'] if p.get('es_dual')==1]
            pos_e2 = [p for p in data['pos'] if p.get('es_dual')==2]
            detalle=""
            for p in data['pos']:
                price=P(p['sym']); gan=(price-p['precio_entry'])/p['precio_entry']*100 if price else 0
                tipo="E1" if p.get('es_dual')==1 else "E2" if p.get('es_dual')==2 else "PRO"
                detalle+=f"\n- {p['sym']} {tipo} {gan:+.1f}% ${p['monto']}"
            msg = f"V32.4 CLARO\nTotal: ${tot:.2f} Flot {flot:+.2f}$\nSaldo Libre: ${data['b']:.2f}\n\nEN ENTRADA:{detalle if detalle else ' Ninguna'}\n\nDESGLOSE: PRO ${sum([p['monto'] for p in pos_normal]):.2f} E1 ${sum([p['monto'] for p in pos_e1]):.2f} E2 ${sum([p['monto'] for p in pos_e2]):.2f}"
            tg(m.chat.id, msg, kb())
            return
        if txt=="DASHBOARD": tg(m.chat.id, f"DASHBOARD\n{DASH_URL}", kb()); return
        if txt=="DUAL": tg(m.chat.id, f"DUAL $3500\n{DASH_URL}/dual/NVDA", kb()); return
        if txt=="AUTO ON": data['auto_buy']=True; save(); tg(m.chat.id, "AUTO ON + ALARMA 7:30", kb()); return
        if txt=="AUTO OFF": data['auto_buy']=False; save(); tg(m.chat.id, "PAUSA", kb()); return
        if txt in ALL_COINS: rsi,price,_,_=AN(txt); tg(m.chat.id, f"{txt} ${price:.4f} RSI {rsi:.1f}", kb()); return
        tg(m.chat.id, f"V32.4\n{DASH_URL}", kb())
    except Exception as e: print(f"Error {e}")

def auto_loop():
    while True:
        try:
            now=datetime.now(ZoneInfo('America/Mexico_City'))
            ny_now = datetime.now(ZoneInfo('America/New_York'))
            try:
                if ny_now.weekday()<5 and now.hour==7 and now.minute==30 and now.second<15:
                    if data.get("last_apertura")!= now.strftime("%Y-%m-%d"):
                        for u in data["alert_users"]:
                            tg(u, f"APERTURA NY EN 5 MIN\nV32.4 LISTO\nE1 $1750 7:35-9:00\nE2 $1750 esperando\n{DASH_URL}", kb())
                        data["last_apertura"]=now.strftime("%Y-%m-%d"); save()
            except: pass
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
                                for u in data["alert_users"]: tg(u,f"E1 AUTO {sym} ${price:.4f} $1750")
                if ny_now.weekday()<5 and data.get('auto_buy'):
                    for sym in ["NVDA","TSLA"]:
                        liq=detectar_liquidez(sym)
                        if liq and sym not in LIQUIDEZ_DATA:
                            LIQUIDEZ_DATA[sym]=liq
                            for u in data["alert_users"]: tg(u,f"E2 LIQ {sym} Triple ${liq['liquidez_en']:.2f} OB ${liq['orderblock']:.2f} -> SI {sym}")
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
                            for u in data["alert_users"]: tg(u,f"STOP {sym} {gan_pct:.2f}%")
                            continue
                        if not p.get("tp1_done") and gan_pct >= TP1_PCT:
                            if p["monto"]>=400:
                                profit_half=(price-p["precio_entry"])/p["precio_entry"]*(p["monto"]/2)
                                data["b"]+=p["monto"]/2 + profit_half; data["gan_total"]+=profit_half; data["gan_hoy"]+=profit_half; p["monto"]=p["monto"]/2; p["tp1_done"]=True; save()
                                for u in data["alert_users"]: tg(u,f"TP1 {sym} +{gan_pct:.2f}%")
                            else:
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]; data["b"]+=p["monto"]+profit; data["gan_total"]+=profit; data["gan_hoy"]+=profit; data["pos"].remove(p); save()
                                for u in data["alert_users"]: tg(u,f"TP1 {sym} +{gan_pct:.2f}%")
                            continue
                        if p.get("tp1_done"):
                            if gan_pct >= TP2_PCT or (p["max_price"]>p["precio_entry"]*1.02 and price < p["max_price"]*(1-TRAILING_PCT/100)):
                                profit=(price-p["precio_entry"])/p["precio_entry"]*p["monto"]; data["b"]+=p["monto"]+profit; data["gan_total"]+=profit; data["gan_hoy"]+=profit; data["pos"].remove(p); save()
                                for u in data["alert_users"]: tg(u,f"TP2 {sym} +{gan_pct:.2f}%")
                    if btc_1h < BTC_CRASH_PCT: continue
                    if rsi<32 and price>ema20*0.995 and btc_t>-1.5:
                        if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(pp['sym']==sym for pp in data["pos"] if not pp.get('es_dual')):
                            if data["b"]<MONTO_TRADE: continue
                            data["pos"].append({"sym":sym,"monto":MONTO_TRADE,"gan":0,"precio_entry":price,"max_price":price,"tp1_done":False})
                            data["b"]-=MONTO_TRADE; data["trades_hoy"]+=1; save()
                            for u in data["alert_users"]: tg(u,f"CASERIA {sym} ${price:.4f} RSI {rsi:.1f}")
                except: continue
                time.sleep(1.5)
            time.sleep(40)
        except Exception as e:
            print(f"Loop err {e}"); time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
