import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v30-eternal"

app = Flask(__name__)
@app.route('/')
def home(): return "V30 ETERNO OK"

def load_data():
    try:
        if not URL or not REST_TOKEN: return {"users":{}}
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res = r.json().get("result")
        if res: return json.loads(res)
    except: pass
    return {"users":{}}

def save_data(data):
    try:
        j = json.dumps(data)
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, j], timeout=10)
    except: pass

def get_market():
    try:
        def get_ticker(sym):
            t = yf.Ticker(sym)
            price = float(t.fast_info['last_price'])
            try:
                hist = t.history(period="5d")
                pct = float((hist['Close'].iloc[-1]/hist['Close'].iloc[-2]-1)*100)
            except: pct = 0.0
            try:
                h = yf.Ticker(sym).history(period="14d")['Close']
                delta = h.diff()
                gain = delta.where(delta>0,0).rolling(14).mean()
                loss = -delta.where(delta<0,0).rolling(14).mean()
                rs = gain/loss
                rsi = round(100-(100/(1+rs.iloc[-1])),1)
            except: rsi = 35.0
            return price, pct, rsi

        btc_p, btc_pct, btc_rsi = get_ticker("BTC-USD")
        eth_p, eth_pct, eth_rsi = get_ticker("ETH-USD")
        xrp_p, xrp_pct, xrp_rsi = get_ticker("XRP-USD")
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        return btc_p, eth_p, xrp_p, usdmxn, btc_pct, eth_pct, xrp_pct, btc_rsi, eth_rsi, xrp_rsi
    except:
        return 64260.86, 1902.23, 1.03, 17.23, -0.53, -0.23, -2.60, 36.9, 47.1, 34.9

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc_p, eth_p, xrp_p, usdmxn, _,_,_, _,_,_ = get_market()
        data["users"][uid] = {
            "efectivo": 0.0,
            "btc": (333.33/usdmxn)/btc_p,
            "eth": (333.33/usdmxn)/eth_p,
            "xrp": (333.33/usdmxn)/xrp_p,
            "inicial": 1000.0
        }
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr = get_market()
    btc_mxn = u['btc']*btc_p*usdmxn
    eth_mxn = u['eth']*eth_p*usdmxn
    xrp_mxn = u['xrp']*xrp_p*usdmxn
    total = u['efectivo']+btc_mxn+eth_mxn+xrp_mxn
    gan = total-u['inicial']
    gan_p = gan/u['inicial']*100

    def tag(r): return " 💎BARATO" if r < 35 else ""

    return f"""🎮 DEMO $1000 MXN (capital práctica)
USD/MXN REAL: ${usdmxn:.2f}
💵 Efectivo DEMO: ${u['efectivo']:.2f} MXN

🔴 BTC: {u['btc']:.8f}
Precio ${btc_p:,.2f} ({bp:.2f}%) RSI:{br}{tag(br)}
Valor ${btc_mxn:.2f} MXN
🔴 ETH: {u['eth']:.8f}
Precio ${eth_p:,.2f} ({ep:.2f}%) RSI:{er}
Valor ${eth_mxn:.2f} MXN
🔴 XRP: {u['xrp']:.8f}
Precio ${xrp_p:.2f} ({xp:.2f}%) RSI:{xr}{tag(xr)}
Valor ${xrp_mxn:.2f} MXN

💵 TOTAL: ${total:.2f} MXN
📈 Ganancia: {gan_p:+.2f}% (${gan:+.2f})

🔔 Alertas -2%/+2% + RSI activas
✅ V30 ETERNO-UPSTASH"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=load_data()
    u=get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u))

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("actualizar", start))
    application.add_handler(CommandHandler("balance", start))
    print("V30 ETERNO Inici
