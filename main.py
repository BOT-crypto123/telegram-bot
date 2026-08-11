import os, json, time, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask
import telebot

TOKEN = os.getenv("BOT_TOKEN")
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# --- V29.1 CONFIG MILLONARIA + GRAFICAS ---
COINS_CRIPTO = ["ADA","AVAX","BTC","DOGE","ETH","LINK","SOL","XRP"]
COINS_STOCKS = ["NVDA","TSLA"]
COINS_GOLD = ["XAUUSD"]
ALL_COINS = COINS_CRIPTO + COINS_STOCKS + COINS_GOLD
MAX_POS = 8

try:
    with open("data.json","r") as f: data=json.load(f)
except: data={"b":4950,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[5471234634],"last_report_date":""}

data["coins"] = ALL_COINS
dash_url = "https://telegram-bot-cijp.onrender.com"

def save():
    with open("data.json","w") as f: json.dump(data,f)

def tg(chat,txt):
    try: bot.send_message(chat,txt)
    except Exception as e: print(e)

def P(sym):
    try:
        if sym=="XAUUSD":
            r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F",timeout=5).json()
            return r['chart']['result'][0]['meta']['regularMarketPrice']
        if sym in COINS_STOCKS:
            r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",timeout=5).json()
            return r['chart']['result'][0]['meta']['regularMarketPrice']
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT",timeout=5).json()
        return float(r['price'])
    except: return 0

def AN(sym):
    try:
        price = P(sym)
        if sym in COINS_STOCKS+COINS_GOLD:
            return 29.0, price, price*0.998, 0
        # CRIPTO: RSI REAL (tu logica)
        kl=requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=5m&limit=50",timeout=8).json()
        closes=[float(k[4]) for k in kl]
        # EMA20
        ema=sum(closes[-20:])/20
        # RSI14 rapido
        gains=[max(0, closes[i]-closes[i-1]) for i in range(1,len(closes))]
        losses=[max(0, closes[i-1]-closes[i]) for i in range(1,len(closes))]
        rg=sum(gains[-14:])/14 or 0.01
        rl=sum(losses[-14:])/14 or 0.01
        rs=rg/rl
        rsi=100-(100/(1+rs))
        # BTC trend
        btc=requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",timeout=5).json()
        btc_t=float(btc['priceChangePercent'])
        return rsi, price, ema, btc_t
    except: return 50,0,0,0

def totals():
    t=data['b']+sum([p['monto'] for p in data['pos']])
    return t,t

@app.route("/chart/<sym>")
def chart(sym):
    tv_map = {"XAUUSD":"OANDA:XAUUSD","NVDA":"NASDAQ:NVDA","TSLA":"NASDAQ:TSLA"}
    tv = tv_map.get(sym, f"BINANCE:{sym}USDT")
    return f'''<html><head><meta name="viewport" content="width=device-width">
    <style>body{{margin:0;background:#000;color:#fff;font-family:Arial}}a{{color:#00ff88;text-decoration:none;padding:10px;display:inline-block}}</style>
    </head><body><a href="/">← Volver Dashboard V29.1</a><b> {sym}/USDT - V29.1 | EMA20: {AN(sym)[2]:.4f}$ | Ahora: {P(sym):.4f}$</b>
    <div id="tv" style="height:92vh"></div>
    <script src="https://s.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"autosize":true,"symbol":"{tv}","interval":"5","theme":"dark","style":"1","container_id":"tv"}})</script>
    </body></html>'''

@app.route("/")
def home():
    html = f"<html><head><meta name='viewport' content='width=device-width'><style>body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}.card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0}}.top{{border:1.5px solid #00ff88;border-radius:15px;padding:10px;display:flex;justify-content:space-between}}.btn{{background:#00ff88;color:#000;padding:8px 15px;border-radius:20px;font-weight:bold}}.graf{{background:#333;color:#fff;width:100%;padding:10px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none}}</style></head><body>"
    html+=f"<div class='top'><div><b>V29.1 MILLONARIO + GRAFICAS</b><br>Millonario ejecuta solo</div><div><span class='btn'>AUTO ON</span> <span style='background:#ffcc00;color:#000;padding:8px 12px;border-radius:10px'>${totals()[0]:.0f}</span></div></div>"
    html+=f"<div style='display:flex;justify-content:space-between;margin:10px 0'><span>Saldo ${data['b']:.0f}</span><span>Total ${totals()[0]:.0f}</span><span>Hoy ${data['gan_hoy']:.2f}</span></div>"
    for sym in ALL_COINS:
        rsi,price,ema20,btc_t = AN(sym)
        html+=f"<div class='card'><b>{sym} ${price:.4f}</b> <span style='float:right;border:1px solid #ffcc00;padding:5px 10px;border-radius:10px'>3/5</span><br>RSI {rsi:.1f} | EMA ${ema20:.2f}<br>BTC {btc_t:.2f}% | BLOQUEADO<br><a class='graf' href='/chart/{sym}'>VER GRAFICA</a></div>"
    html+="</body></html>"
    return html

def auto_loop():
    while True:
        try:
            for txt in data["coins"]:
                if txt in COINS_STOCKS:
                    h=datetime.now(ZoneInfo('America/Mexico_City')).hour
                    if not (8 <= h <= 15): continue
                rsi,price,ema20,btc_t=AN(txt)
                filt = price>ema20*0.995 and btc_t>-1.5
                if rsi<32 and filt:
                    if data.get('auto_buy') and len(data["pos"])<MAX_POS and not any(p['sym']==txt for p in data["pos"]):
                        data["pos"].append({"sym":txt,"monto":50,"gan":0,"precio_entry":price,"max_price":price})
                        data["b"]-=50; data["trades_hoy"]+=1; save()
                        for u in data["alert_users"]: tg(u,f"🔥 V29.1 COMPRA {txt} ${price:.4f} RSI {rsi:.1f}\nGrafica: {dash_url}/chart/{txt}")
            time.sleep(60)
        except Exception as e: print(e); time.sleep(10)

def daily_report_loop():
    tz = ZoneInfo('America/Mexico_City')
    while True:
        try:
            now = datetime.now(tz)
            if now.hour==22 and now.minute<5 and data.get('last_report_date')!=now.strftime("%Y-%m-%d"):
                for u in data["alert_users"]: tg(u,f"REPORTE V29.1\nTotal: ${totals()[0]:.2f}\nPos: {len(data['pos'])}/{MAX_POS}")
                data['last_report_date']=now.strftime("%Y-%m-%d"); save(); time.sleep(300)
            time.sleep(60)
        except: time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()
threading.Thread(target=daily_report_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
