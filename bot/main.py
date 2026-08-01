import os, json, threading, time
print("=== V21.1 FIX VICENTE ===", flush=True)
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
def home(): return "V21.1 LIVE"
@app.route('/health')
def hl(): return "OK"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
def get_prices():
    global CACHE
    if time.time() - CACHE["t"] < 60 and CACHE["data"]:
        return CACHE["data"]
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]"
        r = requests.get(url, timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        data = {"btc": d['BTCUSDT'], "eth": d['ETHUSDT'], "xrp": d['XRPUSDT']}
        CACHE["t"] = time.time()
        CACHE["data"] = data
        return data
    except: pass
    try:
        g = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true", timeout=10).json()
        data = {"btc": (float(g['bitcoin']['usd']), float(g['bitcoin']['usd_24h_change'])), "eth": (float(g['ethereum']['usd']), float(g['ethereum']['usd_24h_change'])), "xrp": (float(g['ripple']['usd']), float(g['ripple']['usd_24h_change']))}
        CACHE["t"] = time.time()
        CACHE["data"] = data
        return data
    except: pass
    if CACHE["data"]:
        return CACHE["data"]
    return {"btc": (63450.12, 1.25), "eth": (3450.55, 0.89), "xrp": (0.62, 2.1)}
def load_bal():
    try:
        with open(BALANCE_FILE,'r') as f: return json.load(f)
    except:
        return {"btc": (INIT/3)/68000, "eth": (INIT/3)/3400, "xrp": (INIT/3)/0.6, "usd":0, "init":INIT, "p_btc":68000,"p_eth":3400,"p_xrp":0.6}
def save_bal(b):
    with open(BALANCE_FILE,'w') as f: json.dump(b,f)
def recuadro(moneda, precio, cambio, bal):
    qty = bal[moneda]
    valor = qty*precio
    p_compra = bal.get(f'p_{moneda}', precio)
    gan = ((precio - p_compra)/p_compra*100) if p_compra>0 else 0
    icono = "🟢" if cambio>=0 else "🔴"
    return f"┌─ {icono} {moneda.upper()} ──────────\n│ 💰 Precio: ${precio:,.4f}\n│ 📈 24h: {cambio:+.2f}%\n│ 📦 Tienes: {qty:.6f}\n│ 💵 Valor: ${valor:.2f}\n│ 🎯 Compra: ${p_compra:,.4f}\n│ 📊 Ganancia: {gan:+.2f}%\n└──────────────────"
def fmt_one(m):
    p = get_prices()
    price, change = p[m]
    bal = load_bal()
    return recuadro(m, price, change, bal)
def fmt_all():
    p = get_prices()
    bal = load_bal()
    total = bal['btc']*p['btc'][0] + bal['eth']*p['eth'][0] + bal['xrp']*p['xrp'][0] + bal['usd']
    pct_total = (total-INIT)/INIT*100
    texto = f"💼 BALANCE TOTAL: ${total:.2f} ({pct_total:+.2f}%)\n\n"
    texto += recuadro("btc", p['btc'][0], p['btc'][1], bal) + "\n\n"
    texto += recuadro("eth", p['eth'][0], p['eth'][1], bal) + "\n\n"
    texto += recuadro("xrp", p['xrp'][0], p['xrp'][1], bal)
    return texto
def get_buttons(m=None):
    if m:
        return InlineKeyboardMarkup([ [InlineKeyboardButton(f"🟢 Comprar {m.upper()}", callback_data=f"comprar_{m}"), InlineKeyboardButton(f"🔴 Vender {m.upper()}", callback_data=f"vender_{m}")], [InlineKeyboardButton("💰 Ver Todo", callback_data="todo")] ])
    return InlineKeyboardMarkup([ [InlineKeyboardButton("🟢 BTC", callback_data="ver_btc"), InlineKeyboardButton("🔴 BTC", callback_data="vender_btc")], [InlineKeyboardButton("🟢 ETH", callback_data="ver_eth"), InlineKeyboardButton("🔴 ETH", callback_data="vender_eth")], [InlineKeyboardButton("🟢 XRP", callback_data="ver_xrp"), InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp")], [InlineKeyboardButton("💰 Balance Total", callback_data="todo")] ])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE,'w') as f: f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ V21.1 RECUADROS LISTO\n/btc /eth /xrp /balance", reply_markup=get_buttons())
async def cmd_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_one("btc"), reply_markup=get_buttons("btc"))
async def cmd_eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_one("eth"), reply_markup=get_buttons("eth"))
async def cmd_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_one("xrp"), reply_markup=get_buttons("xrp"))
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(fmt_all(), reply_markup=get_buttons())
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bal = load_bal()
    precios = get_prices()
    data = q.data
    if data.startswith("ver_"):
        m = data.split("_")[1]
        await q.edit_message_text(fmt_one(m), reply_markup=get_buttons(m))
        return
    if data == "todo":
        await q.edit_message_text(fmt_all(), reply_markup=get_buttons())
        return
    accion, moneda = data.split("_")
    precio = precios[moneda][0]
    if accion == "comprar":
        cant = (50*(1-COMISION))/precio
        bal[moneda]+=cant
        bal[f"p_{moneda}"]=precio
        save_bal(bal)
        await q.edit_message_text(f"✅ COMPRA {moneda.upper()}\n\n"+fmt_one(moneda), reply_markup=get_buttons(moneda))
    else:
        if bal[moneda]<=0:
            await q.answer(f"No tienes {moneda.upper()}")
            return
        usd = bal[moneda]*precio*(1-COMISION)
        bal['usd']+=usd
        bal[moneda]=0
        save_bal(bal)
        await q.edit_message_text(f"✅ VENTA {moneda.upper()} ${usd:.2f}\n\n"+fmt_all(), reply_markup=get_buttons())
def main():
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=5)
    except: pass
    time.sleep(2)
    threading.Thread(target=run_web, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("btc", cmd_btc))
    application.add_handler(CommandHandler("eth", cmd_eth))
    application.add_handler(CommandHandler("xrp", cmd_xrp))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CallbackQueryHandler(buttons))
    print("V21.1 FIX LIVE", flush=True)
    application.run_polling(drop_pending_updates=True)
if __name__=="__main__":
    main()