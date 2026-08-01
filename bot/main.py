import os, json, threading, time
from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_FILE = "/tmp/chat_id.txt"
BALANCE_FILE = "/tmp/balance.json"
CACHE = {"t":0, "data":None}
INIT = 1000.0
COMISION = 0.0078

app = Flask(__name__)
@app.route('/')
def h(): return "V18 SEPARADO LIVE"
@app.route('/health')
def hl(): return "OK"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

def get_prices():
    global CACHE
    if time.time() - CACHE["t"] < 60 and CACHE["data"]: return CACHE["data"]
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]"
        r = requests.get(url, timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        data = {"btc": d['BTCUSDT'], "eth": d['ETHUSDT'], "xrp": d['XRPUSDT']}
        CACHE = {"t": time.time(), "data": data}
        return data
    except:
        return CACHE["data"]

def load_bal():
    try:
        with open(BALANCE_FILE,'r') as f: return json.load(f)
    except:
        return {"btc": (INIT/3)/68000, "eth": (INIT/3)/3400, "xrp": (INIT/3)/0.6, "usd":0, "init":INIT, "p_btc":68000,"p_eth":3400,"p_xrp":0.6}
def save_bal(b):
    with open(BALANCE_FILE,'w') as f: json.dump(b,f)

def fmt_one(moneda):
    precios = get_prices()
    if not precios: return "Actualizando, intenta en 5 seg"
    bal = load_bal()
    price, change = precios[moneda]
    qty = bal[moneda]
    valor = qty * price
    p_compra = bal.get(f"p_{moneda}", price)
    gan = (price - p_compra)/p_compra*100 if p_compra else 0
    return (f"🟢 {moneda.upper()}: ${price:,.2f} ({change:+.2f}%)\n"
            f"Tienes: {qty:.6f} {moneda.upper()}\n"
            f"Valor: ${valor:.2f}\n"
            f"Compra: ${p_compra:,.2f}\n"
            f"Gan: {gan:+.2f}%")

def fmt_all():
    precios = get_prices()
    if not precios: return "Actualizando..."
    bal = load_bal()
    btc_p, btc_c = precios['btc']; eth_p, eth_c = precios['eth']; xrp_p, xrp_c = precios['xrp']
    total = bal['btc']*btc_p + bal['eth']*eth_p + bal['xrp']*xrp_p + bal['usd']
    txt = (f"📊 BALANCE TOTAL ${total:.2f}\n\n"
           f"BTC: ${btc_p:,.0f} ({btc_c:+.1f}%) = ${bal['btc']*btc_p:.2f}\n"
           f"ETH: ${eth_p:,.0f} ({eth_c:+.1f}%) = ${bal['eth']*eth_p:.2f}\n"
           f"XRP: ${xrp_p:.4f} ({xrp_c:+.1f}%) = ${bal['xrp']*xrp_p:.2f}\n\n"
           f"Ganancia: ${total-INIT:+.2f}")
    return txt

def get_buttons(moneda=None):
    if moneda:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🟢 Comprar {moneda.upper()}", callback_data=f"comprar_{moneda}"),
             InlineKeyboardButton(f"🔴 Vender {moneda.upper()}", callback_data=f"vender_{moneda}")],
            [InlineKeyboardButton("💰 Ver Todo", callback_data="todo")]
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 BTC", callback_data="ver_btc"), InlineKeyboardButton("🔴 BTC", callback_data="vender_btc")],
        [InlineKeyboardButton("🟢 ETH", callback_data="ver_eth"), InlineKeyboardButton("🔴 ETH", callback_data="vender_eth")],
        [InlineKeyboardButton("🟢 XRP", callback_data="ver_xrp"), InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp")],
        [InlineKeyboardButton("💰 Balance Total", callback_data="todo")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE,'w') as f: f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ V18 - Monedas separadas\n/btc /eth /xrp /balance", reply_markup=get_buttons())

async def cmd_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_one("btc"), reply_markup=get_buttons("btc"))
async def cmd_eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_one("eth"), reply_markup=get_buttons("eth"))
async def cmd_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_one("xrp"), reply_markup=get_buttons("xrp"))
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_all(), reply_markup=get_buttons())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    bal = load_bal(); precios = get_prices()
    if not precios: return
    data = q.data
    if data.startswith("ver_"):
        m = data.split("_")[1]
        await q.edit_message_text(fmt_one(m), reply_markup=get_buttons(m)); return
    if data == "todo":
        await q.edit_message_text(fmt_all(), reply_markup=get_buttons()); return
    if data == "precio":
        await q.edit_message_text(fmt_all(), reply_markup=get_buttons()); return
    accion, moneda = data.split("_")
    precio = precios[moneda][0]
    if accion == "comprar":
        cant = (50*(1-COMISION))/precio; bal[moneda]+=cant; bal[f"p_{moneda}"]=precio; save_bal(bal)
        await q.edit_message_text(f"✅ COMPRA {moneda.upper()}\n\n"+fmt_one(moneda), reply_markup=get_buttons(moneda))
    else:
        if bal[moneda]<=0:
            await q.answer(f"No tienes {moneda.upper()}"); return
        usd = bal[moneda]*precio*(1-COMISION); bal
