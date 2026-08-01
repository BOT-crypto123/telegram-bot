import os
import threading
import logging
import json
import yfinance as yf
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# WEB SERVER 100% GRATIS - Para que Render no se apague
app = Flask(__name__)
@app.route('/')
def home(): return "Bot V11 LIVE - 100% Gratis Vicente"
@app.route('/health')
def health(): return "OK"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

# PORTAFOLIO $3000 MXN
PORTFOLIO = {"BTC":{"qty":0.00015,"mxn_free":0},"ETH":{"qty":0.028534,"mxn_free":0},"XRP":{"qty":0.0,"mxn_free":1000}}

def get_prices():
    try:
        usd_mxn = yf.Ticker("USDMXN=X").
