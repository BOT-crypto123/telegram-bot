import os, json, threading
from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_FILE = "/tmp/chat_id.txt"
BALANCE_FILE = "/tmp/balance.json"
INIT = 1000.0
COMISION = 0.0078

app = Flask(__name__)
@app.route('/')
def h(): return "V16 SMART ALERTS LIVE"
@app.route('/health')
def hl(): return "OK"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

def get_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=15).json()
        return {
            "btc": (r['bitcoin']['usd'], r['bitcoin'].get('usd_24h_change',0)),
            "eth": (r['ethereum']['usd'], r['ethereum'].get('usd_24h_change',0)),
            "xrp": (r['ripple']['usd'], r['ripple'].get('usd_24h_change',0))
        }
    except Exception as e:
        print(f"Error precios: {e}")
        return None

def load_bal():
    try:
        with open(BALANCE_FILE,'r') as f: return json.load(f)
    except:
        return {"btc": (INIT/3)/68000, "eth": (INIT/3)/3400, "xrp": (INIT/3)/0.6, "usd":0, "init":INIT, "p_btc":68000,"p_eth":3400,"p_xrp":0.6}

def save_bal(b):
    with open(BALANCE_FILE,'w') as f: json.dump(b,f)

def format_msg():
    precios = get_prices()
    if not precios:
        return "⚠️ CoinGecko ocupado, intenta /balance en 10 seg"
    bal = load_bal()
    btc_p, btc_c = precios['btc']
    eth_p, eth_c = precios['eth']
    xrp_p, xrp_c = precios['xrp']
    total = bal['btc']*btc_p + bal['eth']*eth_p + bal['xrp']*xrp_p + bal['usd']
    gan = total - bal['init']
    pct = gan/bal['init']*100
    return (f"📊 DEMO $1000 - BTC ETH XRP REAL\n\n"
            f"🟢 BTC: ${btc_p:,.2f} ({btc_c:+.2f}%)\n{bal['btc']:.6f} = ${bal['btc']*btc_p:.2f}\n\n"
            f"🟢 ETH: ${eth_p:,.2f} ({eth_c:+.2f}%)\n{bal['eth']:.6f} = ${bal['eth']*eth_p:.2f}\n\n"
            f"🟢 XRP: ${xrp_p:.4f} ({xrp_c:+.2f}%)\n{bal['xrp']:.2f} = ${bal['xrp']*xrp_p:.2f}\n\n"
            f"💰 Total: ${total:.2f}\n📈 Ganancia: ${gan:+.2f} ({pct:+.2f}%)")

def get_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 BTC", callback_data="comprar_btc"), InlineKeyboardButton("🔴 BTC", callback_data="vender_btc")],
        [InlineKeyboardButton("🟢 ETH", callback_data="comprar_eth"), InlineKeyboardButton("🔴 ETH", callback_data="vender_eth")],
        [InlineKeyboardButton("🟢 XRP", callback_data="comprar_xrp"), InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp")],
        [InlineKeyboardButton("💰 Actualizar", callback_data="precio")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE,'w') as f: f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ V16 SMART ALERTS LIVE\nSolo aviso cuando hay oportunidad real", reply_markup=get_buttons())
    await update.message.reply_text(format_msg(), reply_markup=get_buttons())

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_msg(), reply_markup=get_buttons())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bal = load_bal()
    precios = get_prices()
    if not precios:
        await q.edit_message_text("Error precios, intenta en 10 seg", reply_markup=get_buttons())
        return
    if q.data == "precio":
        await q.edit_message_text(format_msg(), reply_markup=get_buttons())
        return
    accion, moneda = q.data.split("_")
    precio = precios[moneda][0]
    if accion == "comprar":
        cant = (50*(1-COMISION))/precio
        bal[moneda] += cant
        bal[f"p_{moneda}"] = precio
        save_bal(bal)
        await q.edit_message_text(f"✅ COMPRA {moneda.upper()} {cant:.6f} a ${precio:,.2f}\n\n"+format_msg(), reply_markup=get_buttons())
    else:
        if bal[moneda] <=0:
            await q.answer(f"No tienes {moneda.upper()}")
            return
        usd = bal[moneda]*precio*(1-COMISION)
        bal['usd']+=usd
        bal[moneda]=0
        save_bal(bal)
        await q.edit_message_text(f"✅ VENTA {moneda.upper()} ${usd:.2f}\n\n"+format_msg(), reply_markup=get_buttons())

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
                await context.bot.send_message(chat_id=int(cid), text=f"🟢 OPORTUNIDAD COMPRA {moneda.upper()}!\n📉 Cayó {cambio:.2f}%\n💰 ${precio:,.4f}", reply_markup=get_buttons())
            if bal[moneda] > 0:
                p_compra = bal.get(f"p_{moneda}",0)
                if p_compra>0:
                    gan = (precio - p_compra)/p_compra*100
                    gan_neta = gan - (COMISION*2*100)
                    if gan_neta >= 2.0:
                        await context.bot.send_message(chat_id=int(cid), text=f"🔴 OPORTUNIDAD VENTA {moneda.upper()}!\n📈 ${precio:,.4f}\n✅ Ganancia NETA: {gan_neta:.2f}%", reply_markup=get_buttons())
    except Exception as e:
        print(f"Error alerta: {e}")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CallbackQueryHandler(buttons))
    application.job_queue.run_repeating(alerta_inteligente, interval=300, first=30)
    application.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
