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

# --- CONFIG $5K REAL ---
MAX_POS = 10
MONTO_TRADE = 500
SALDO_INICIAL = 5000
# -----------------------

DASH_URL = "https://telegram-bot-cijp.onrender.com"

try:
    with open("data.json","r") as f: data=json.load(f)
    # Si venia de $50, ajustamos saldo solo si es primera vez
    if data.get("b",0) < 1000 and len(data.get("pos",[]))==0:
        data["b"]=SALDO_INICIAL
except:
    data={"b":SALDO_INICIAL,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[5471234634],"last_report_date":""}

data["coins"]=ALL_COINS

def save():
    try:
        with open("data.json","w") as f: json.dump(data,f)
    except: pass

def tg(chat,txt,markup=None):
    try: bot.send_message(chat,txt,reply_markup=markup, disable_web_page_preview=True)
    except Exception as e: print(f"TG Error {e}")

def P(sym):
    try:
        headers = {"User-Agent":"Mozilla/5.0"}
        if sym=="XAUUSD":
            r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",timeout=8, headers=headers).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        if sym in COINS_STOCKS:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",timeout=8, headers=headers).json()
            return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT",timeout=8).json()
        if 'price' not in r: return 0
        return float(r['price'])
    except Exception as e:
        print(f"P error {sym}: {e}")
        return 0

def AN(sym):
    try:
        price = P(sym)
        if price==0:
            return 50,0,0,0
        if sym in COINS_STOCKS+COINS_GOLD:
            return 29.0, price, price*0.998, 0

        kl_resp = requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=5m&limit=50",timeout=8)
        kl = kl_resp.json()
        if not isinstance(kl, list) or len(kl) < 20:
            # Binance esta limitando, regresamos datos del precio actual sin RSI
            print(f"Binance limit/wait en {sym}: {str(kl)[:100]}")
            return 50, price, price*0.998, 0

        closes=[float(k[4]) for k in kl]
        ema=sum(closes[-20:])/20
        gains=[max(0, closes[i]-closes[i-1]) for i in range(1,len(closes))]
        losses=[max(0, closes[i-1]-closes[i]) for i in range(1,len(closes))]
        rg=sum(gains[-14:])/14 or 0.01
        rl=sum(losses[-14:])/14 or 0.01
        rsi=100-(100/(1+rg/rl))

        try:
            btc=requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",timeout=5).json()
            btc_change = float(btc.get('priceChangePercent', 0))
        except:
            btc_change = 0
        return rsi, price, ema, btc_change
    except Exception as e:
        print(f"AN error {sym}: {e}")
        return 50,0,0,0

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
    html+=f"<div class='top'><div><b>V29.3 $5K REAL MODE</b><br>Auto ejecuta solo</div><div><span class='btn'>{'AUTO ON' if data['auto_buy'] else 'AUTO OFF'}</span> <span style='background:#ffcc00;color:#000;padding:8px 12px;border-radius:10px;font-weight:bold'>${tt:.0f}</span></div></div>"
    html+=f"<div style='display:flex;justify-content:space-between;margin:12px 0'><span>Saldo ${data['b']:.0f}</span><span>Total ${tt:.0f}</span><span>Hoy ${data['gan_hoy']:.2f}</span></div>"
    for sym in ALL_COINS:
        rsi,price,ema20,btc_t = AN(sym)
        color="#00ff88" if rsi<32 else "#fff"
        html+=f"<div class='card'><b>{sym} ${price:.4f}</b><br><span style='color:{color}'>RSI {rsi:.1f}</span> | EMA ${ema20:.2f} | BTC {btc_t:.2f}%<br><a class='graf' href='/chart/{sym}'>📈 VER GRAFICA {sym}</a></div>"
    html+=f"<div class='card'>Pos abiertas: {len(data['pos'])}/{MAX_POS} | Monto x Pos: ${MONTO_TRADE}</div></body></html>"
    return html

@app.route("/dashboard")
def dashboard_redirect():
    return home()

@app.route("/chart/<sym>")
def chart(sym):
    tv_map = {"XAUUSD":"OANDA:XAUUSD","NVDA":"NASDAQ:NVDA","TSLA":"NASDAQ:TSLA"}
    tv = tv_map.get(sym, f"BINANCE:{sym}USDT")
    p = P(sym); _,_,ema,_ = AN(sym)
    return f'''<html><head><meta name="viewport" content="width=device-width">
    <style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}a{{color:#00ff88;text-decoration:none;padding:12px;display:inline-block;font-weight:bold}}</style>
    </head><body><a href="/">← Volver Dashboard V29.3</a><b> {sym} ${p:.4f} EMA {ema:.2f}</b>
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

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    txt = m.text.upper().strip() if m.text else ""
    if m.chat.id not in data["alert_users"]:
        data["alert_users"].append(m.chat.id); save()

    if txt in ["/START","START","/BALANCE","/B","BALANCE","B"]:
        t,_=totals()
        tg(m.chat.id, f"V29.3 $5K REAL MODE LIVE ✅\nTotal: ${t:.2f}\nSaldo: ${data['b']:.2f}\nPos: {len(data['pos'])}/{MAX_POS} x ${MONTO_TRADE}\nAuto: {'ON' if data['auto_buy'] else 'OFF'}\nDashboard: {DASH_URL}", kb())
        return
    if txt=="DASHBOARD":
        tg(m.chat.id, f"📊 Dashboard V29.3:\n{DASH_URL}\n\nGraficas:\n{DASH_URL}/chart/BTC", kb())
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
                                tg(u,f"🔥 V29.3 COMPRA {sym} ${price:.4f} RSI {rsi:.1f} x ${MONTO_TRADE}\nGrafica: {DASH_URL}/chart/{sym}")
                except Exception as e_inner:
                    print(f"Error en {sym}: {e_inner}")
                    continue
                time.sleep(2) # pausa entre monedas para no saturar Binance
            time.sleep(90) # espera 90 seg entre ciclos
        except Exception as e:
            print(f"Error loop principal: {e}")
            time.sleep(60)
            continue

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
