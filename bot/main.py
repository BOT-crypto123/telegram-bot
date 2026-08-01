import os, json, threading, time, sys
print("=== INICIANDO V19 ===", flush=True)

from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    print("ERROR: No hay BOT_TOKEN en Environment", flush=True)
    sys.exit(1)

print(f"Token OK: {TOKEN[:10]}...", flush=True)

CHAT_ID_FILE = "/tmp/chat_id.txt"
BALANCE_FILE = "/tmp/balance.json"
CACHE = {"t":0, "data":None}
INIT = 1000.0
COMISION = 0.0078

app = Flask(__name__)
@app.route('/')
def h(): return "V19 SEPARADO LIVE - OK"
@app.route('/health')
def hl(): return "OK"
def run_web():
    port = int(os.environ.get("PORT",10000))
    print(f"Web en puerto {port}", flush=True)
    app.run(host='0.0.0.0', port=port)

def get_prices():
    global CACHE
    if time.time() - CACHE["t"] < 60 and CACHE["data"]:
        return CACHE["data"]
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]"
        r = requests.get(url, timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        data = {"btc": d['BTCUSDT'], "eth": d['ETHUSDT'], "xrp": d['XRPUSDT']}
        CACHE = {"t": time.time(), "data": data}
        return data
    except Exception as e:
        print(f"Error Binance: {e}", flush=True)
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
    if not precios: return "Actualizando precios... espera 10 seg y dale /"+moneda
    bal = load_bal()
    price, change = precios[moneda]
    qty = bal[moneda]
    return f"🟢 {moneda.upper()}: ${price:,.2f} ({change:+.2f}%)\nTienes: {qty:.6f}\nValor: ${qty*price:.2f}"

def fmt_all():
    precios = get_prices()
    if not precios: return "Actualizando... /balance en 10 seg"
    bal = load_bal()
    btc_p,_ = precios['btc']; eth_p,_ = precios['eth']; xrp_p,_ = precios['xrp']
    total = bal['btc']*btc_p + bal['eth']*eth_p + bal['xrp']*xrp_p + bal['usd']
    return f"📊 TOTAL: ${total:.2f}\nBTC ${bal['btc']*btc_p:.2f} | ETH ${bal['eth']*eth_p:.2f} | XRP ${bal['xrp']*xrp_p:.2f}"

def get_buttons(moneda=None):
    if moneda:
        return InlineKeyboardMarkup([[InlineKeyboardButton(f"🟢 Comprar {moneda.upper()}", callback_data=f"comprar_{moneda}"), InlineKeyboardButton(f"🔴 Vender {moneda.upper()}", callback_data=f"vender_{moneda}")],[InlineKeyboardButton("💰 Total", callback_data="todo")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 BTC", callback_data="ver_btc"), InlineKeyboardButton("🔴 BTC", callback_data="vender_btc")],[InlineKeyboardButton("🟢 ETH", callback_data="ver_eth"), InlineKeyboardButton("🔴 ETH", callback_data="vender_eth")],[InlineKeyboardButton("🟢 XRP", callback_data="ver_xrp"), InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp")],[InlineKeyboardButton("💰 Balance", callback_data="todo")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE,'w') as f: f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ V19 ACTIVO - Monedas separadas\n/btc /eth /xrp /balance", reply_markup=get_buttons())

async def cmd_btc(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_one("btc"), reply_markup=get_buttons("btc"))
async def cmd_eth(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_one("eth"), reply_markup=get_buttons("eth"))
async def cmd_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_one("xrp"), reply_markup=get_buttons("xrp"))
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_all(), reply_markup=get_buttons())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    bal = load_bal(); precios = get_prices()
    if not precios:
        await q.edit_message_text("Actualizando...", reply_markup=get_buttons()); return
    data = q.data
    if data.startswith("ver_"):
        m = data.split("_")[1]
        await q.edit_message_text(fmt_one(m), reply_markup=get_buttons(m)); return
    if data == "todo":
        await q.edit_message_text(fmt_all(), reply_markup=get_buttons()); return
    accion, moneda = data.split("_")
    precio = precios[moneda][0]
    if accion == "comprar":
        cant = (50*(1-COMISION))/precio; bal[moneda]+=cant; bal[f"p_{moneda}"]=precio; save_bal(bal)
        await q.edit_message_text(f"✅ COMPRA {moneda.upper()}\n\n"+fmt_one(moneda), reply_markup=get_buttons(moneda))
    else:
        if bal[moneda]<=0:
            await q.answer(f"No tienes {moneda.upper()}"); return
        usd = bal[moneda]*precio*(1-COMISION); bal['usd']+=usd; bal[moneda]=0; save_bal(bal)
        await q.edit_message_text(f"✅ VENTA {moneda.upper()} ${usd:.2f}\n\n"+fmt_all(), reply_markup=get_buttons())

async def alerta_inteligente(context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_ID_FILE,'r') as f: cid = f.read().strip()
        if not cid: return
        precios = get_prices()
        if not precios: return
        bal = load_bal()
        for moneda in ["btc","eth","xrp"]:
            precio, cambio = precios[moneda]
            if cambio <= -2.0:
                await context.bot.send_message(chat_id=int(cid), text=f"🟢 COMPRA {moneda.upper()}! {cambio:.2f}% ${precio:,.2f}", reply_markup=get_buttons(moneda))
            if bal[moneda]>0:
                p_compra = bal.get(f"p_{moneda}",0)
                if p_compra>0:
                    gan = (precio - p_compra)/p_compra*100 - 1.56
                    if gan >= 2.0:
                        await context.bot.send_message(chat_id=int(cid), text=f"🔴 VENDE {moneda.upper()}! +{gan:.2f}% ${precio:,.2f}", reply_markup=get_buttons(moneda))
    except Exception as e:
        print(f"Error alerta: {e}", flush=True)

def main():
    threading.Thread(target=run_web, daemon=True).start()
    print("Iniciando bot...", flush=True)
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("btc", cmd_btc))
    application.add_handler(CommandHandler("eth", cmd_eth))
    application.add_handler(CommandHandler("xrp", cmd_xrp))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CallbackQueryHandler(buttons))
    application.job_queue.run_repeating(alerta_inteligente, interval=300, first=30)
    print("Bot polling iniciado", flush=True)
    application.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
