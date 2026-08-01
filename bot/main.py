import os, threading
import yfinance as yf
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORTFOLIO = {"BTC":{"qty":0.00015,"free":0},"ETH":{"qty":0.028534,"free":0},"XRP":{"qty":0.0,"free":1000}}

app = Flask(__name__)
@app.route('/')
def home(): return "V12 LIVE"
@app.route('/health')
def health(): return "OK"

def run_web():
    p = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=p)

def get_price(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d")
        last = float(df['Close'].iloc[-1])
        open_p = float(df['Open'].iloc[0])
        ch = (last-open_p)/open_p*100
        return last, ch
    except: return 0,0

def get_rate():
    try: return float(yf.Ticker("USDMXN=X").history(period="1d")['Close'].iloc[-1])
    except: return 18.6

def build_msg():
    rate = get_rate()
    total = 0
    txt = ""
    for c in ["BTC","ETH","XRP"]:
        usd,ch = get_price(c+"-USD")
        mxn = usd*rate
        h = PORTFOLIO[c]
        t = h["qty"]*mxn + h["free"]
        total+=t
        txt+=f"{c}: ${mxn:.0f} MXN ({ch:+.1f}%)\n"
    txt+=f"\nTOTAL: ${total:.0f} / 3000 MXN"
    return txt

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("V12 LIVE - Usa /balance /btc /eth /xrp")

async def bal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_msg())

async def price_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.replace("/","").upper()
    usd,ch = get_price(coin+"-USD")
    await update.message.reply_text(f"{coin}: ${usd*get_rate():.0f} MXN {ch:+.1f}%")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app_t = ApplicationBuilder().token(BOT_TOKEN).build()
    app_t.add_handler(CommandHandler("start", start))
    app_t.add_handler(CommandHandler("balance", bal))
    app_t.add_handler(CommandHandler("btc", price_cmd))
    app_t.add_handler(CommandHandler("eth", price_cmd))
    app_t.add_handler(CommandHandler("xrp", price_cmd))
    app_t.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
