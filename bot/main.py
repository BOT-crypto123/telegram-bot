import os
import threading
import yfinance as yf
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot V11 LIVE"
@app.route('/health')
def health():
    return "OK"
def run_web():
    p = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=p)
threading.Thread(target=run_web, daemon=True).start()

PORT = {"BTC":{"qty":0.00015,"free":0},"ETH":{"qty":0.028534,"free":0},"XRP":{"qty":0.0,"free":1000}}

def get_price(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1d")
        usd = float(df['Close'].iloc[-1])
        opn = float(df['Open'].iloc[0])
        ch = (usd-opn)/opn*100
        return usd, ch
    except:
        return 0,0

def get_rate():
    try:
        df = yf.Ticker("USDMXN=X").history(period="1d")
        return float(df['Close'].iloc[-1])
    except:
        return 18.6

def build_msg():
    rate = get_rate()
    txt = ""
    total = 0
    for coin in ["BTC","ETH","XRP"]:
        usd,ch = get_price(coin+"-USD")
        mxn = usd*rate
        h = PORT[coin]
        tot = h["qty"]*mxn+h["free"]
        total += tot
        txt += f"{coin}: ${mxn:.0f} MXN (${usd:.2f}) {ch:+.2f}%\n"
        txt += f"Saldo: ${h['free']:.0f} | {h['qty']:.6f}\n"
        txt += f"TOTAL {coin}: ${tot:.0f}\n\n"
    txt += f"TOTAL: ${total:.0f} / 3000 MXN"
    return txt

def kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 BTC",callback_data="buy_BTC"),InlineKeyboardButton("🟢 ETH",callback_data="buy_ETH"),InlineKeyboardButton("🟢 XRP",callback_data="buy_XRP")],
        [InlineKeyboardButton("🔴 BTC",callback_data="sell_BTC"),InlineKeyboardButton("🔴 ETH",callback_data="sell_ETH"),InlineKeyboardButton("🔴 XRP",callback_data="sell_XRP")]
    ])

async def start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("V11 LIVE /balance",reply_markup=kb())
async def bal(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Consultando...")
    await update.message.reply_text(build_msg(),reply_markup=kb())
async def pr(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.replace("/","").upper()
    usd,ch = get_price(coin+"-USD")
    rate = get_rate()
    await update.message.reply_text(f"{coin}: ${usd*rate:.0f} MXN {ch:+.2f}%",reply_markup=kb())
async def btn(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    await q.message.reply_text(f"Senal {q.data}")

def main():
    app_t = ApplicationBuilder().token(BOT_TOKEN).build()
    app_t.add_handler(CommandHandler("start",start))
    app_t.add_handler(CommandHandler("balance",bal))
    app_t.add_handler(CommandHandler("btc",pr))
    app_t.add_handler(CommandHandler("eth",pr))
    app_t.add_handler(CommandHandler("xrp",pr))
    app_t.add_handler(CallbackQueryHandler(btn))
    app_t.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
