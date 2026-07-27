import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

async def start(u,c):
    await u.message.reply_text(f"Hola {u.effective_user.first_name}! Bot listo")

async def help_cmd(u,c):
    await u.message.reply_text("/start /help /echo /chatid")

async def echo_cmd(u,c):
    await u.message.reply_text(" ".join(c.args) or "Escribe algo")

async def chatid(u,c):
    await u.message.reply_text(f"Tu chat ID: {u.effective_chat.id}")

async def echo_text(u,c):
    await u.message.reply_text(u.message.text)

def main():
    token=os.getenv("BOT_TOKEN")
    app=ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help_cmd))
    app.add_handler(CommandHandler("echo",echo_cmd))
    app.add_handler(CommandHandler("chatid",chatid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text))
    print("Bot iniciado...")
    app.run_polling()

if __name__=="__main__":
    main()
