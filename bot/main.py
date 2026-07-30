import os, asyncio, requests, json
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
BALANCE_FILE = "/tmp/demo_balance.json"
INIT = 1000.0
CHAT_ID = 8976512826  # Tu cuenta nueva Rub E

def get_prices():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd", timeout=10)
        j = r.json()
        return j['bitcoin']['usd'], j['ethereum']['usd'], j['ripple']['usd']
    except:
        return 68000, 3500, 0.6

def get_balance():
    try:
        with open(BALANCE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"usd": INIT, "btc": 0}

def save_balance(b):
    with open(BALANCE_FILE, 'w') as f:
        json.dump(b, f)

def format_msg():
    btc, eth, xrp = get_prices()
    bal = get_balance()
    total = bal["usd"] + bal["btc"]*btc
    return f"⏰ *ALERTA 1 HORA - BOT Vicente*\n\nBTC: ${btc:,.2f}\nETH: ${eth:,.2f}\nXRP: ${xrp:.4f}\n\n💰 Balance: ${total:,.2f} USD\n\n¿Qué quieres hacer?"

# Esta es la función que te avisa cada hora
async def alerta_hora(context: ContextTypes.DEFAULT_TYPE):
    botones = [
        [InlineKeyboardButton("🟢 COMPRAR BTC", callback_data='comprar'),
         InlineKeyboardButton("🔴 VENDER BTC", callback_data='vender')],
        [InlineKeyboardButton("💰 Ver Precio Ahora", callback_data='precio')]
    ]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=format_msg(),
        reply_markup=InlineKeyboardMarkup(botones),
        parse_mode='Markdown'
    )

async def handle_message(update, context):
    text = update.message.text.lower()
    if "precio" in text or "price" in text or "/start" in text:
        botones = [
            [InlineKeyboardButton("🟢 COMPRAR", callback_data='comprar'),
             InlineKeyboardButton("🔴 VENDER", callback_data='vender')]
        ]
        await update.message.reply_text(format_msg(), reply_markup=InlineKeyboardMarkup(botones), parse_mode='Markdown')

async def handle_buttons(update, context):
    query = update.callback_query
    await query.answer()
    btc, eth, xrp = get_prices()
    bal = get_balance()
    
    if query.data == 'comprar':
        if bal["usd"] >= 100:
            bal["usd"] -= 100
            bal["btc"] += 100/btc
            save_balance(bal)
            await query.edit_message_text(f"✅ COMPRASTE $100 de BTC a ${btc:,.2f}\n\n{format_msg()}", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ No tienes suficiente USD")
    elif query.data == 'vender':
        if bal["btc"] > 0:
            bal["usd"] += bal["btc"]*btc
            bal["btc"] = 0
            save_balance(bal)
            await query.edit_message_text(f"✅ VENDISTE todo a ${btc:,.2f}\n\n{format_msg()}", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ No tienes BTC para vender")
    else:
        await query.edit_message_text(format_msg(), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 COMPRAR", callback_data='comprar'),
             InlineKeyboardButton("🔴 VENDER", callback_data='vender')]
        ]), parse_mode='Markdown')

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    
    # AQUÍ ESTÁ LA CLAVE: Avisa cada 3600 segundos = 1 hora
    app.job_queue.run_repeating(alerta_hora, interval=3600, first=10)
    
    print(f"Bot iniciado - Avisos cada 1 hora a {CHAT_ID}")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
