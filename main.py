import os, json, time, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = "AQUI_TU_TOKEN_SI_NO_USAS_ENV"
    print("FALTA BOT_TOKEN")

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

COINS_CRIPTO = ["ADA","AVAX","BTC","DOGE","ETH","LINK","SOL","XRP"]
COINS_STOCKS = ["NVDA","TSLA"]
COINS_GOLD = ["XAUUSD"]
ALL_COINS = COINS_CRIPTO + COINS_STOCKS + COINS_GOLD
MAX_POS = 8
DASH_URL = "https://telegram-bot-cijp.onrender.com"

try:
    with open("data.json","r") as f: data=json.load(f)
except:
    data={"b":4950,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[5471234634],"last_report_date":""}

data["coins"]=ALL_COINS

def save():
    try:
        with open("data.json","w") as f: json.dump(data,f)
    except: pass

def tg(chat,txt,markup=None):
    try: bot.send_message(chat,txt,reply_markup=markup, disable_web_page_preview=True)
    except Exception as e: print(e)

def P(sym):
    try:
        if sym=="XAUUSD":
            r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",timeout=5).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        if sym in COINS_STOCKS:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",timeout=5).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT",timeout=5).json()
        return float(r['price'])
    except: return 0

def AN(sym):
    try:
        price = P(sym)
        if sym in COINS_STOCKS+COINS_GOLD:
            return 29.0, price, price*0.998, 0
        kl=requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=5m&limit=50",timeout=8).json()
        closes=[float(k[4]) for k in kl]
        ema=sum(closes[-20:])/20
        gains=[max(0, closes[i]-closes[i-1]) for i in range(1,len(closes))]
        losses=[max(0, closes[i-1]-closes[i]) for i in range(1,len(closes))]
        rg=sum(gains[-14:])/14 or 0.01
        rl=sum(losses[-14:])/14 or 0.01
        rsi=100-(100/(1+rg/rl))
        btc=requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",timeout=5).json()
        return rsi, price, ema, float(btc['priceChangePercent'])
    except: return 50,0,0,0

def totals():
    t=data['b']+sum([p['monto']+p.get('gan',0) for p in data['pos']])
    return t,t

def kb():
    m=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=4)
    m.add("BTC","ETH","SOL","XRP")
    m.add("DOGE","AVAX","LINK","ADA")
    m.add("NVDA","TSLA","XAUUSD","DASHBOARD")
    m.add("AUTO ON","AUTO OFF")
    return m

# --- DASHBOARD CORREGIDO ---
@app.route("/")
def home():
    tt, _ = totals()
    html=f"""<html><head><meta name='viewport' content='width=device-width'><style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
   .card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:4px solid #00ff88}}
   .top{{border:1.5px solid #00ff88;border-radius:15px;padding:12px;display:flex;justify-content:space-between;align-items:center}}
   .btn{{background:#00ff88;color:#000;padding:8px 15px;border-radius:20px;font-weight:bold}}
   .graf{{background:#00ff88;color:#000;width:100%;padding:12px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}
    </style></head><body>"""
    html+=f"<div class='top'><div><b>V29.2 MILLONARIO</b><br>Auto ejecuta solo</div><div><span class='btn'>{'AUTO ON' if data['auto_buy'] else 'AUTO OFF'}</span> <span style='background:#ffcc00;color:#000;padding:8px 12px;border-radius:10px;font-weight:bold'>${tt:.0f}</span></div></div>"
    html+=f"<div style='display:flex;justify-content:space-between;margin:12px 0'><span>Saldo ${data['b']:.0f}</span><span>Total ${tt:.0f}</span><span>Hoy ${data['gan_hoy']:.2f}</span></div>"
    for sym in ALL_COINS:
        rsi,price,ema20,btc_t = AN(sym)
        color="#00ff88" if rsi<32 else "#fff"
        html+=f"<div class='card'><b>{sym} ${price:.4f}</b><br><span style='color:{color}'>RSI {rsi:.1f}</span> | EMA ${ema20:.2f} | BTC {btc_t:.2f}%<br><a class='graf' href='/chart/{sym}'>📈 VER GRAFICA {sym}</a></div>"
    html+=f"<div class='card'>Pos abiertas: {len(data['pos'])}/{MAX_POS}</div></body></html>"
    return html

