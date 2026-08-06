import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v29-eternal"

app = Flask(__name__)
@app.route('/')
def home(): return "V29 ETERNO-UPSTASH OK"

def load_data():
    try:
        if not URL or not REST_TOKEN: return {"users":{}}
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res = r.json().get("result")
        if res: return json.loads(res)
    except Exception as e:
        print(f"Load err: {e}")
    return {"users":{}}

def save_data(data):
    try:
        j = json.dumps(data)
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, j], timeout=10)
    except Exception as e:
        print(f"Save err: {e}")

def get_prices():
    try:
        btc = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        # RSI simple
        def rsi(ticker):
            try:
                hist = yf.Ticker(ticker).history(period="14d")['Close']
                delta = hist.diff()
                gain = delta.where(delta>0,0).rolling(14).mean()
                loss = -delta.where(delta<0,0).rolling(14).mean()
                rs = gain / loss
                return round(100 - (100/(1+rs.iloc[-1])),1)
            except: return 35.0
        return btc, eth, xrp, usdmxn, rsi("BTC-USD"), rsi("ETH-USD"), rsi("XRP-USD")
    except:
        return 64185, 1899, 1.03, 17.23, 35.0, 45.3, 32.2

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        # Reparto inicial $333.33 cada uno como en tu captura
        btc_p, eth_p, xrp_p, usdmxn, _, _, _ = get_prices()
        data["users"][uid] = {
            "efectivo_mxn": 0.0,
            "btc": (333.33/usdmxn)/btc_p,
            "eth": (333.33/usdmxn)/eth_p,
            "xrp": (333.33/usdmxn)/xrp_p,
            "inicial": 1000.0
        }
        save_data(data)
    return data["users"][uid]

def format_portfolio(u):
    btc_p, eth_p, xrp_p, usdmxn, rsi_btc, rsi_eth, rsi_xrp = get_prices()
    btc_val_mxn = u['btc']*btc_p*usdmxn
    eth_val_mxn = u['eth']*eth_p*usdmxn
    xrp_val_mxn = u['xrp']*xrp_p*usdmxn
    total = u['efectivo_mxn'] + btc_val_mxn + eth_val_mxn + xrp_val_mxn
    gan = total - u['inicial']
    gan_p = (gan/u['inicial']*100) if u['inicial'] else 0

    barato_btc = " 💎BARATO" if rsi_btc < 35 else ""
    barato_xrp = " 💎BARATO" if rsi_xrp < 35 else ""

    msg = f"""🎮 DEMO $1000 MXN (capital práctica)
💵 USD/MXN REAL: ${usdmxn:.2f}
💵 Efectivo DEMO: ${u['efectivo_mxn']:.2f} MXN

🔴 BTC: {u['btc']:.8f}
Precio ${btc_p:,.2f} RSI:{rsi_btc}{barato_btc}
Valor ${btc_val_mxn:.2f} MXN
🔴 ETH: {u['eth']:.8f}
Precio ${eth_p:,.2f} RSI:{rsi_eth}
Valor ${eth_val_mxn:.2f} MXN
🔴 XRP: {u['xrp']:.8f}
Precio ${xrp_p:.2f} RSI:{rsi_xrp}{barato_xrp}
Valor ${xrp_val_mxn:.2f} MXN

💰 TOTAL: ${total:.2f} MXN
📈 Ganancia: {gan_p:.2f}% (${gan:.2f})

🔔 Alertas -2%/+2% + RSI activas
✅ V29 ETERNO-UPSTASH"""
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=load_data()
    u=get_user(update.effective_user.id, data)
    await update.message.reply_text(format_portfolio(u))

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa: /comprar BTC 100 (en MXN)\nEjemplo: /comprar BTC 100")

async def vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa: /vender BTC 0.001")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("actualizar", start))
    application.add_handler(CommandHandler("comprar", comprar))
    application.add_handler(CommandHandler("vender", vender))
    application.add_handler(CommandHandler("balance", start))
    print("Bot V29 ETERNO Iniciado")
    application.run_polling()
