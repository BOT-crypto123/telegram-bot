import os, json, requests, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = 8976512826  # Tu cuenta nueva Rub E
BALANCE_FILE = "/tmp/demo_balance.json"
INIT = 1000.0

def get_prices():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd", timeout=10).json()
        return r['bitcoin']['usd'], r['ethereum']['usd'], r['ripple']['usd']
    except:
        return 68000.0, 3400.0, 0.6

def load_bal():
    try:
        with open(BALANCE_FILE,'r') as f: return json.load(f)
    except:
        return {"usd": INIT/3, "btc": (INIT/3)/68000, "eth": (INIT/3)/3400, "xrp": (INIT/3)/0.6, "init": INIT}

def save_bal(b):
    with open(BALANCE_FILE,'w') as f: json.dump(b,f)

def format_msg():
    btc_p, eth_p, xrp_p = get_prices()
    bal = load_bal()
    btc_v = bal['btc']*btc_p
    eth_v = bal['eth']*eth_p
    xrp_v = bal['xrp']*xrp_p
    total = bal['usd'] + btc_v + eth_v + xrp_v
    ganancia = total - bal['init']
    pct = (ganancia / bal['init'])*100

    return f"""📊 DEMO $1000 - GANANCIA REAL (BTC ETH XRP)

🟢 BTC: ${btc_p:,.4f}
{bal['btc']:.4f} = ${btc_v:.2f}

🟢 ETH: ${eth_p:,.4f}
{bal['eth']:.4f} = ${eth_v:.2f}

🟢 XRP: ${xrp_p:.4f}
{bal['xrp']:.4f} = ${xrp_v:.2f}

💰 Total: ${total:.2f}
📈 Ganancia REAL: ${ganancia:+.2f} ({pct:+.2f}%)

Demo - no cobrable pero precio real"""

def get_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 COMPRAR", callback_data="comprar"), InlineKeyboardButton("🔴 VENDER", callback_data="vender")],
        [InlineKeyboardButton("💰 Precio Ahora", callback_data="precio")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot BTC+ETH+XRP Demo REAL activo\nEscribe 'precio'", reply_markup=get_buttons())

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.lower()
    if "precio" in txt or "/start" in txt or "price" in txt:
        await update.message.reply_text(format_msg(), reply_markup=get_buttons())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "precio":
        await query.edit_message_text(format_msg(), reply_markup=get_buttons())
    else:
        await query.edit_message_text(f"{format_msg()}\n\n👉 Opción: {query.data.upper()}\n\nEscribe: 'comprar btc 100' o 'vender eth 50'", reply_markup=get_buttons())

# --- ESTA ES LA ALERTA CADA 1 HORA ---
async def alerta_hora(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text=f"⏰ ALERTA 1 HORA - BTC Vicente\n\n{format_msg()}", reply_markup=get_buttons())

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, precio))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    # Avisa cada 3600 segundos = 1 hora, primer aviso en 10 segundos
    app.job_queue.run_repeating(alerta_hora, interval=3600, first=10)
    
    print(f"Bot iniciado - Avisos cada 1 hora a {CHAT_ID}")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
