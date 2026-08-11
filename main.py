import os, json, time, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    print("FALTA BOT_TOKEN")
    TOKEN = "123456:TEST"

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

COINS_CRIPTO = ["ADA","AVAX","BTC","DOGE","ETH","LINK","SOL","XRP"]
COINS_STOCKS = ["NVDA","TSLA"]
COINS_GOLD = ["XAUUSD"]
ALL_COINS = COINS_CRIPTO + COINS_STOCKS + COINS_GOLD
MAX_POS = 10
MONTO_TRADE = 500
SALDO_INICIAL = 5000
DASH_URL = "https://telegram-bot-cijp.onrender.com"

try:
    with open("data.json","r") as f: data=json.load(f)
    if data.get("b",0) < 1000 and len(data.get("pos",[]))==0:
        data["b"]=SALDO_INICIAL
except:
    data={"b":SALDO_INICIAL,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[],"last_report_date":""}
data["coins"]=ALL_COINS

def save():
    try:
        with open("data.json","w") as f: json.dump(data,f)
    except: pass

def tg(chat,txt,markup=None):
    try: bot.send_message(chat,txt,reply_markup=markup, disable_web_page_preview=True)
    except Exception as e: print(f"TG Error {e}")

# --- NUEVO SISTEMA ANTI-BLOQUEO ---
def get_price_robust(sym):
    # 1. Intenta Binance.com
    try:
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT",timeout=4).json()
        if 'price' in r and float(r['price'])>0: return float(r['price'])
    except: pass
    # 2. Intenta Binance.vision (no bloquea USA)
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT",timeout=4).json()
        if 'price' in r and float(r['price'])>0: return float(r['price'])
    except: pass
    # 3. Intenta Yahoo como respaldo para cripto
    try:
        mp={"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XRP":"XRP-USD","DOGE":"DOGE-USD","AVAX":"AVAX-USD","LINK":"LINK-USD","ADA":"ADA-USD"}
        ysym=mp.get(sym)
        if ysym:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}",timeout=5, headers={"User-Agent":"Mozilla/5.0"}).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
    except Exception as e: print(f"Yahoo fail {sym}: {e}")
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
    for url in [f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=5m&limit=50",
                f"https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=5m&limit=50"]:
        try:
            kl=requests.get(url,timeout=6).json()
            if isinstance(kl,list) and len(kl)>=20: return kl
        except: pass
    return []

def AN(sym):
    try:
        price = P(sym)
        if price==0: return 50,0,0,0
        if sym in COINS_STOCKS+COINS_GOLD:
            # Calcula EMA real de Yahoo
            try:
                ysym="GC=F" if sym=="XAUUSD" else sym
                r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?range=1d&interval=5m",timeout=6, headers={"User-Agent":"Mozilla/5.0"}).json()
                closes=r['chart']['result'][0]['indicators']['quote'][0]['close']
                closes=[c for c in closes if c]
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
            btc_change = float(btc.get('priceChangePercent', 0))
        except: btc_change=0
        return rsi, price, ema, btc_change
    except Exception as e:
        print(f"AN error {sym}: {e}")
        return 50,0,0,0

def totals():
    t=data['b']+sum([p['monto']+p.get('gan',0) for p in data['pos']])
    return t,t

def kb():
    m=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=4)
    m.add("BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA","NVDA","TSLA","XAUUSD","DASHBOARD","AUTO ON","AUTO OFF")
    return m

@app.route("/")
def home():
    tt, _ = totals()
    html=f"""<html><head><meta name='viewport' content='width=device-width'><style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
  .card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:4px solid #00ff88}}
  .top{{border:1.5px solid #00ff88;border-radius:15px;padding:12px;display:flex;justify-content:space-between;align-items:center}}
  .btn{{background:#00ff88;color:#000;padding:8px 15px;border-radius:20px;font-weight:bold}}
  .graf{{background:#00ff88;color:#000;width:100%;padding:12px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}
    </style></head><body>
    <div class='top'><div><b>V29.5 ANTI-BLOQUEO $5K</b><br>Binance Vision Fix</div><div><span class='btn'>{'AUTO ON' if data['auto_buy'] else 'AUTO OFF'}</span> <span style='background:#ffcc00;color:#000;padding:8px 12px;border-radius:10px;font-weight:bold'>${tt:.0f}</span></div></div>
    <div style='display:flex;justify-content:space-between;margin:12px 0'><span>Saldo ${data['b']:.0f}</span><span>Total ${tt:.0f}</span><span>Hoy ${data['gan_hoy']:.2f}</span></div>"""
    for sym in ALL_COINS:
        rsi,price,ema20,btc_t = AN(sym)
        color="#00ff88" if rsi<32 else "#fff"
        html+=f"<div class='card'><b>{sym} ${price:.4f}</b><br><span style='color:{color}'>RSI {rsi:.1f}</span> | EMA ${ema20:.2f} | BTC {btc_t:.2f}%<br><a class='graf' href='/chart/{sym}'>📈 VER GRAFICA {sym}</a></div>"
    html+=f"<div class='card'>Pos abiertas: {len(data['pos'])}/{MAX_POS} | Monto x Pos: ${MONTO_TRADE}</div></body></html>"
    return html

