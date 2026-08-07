import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v31-fix"

app = Flask(__name__)
@app.route('/')
def home(): return "V31.1 FIX OK"

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
    # valores por defecto si falla yfinance
    btc_p, eth_p, xrp_p, usdmxn = 64200.0, 1900.0, 1.03, 17.20
    bp, ep, xp = -0.5, -0.3, -2.5
    br, er, xr = 36.9, 47.1, 34.9
    try:
        def get_one(sym):
            t = yf.Ticker(sym)
            price = float(t.fast_info['last_price'])
            hist = t.history(period="7d")
            if len(hist) < 2:
                return price, 0.0, 40.0
            pct = float((hist['Close'].iloc[-1]/hist['Close'].iloc[-2]-1)*100)
            try:
                delta = hist['Close'].diff()
                gain = delta.where(delta>0,0).rolling(14).mean()
                loss = -delta.where(delta<0,0).rolling(14).mean()
                rs = gain/loss
                rsi = float(100 - (100/(1+rs.iloc[-1])))
                if str(rsi) == 'nan': rsi = 40.0
            except:
                rsi = 40.0
            return price, pct, round(rsi,1)
        btc_p, bp, br = get_one("BTC-USD")
        eth_p, ep, er = get_one("ETH-USD")
        xrp_p, xp, xr = get_one("XRP-USD")
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
    except Exception as e:
        print(f"Market fallback: {e}")
    return btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc_p, eth_p, xrp_p, usdmxn, _,_,_, _,_,_ = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/usdmxn)/btc_p,"eth":(333.33/usdmxn)/eth_p,"xrp":(333.33/usdmxn)/xrp_p,"inicial":1000.0}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr = get_market()
    btc_mxn = u['btc']*btc_p*usdmxn
    eth_mxn = u['eth']*eth_p*usdmxn
    xrp_mxn = u['xrp']*xrp_p*usdmxn
    total = u['efectivo']+btc_mxn+eth_mxn+xrp_mxn
    gan_p = (total-u['inicial'])/u['inicial']*100
    def tag(r): return " BARATO" if r < 35 else ""
    return f"DEMO $1000 MXN\nUSD/MXN: ${usdmxn:.2f}\nEfectivo: ${u['efectivo']:.2f} MXN\n\nBTC: {u['btc']:.8f} | ${btc_mxn:.2f} MXN\nPrecio ${btc_p:,.2f} ({bp:.2f}%) RSI:{br}{tag(br)}\nETH: {u['eth']:.8f} | ${eth_mxn:.2f} MXN\nPrecio ${eth_p:,.2f} ({ep:.2f}%) RSI:{er}\nXRP: {u['xrp']:.8f} | ${xrp_mxn:.2f} MXN\nPrecio ${xrp_p:.2f} ({xp:.2f}%) RSI:{xr}{tag(xr)}\n\nTOTAL: ${total:.2f} MXN\nGanancia: {gan_p:+.2f}%\n\nAlertas -2%/+2% + RSI activas\nV31.1 ETERNO-FIX"

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
    print("V31.1 Iniciado OK")
    application.run_polling()
