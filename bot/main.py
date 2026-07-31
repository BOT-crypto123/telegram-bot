import os, time, requests, telebot, threading
from flask import Flask
TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
bot=telebot.TeleBot(TOKEN, threaded=False)
def get_btc_price():
    try:
        r=requests.get("https://api.coindesk.com/v1/bpi/currentprice/USD.json",timeout=10).json()
        return float(r["bpi"]["USD"]["rate_float"])
    except:
        return 115000.0
@bot.message_handler(commands=['start','balance'])
def h(m):
    p=get_btc_price()
    v=0.0085*p
    bot.reply_to(m,f"📊 *BTC VICENTE*\n💰 BTC: ${p:,.2f}\n💼 Valor: ${v:,.2f}\n✅ BOT VIVO",parse_mode="Markdown")
app=Flask(__name__)
@app.route('/')
def home(): return "OK",200
threading.Thread(target=lambda: app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000))),daemon=True).start()
bot.delete_webhook(drop_pending_updates=True)
bot.infinity_polling()
