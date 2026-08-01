import os, threading, asyncio
import nest_asyncio
nest_asyncio.apply()
import yfinance as yf
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORTFOLIO = {"BTC":{"qty":0.00015,"free":0},"ETH":{"qty":0.028534,"free":0},"XRP":{"qty":0.0,"free":1000}}

app = Flask(__name__)
@app.route('/')
def home(): return "V13 LIVE"
@app.route('/health')
def health(): return "OK"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def get_price(t):
    try:
        df = yf.Ticker(t).history(period="1d")
        return float(df['Close'].iloc[-1]), float((df['Close'].iloc[-1]-df['Open'].iloc[0])/df['Open'].iloc[0]*100)
    except: return 0,0
def get_rate():
    try: return float(yf.Ticker("USDMXN=X").history(period="1d")['Close'].iloc[-1])
    except: return 18.6

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE): await u.message.reply_text("V13 LIVE - /balance")
async def bal(u: Update, c: ContextTypes.DEFAULT_TYPE):
    rate=get_rate(); total=0; txt=""
    for k in ["BTC","ETH","XRP"]:
        usd,ch=get_price(k+"-USD"); mxn=usd*rate; t=PORTFOLIO[k]["qty"]*mxn+PORTFOLIO[k]["free"]; total+=t
        txt+=f"{k}: ${mxn:.0f} MXN ({ch:+.1f}%)\n"
    txt+=f"\nTOTAL: ${total:.0f} / 3000 MXN"
    await u.message.reply_text(txt)
async def price_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    coin=u.message.text.replace("/","").upper(); usd,ch=get_price(coin+"-USD")
    await u.message.reply_text(f"{coin}: ${usd*get_rate():.0f} MXN {ch:+.1f}%")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app_t = ApplicationBuilder().token(BOT_TOKEN).build()
    app_t.add_handler(CommandHandler("start", start))
    app_t.add_handler(CommandHandler("balance", bal))
    app_t.add_handler(CommandHandler("btc", price_cmd))
    app_t.add_handler(CommandHandler("eth", price_cmd))
    app_t.add_handler(CommandHandler("xrp", price_cmd))
    app_t.run_polling(drop_pending_updates=True)

if __name__=="__main__": main()
