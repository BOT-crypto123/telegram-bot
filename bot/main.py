import os
import threading
import logging
import json
import yfinance as yf
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === WEB SERVER 100% GRATIS PARA RENDER ===
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot Vicente V11 LIVE - 100% Gratis"
@app.route('/health')
def health():
    return "OK"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

# === TU PORTAFOLIO $3000 MXN ===
PORTFOLIO_FILE = "/tmp/portfolio.json"
DEFAULT_PORTFOLIO = {
    "BTC": {"qty": 0.00015, "mxn_free": 0},
    "ETH": {"qty": 0.028534, "mxn_free": 0},
    "XRP": {"qty": 0.0, "mxn_free": 1000}
}
CAPITAL_INICIAL = 3000

def load_portfolio():
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
    except: pass
    return DEFAULT_PORTFOLIO

def get_prices():
    try:
        usd_mxn_data = yf.Ticker("USDMXN=X").history(period="1d")
        usd_mxn = usd_mxn_data['Close'].iloc[-1] if not usd_mxn_data.empty else 18.5
    except: usd_mxn = 18.5
    tickers = {"BTC": "BTC-USD", "ETH": "ETH-USD", "XRP": "XRP-USD"}
    result = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="1d")
            if not data.empty:
                usd = data['Close'].iloc[-1]
                change = ((usd - data['Open'].iloc[0]) / data['Open'].iloc[0] * 100)
                result[name] = {"usd": usd, "mxn": usd*usd_mxn, "change": change}
        except: pass
    return result, usd_mxn

def build_balance_message():
    portfolio = load_portfolio()
    prices, _ = get_prices()
    total_mxn = 0
    msg = ""
    for coin in ["BTC", "ETH", "XRP"]:
        p = prices.get(coin)
        if not p: continue
        hold = portfolio.get(coin, {"qty":0,"mxn_free":0})
        qty = hold.get("qty",0)
        mxn_free = hold.get("mxn_free",0)
        total_coin = qty * p["mxn"] + mxn_free
        total_mxn += total_coin
        msg += f"{coin}: ${p['mxn']:,.0f} MXN (${p['usd']:,.2f}) ({p['change']:+.2f}%)\n"
        msg += f"Saldo: ${mxn_free:.0f} MXN | {qty:.6f}\n"
        msg += f"TOTAL {coin}: ${total_coin:.0f} MXN\n\n"
    msg += f"💰 TOTAL: ${total_mxn:.0f} / ${CAPITAL_INICIAL} MXN"
    return msg

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 BTC", callback_data="buy_BTC"),
         InlineKeyboardButton("🟢 ETH", callback_data="buy_ETH"),
         InlineKeyboardButton("🟢 XRP", callback_data="buy_XRP")],
        [InlineKeyboardButton("🔴 BTC", callback_data="sell_BTC"),
         InlineKeyboardButton("🔴 ETH", callback_data="sell_ETH"),
         InlineKeyboardButton("🔴 XRP", callback_data="sell_XRP")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡VICENTE! Bot V11 LIVE\n\n/balance - Ver portafolio", reply_markup=get_keyboard())

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Consultando...")
    await update.message.reply_text(build_balance_message(), reply_markup=get_keyboard())

async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.replace("/","").upper()
    prices,_ = get_prices()
    if coin in prices:
        p = prices[coin]
        await update.message.reply_text(f"{coin}: ${p['mxn']:,.0f} MXN (${p['usd']:,.2f}) {p['change']:+.2f}%", reply_markup=get_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, coin = query.data.split("_")
    await query.message.reply_text(f"{'🟢 COMPRA' if action=='buy' else '🔴 VENTA'} {coin} - Usa /balance")

def main():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("balance", balance_cmd))
    app_telegram.add_handler(CommandHandler("btc", price_cmd))
    app_telegram.add_handler(CommandHandler("eth", price_cmd))
    app_telegram.add_handler(CommandHandler("xrp", price_cmd))
    app_telegram.add_handler(CallbackQueryHandler(button_callback))
    app_telegram.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