@app.route("/chart/<sym>")
def chart(sym):
    tv_map = {"XAUUSD":"OANDA:XAUUSD","NVDA":"NASDAQ:NVDA","TSLA":"NASDAQ:TSLA"}
    tv = tv_map.get(sym, f"BINANCE:{sym}USDT")
    p = P(sym); _,_,ema,_ = AN(sym)
    return f'''<html><head><meta name="viewport" content="width=device-width">
    <style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}a{{color:#00ff88;text-decoration:none;padding:12px;display:inline-block;font-weight:bold}}</style>
    </head><body><a href="/">← Volver Dashboard V29.2</a><b> {sym} ${p:.4f} EMA {ema:.2f}</b>
    <div id="tv" style="height:92vh"></div>
    <script src="https://s.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"autosize":true,"symbol":"{tv}","interval":"5","theme":"dark","style":"1","container_id":"tv"}})</script>
    </body></html>'''

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

# --- COMANDOS TELEGRAM CORREGIDOS ---
@bot.message_handler(func=lambda m: True)
def all_msg(m):
    txt = m.text.upper().strip() if m.text else ""
    if m.chat.id not in data["alert_users"]:
        data["alert_users"].append(m.chat.id); save()

    if txt in ["/START","START","/BALANCE","/B","BALANCE","B"]:
        t,_=totals()
        tg(m.chat.id, f"V29.2 LIVE ✅\nTotal: ${t:.2f}\nSaldo: ${data['b']:.2f}\nPos: {len(data['pos'])}/{MAX_POS}\nAuto: {'ON' if data['auto_buy'] else 'OFF'}\nDashboard: {DASH_URL}", kb())
        return
    if txt=="DASHBOARD":
        tg(m.chat.id, f"📊 Tu Dashboard V29.2:\n{DASH_URL}\n\nGraficas:\n{DASH_URL}/chart/BTC", kb())
        return
    if txt=="AUTO ON":
        data['auto_buy']=True; save()
        tg(m.chat.id, "✅ AUTO ON - Ya compro solo cuando RSI <32", kb())
        return
    if txt=="AUTO OFF":
        data['auto_buy']=False; save()
        tg(m.chat.id, "⏸️ AUTO OFF - Pausado", kb())
        return
    if txt in ALL_COINS:
        rsi,price,ema,btc_t = AN(txt)
        estado = "🔥 APTO PARA COMPRA" if price>ema*0.995 and rsi<32 else "⏳ Aun no compra"
        tg(m.chat.id, f"{txt} RSI {rsi:.1f} ${price:.4f}\nEMA ${ema:.2f} BTC {btc_t:.2f}%\n{estado}\nDash: {DASH_URL}\nGrafica: {DASH_URL}/chart/{txt}", kb())
        return

def auto_loop():
    while True:
        try:
            for sym in data["coins"]:
                if sym in COINS_STOCKS:
                    h=datetime.now(ZoneInfo('America/Mexico_City')).hour
                    if not (8 <= h <= 15): continue
                rsi,price,ema20,btc_t=AN(sym)
                if rsi<32 and price>ema20*0.995 and btc_t>-1.5:
                    if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(p['sym']==sym for p in data["pos"]):
                        data["pos"].append({"sym":sym,"monto":50,"gan":0,"precio_entry":price,"max_price":price})
                        data["b"]-=50; data["trades_hoy"]+=1; save()
                        for u in data["alert_users"]:
                            tg(u,f"🔥 V29.2 COMPRA {sym} ${price:.4f} RSI {rsi:.1f}\nGrafica: {DASH_URL}/chart/{sym}")
            time.sleep(60)
        except Exception as e: print(e); time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
