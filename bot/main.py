import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-bot-v29"

app = Flask(__name__)
@app.route('/')
def home(): return "Bot V29 Activo - Upstash OK"

def load_data():
    try:
        if not URL or not REST_TOKEN: raise Exception("No URL")
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        data = r.json().get("result")
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"Load error: {e}")
    return {"users": {}}

def save_data(data):
    try:
        j = json.dumps(data)
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, j], timeout=10)
        print("Guardado en Upstash OK")
    except Exception as e:
        print(f"Save error: {e}")

def get_price():
    try:
        btc = yf.Ticker("BTC-USD")
        return float(btc.fast_info['last_price'])
    except:
        return 65000.0

def get_user_data(user_id, data):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 1000.0, "btc": 0.0}
        save_data(data)
    return data["users"][uid]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    u = get_user_data(update.effective_user.id, data)
    await update.message.reply_text(f"🚀 Bot BTC Activo!\n💰 Balance: ${u['balance']:.2f}\n₿ BTC: {u['btc']}\n\nUsa:\n/price - precio\n/buy 100 - comprar $100\n/sell 0.01 - vender\n/balance - ver todo")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price()
    await update.message.reply_text(f"₿ BTC ahora: ${p:,.2f}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    u = get_user_data(update.effective_user.id, data)
    p = get_price()
    total = u['balance'] + (u['btc'] * p)
    await update.message.reply_text(f"📊 Tu cuenta:\nEfectivo: ${u['balance']:.2f}\nBTC: {u['btc']}\nValor BTC: ${u['btc']*p:.2f}\nTOTAL: ${total:.2f}")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(context.args[0])
        data = load_data()
        u = get_user_data(update.effective_user.id, data)
        if u['balance'] < amount:
            await update.message.reply_text("❌ No tienes suficiente saldo")
            return
        p = get_price()
        btc_bought = amount / p
        u['balance'] -= amount
        u['btc'] += btc_bought
        save_data(data)
        await update.message.reply_text(f"✅ Compraste {btc_bought:.6f} BTC por ${amount:.2f}\nPrecio: ${p:,.2f}")
    except:
        await update.message.reply_text("Uso: /buy 100")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(context.args[0])
        data = load_data()
        u = get_user_data(update.effective_user.id, data)
        if u['btc'] < amount:
            await update.message.reply_text("❌ No tienes suficiente BTC")
            return
        p = get_price()
        usd = amount * p
        u['btc'] -= amount
        u['balance'] += usd
        save_data(data)
        await update.message.reply_text(f"✅ Vendiste {amount} BTC por ${usd:.2f}")
    except:
        await update.message.reply_text("Uso: /sell 0.01
