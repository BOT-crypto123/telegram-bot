import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Hola Rub! BOT DEMO ACTIVO\n"
        "💰 Balance: $1000 (demo)\n"
        "Escribe: precio, balance, /start"
    )

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 BTC: $68,432 (demo)\n"
        "📊 Balance: $1000\n"
        "📈 Ganancia hoy: +$23.50 (demo)\n"
        "✅ Bot funcionando perfecto!"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.lower()
    if "precio" in txt or "btc" in txt:
        await precio(update, context)
    elif "balance" in txt or "saldo" in txt:
        await update.message.reply_text("💰 Tu balance demo: $1000")
    else:
        await start(update, context)

print("BOT DEMO INICIADO - $1000")
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_polling()