@app.route("/chart/<sym>")
def chart(sym):
    tv_map = {"XAUUSD":"OANDA:XAUUSD","NVDA":"NASDAQ:NVDA","TSLA":"NASDAQ:TSLA","BTC":"BINANCE:BTCUSDT","ETH":"BINANCE:ETHUSDT","SOL":"BINANCE:SOLUSDT","XRP":"BINANCE:XRPUSDT","DOGE":"BINANCE:DOGEUSDT","AVAX":"BINANCE:AVAXUSDT","LINK":"BINANCE:LINKUSDT","ADA":"BINANCE:ADAUSDT"}
    tv = tv_map.get(sym, f"BINANCE:{sym}USDT")
    p = P(sym)
    rsi,_,ema,_ = AN(sym)
    return f'<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}.header{{padding:12px;background:#111;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}} a{{color:#00ff88;text-decoration:none;font-weight:bold}} #tv{{height:90vh;width:100%}}</style></head><body><div class="header"><a href="/">← Volver V29.5</a><span><b>{sym} ${p:.2f} RSI {rsi:.1f}</b> EMA {ema:.2f}</span></div><div id="tradingview_chart"></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({{"autosize": true,"symbol": "{tv}","interval": "5","timezone": "America/Mexico_City","theme": "dark","style": "1","locale": "es","enable_publishing": false,"allow_symbol_change": true,"container_id": "tradingview_chart"}});</script></body></html>'

@app.route("/webhook", methods=['POST'])
def webhook():
    if request.data:
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
    return "ok", 200

@app.route("/setwebhook")
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{DASH_URL}/webhook")
    return f"webhook set a {DASH_URL}/webhook - OK"

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    txt = m.text.upper().strip() if m.text else ""
    if m.chat.id not in data["alert_users"]:
        data["alert_users"].append(m.chat.id); save()
    if txt in ["/START","START","/BALANCE","/B","BALANCE","B"]:
        t,_=totals()
        tg(m.chat.id, f"V29.5 ANTI-BLOQUEO LIVE ✅\nTotal: ${t:.2f}\nSaldo: ${data['b']:.2f}\nPos: {len(data['pos'])}/{MAX_POS} x ${MONTO_TRADE}\nAuto: {'ON' if data['auto_buy'] else 'OFF'}\nDashboard: {DASH_URL}", kb())
        return
    if txt=="DASHBOARD":
        tg(m.chat.id, f"📊 {DASH_URL}", kb()); return
    if txt=="AUTO ON": data['auto_buy']=True; save(); tg(m.chat.id, "✅ AUTO ON", kb()); return
    if txt=="AUTO OFF": data['auto_buy']=False; save(); tg(m.chat.id, "⏸️ AUTO OFF", kb()); return
    if txt in ALL_COINS:
        rsi,price,ema,btc_t = AN(txt)
        tg(m.chat.id, f"{txt} RSI {rsi:.1f} ${price:.4f}\nEMA ${ema:.2f} BTC {btc_t:.2f}%\nGrafica: {DASH_URL}/chart/{txt}", kb())
        return

def auto_loop():
    while True:
        try:
            for sym in data["coins"]:
                try:
                    if sym in COINS_STOCKS:
                        h=datetime.now(ZoneInfo('America/Mexico_City')).hour
                        if not (8 <= h <= 15): continue
                    rsi,price,ema20,btc_t=AN(sym)
                    if price==0: continue
                    if rsi<32 and price>ema20*0.995 and btc_t>-1.5:
                        if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(p['sym']==sym for p in data["pos"]):
                            if data["b"] < MONTO_TRADE: continue
                            data["pos"].append({"sym":sym,"monto":MONTO_TRADE,"gan":0,"precio_entry":price,"max_price":price})
                            data["b"]-=MONTO_TRADE; data["trades_hoy"]+=1; save()
                            for u in data["alert_users"]:
                                tg(u,f"🔥 V29.5 COMPRA {sym} ${price:.4f} RSI {rsi:.1f} x ${MONTO_TRADE}\nGrafica: {DASH_URL}/chart/{sym}")
                except Exception as e_inner: print(f"Error en {sym}: {e_inner}"); continue
                time.sleep(2)
            time.sleep(90)
        except Exception as e:
            print(f"Error loop: {e}"); time.sleep(60); continue

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
