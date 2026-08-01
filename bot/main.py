import os, requests, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
XRP_CANT = 555.55
XRP_COMPRA = 0.60

def get_prices():
    try:
        url="https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd"
        r=requests.get(url,timeout=15).json()
        return {"BTC":r["bitcoin"]["usd"],"ETH":r["ethereum"]["usd"],"XRP":r["ripple"]["usd"]}
    except Exception as e:
        print(f"Error coingecko: {e}")
        return None

def texto_balance():
    p=get_prices()
    if not p: return "Error precios, intenta /balance de nuevo"
    xrp_v = XRP_CANT * p["XRP"]
    gan = xrp_v - (XRP_CANT*XRP_COMPRA)
    porc = ((p["XRP"]-XRP_COMPRA)/XRP_COMPRA*100)
    return f"💰 BALANCE V22.4 LIVE\n\n📦 {XRP_CANT} XRP\n💵 Valor: ${xrp_v:.2f}\n🎯 Compra: ${XRP_COMPRA}\n📊 Gan: {porc:+.2f}% (${gan:.2f})\n\nBTC: ${p['BTC']:,.2f}\nETH: ${p['ETH']:,.2f}\nXRP: ${p['XRP']:.4f}"

def menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Comprar",callback_data="c"),InlineKeyboardButton("🔴 Vender",callback_data="v")],[InlineKeyboardButton("💰 Ver Todo",callback_data="t")]])

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE): await u.message.reply_text(texto_balance(),reply_markup=menu())
async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE): await u.message.reply_text(texto_balance(),reply_markup=menu())
async def btc(u:Update,c:ContextTypes.DEFAULT_TYPE): 
    p=get_prices(); await u.message.reply_text(f"BTC ${p['BTC']:,.2f}" if p else "Error")
async def eth(u:Update,c:ContextTypes.DEFAULT_TYPE): 
    p=get_prices(); await u.message.reply_text(f"ETH ${p['ETH']:,.2f}" if p else "Error")
async def xrp(u:Update,c:ContextTypes.DEFAULT_TYPE): 
    p=get_prices(); await u.message.reply_text(f"XRP ${p['XRP']:.4f}" if p else "Error")
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer()
    if q.data=="t": await q.edit_message_text(texto_balance(),reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"Bot V22.4 OK")
    def log_message(self,*a): pass

def run_web():
    HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web,daemon=True).start()
    print("Iniciando Bot V22.4...")
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("balance",bal))
    app.add_handler(CommandHandler("btc",btc))
    app.add_handler(CommandHandler("eth",eth))
    app.add_handler(CommandHandler("xrp",xrp))
    app.add_handler(CallbackQueryHandler(btn))
    print("Bot V22.4 listo - polling")
    # Esto arregla el Conflict
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
