import os, requests, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
XRP_CANT = 555.55
XRP_COMPRA = 0.60

def get_prices():
    # 1- Intento CoinGecko
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd",timeout=8).json()
        if "bitcoin" in r:
            return {"BTC":r["bitcoin"]["usd"],"ETH":r["ethereum"]["usd"],"XRP":r["ripple"]["usd"]}
    except: pass
    # 2- Intento Kraken (este casi nunca bloquea Render)
    try:
        r=requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCUSD,ETHUSD,XRPUSD",timeout=8).json()
        d=r["result"]
        # Kraken keys: XXBTZUSD, XETHZUSD, XXRPZUSD
        btc=float(d["XXBTZUSD"]["c"][0])
        eth=float(d["XETHZUSD"]["c"][0])
        xrp=float(d["XXRPZUSD"]["c"][0])
        return {"BTC":btc,"ETH":eth,"XRP":xrp}
    except Exception as e:
        print(f"Error Kraken: {e}")
    # 3- Intento Coinbase
    try:
        b=requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=8).json()
        e=requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot",timeout=8).json()
        x=requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot",timeout=8).json()
        return {"BTC":float(b["data"]["amount"]),"ETH":float(e["data"]["amount"]),"XRP":float(x["data"]["amount"])}
    except: pass
    return None

def texto_balance():
    p=get_prices()
    if not p: 
        print("FALLO TOTAL PRECIOS")
        return "Error precios, intenta /balance de nuevo"
    xrp_v = XRP_CANT * p["XRP"]
    gan = xrp_v - (XRP_CANT*XRP_COMPRA)
    porc = ((p["XRP"]-XRP_COMPRA)/XRP_COMPRA*100)
    return f"💰 BALANCE V22.5 LIVE\n\n📦 {XRP_CANT} XRP\n💵 Valor: ${xrp_v:.2f}\n🎯 Compra: ${XRP_COMPRA}\n📊 Gan: {porc:+.2f}% (${gan:.2f})\n\nBTC: ${p['BTC']:,.2f}\nETH: ${p['ETH']:,.2f}\nXRP: ${p['XRP']:.4f}"

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Comprar XRP",callback_data="t"),InlineKeyboardButton("🔴 Vender XRP",callback_data="t")],[InlineKeyboardButton("💰 Ver Todo",callback_data="t")]])

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE): await u.message.reply_text(texto_balance(),reply_markup=menu())
async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE): await u.message.reply_text(texto_balance(),reply_markup=menu())
async def btc(u:Update,c:ContextTypes.DEFAULT_TYPE): p=get_prices(); await u.message.reply_text(f"BTC ${p['BTC']:,.2f}" if p else "Error")
async def eth(u:Update,c:ContextTypes.DEFAULT_TYPE): p=get_prices(); await u.message.reply_text(f"ETH ${p['ETH']:,.2f}" if p else "Error")
async def xrp(u:Update,c:ContextTypes.DEFAULT_TYPE): p=get_prices(); await u.message.reply_text(f"XRP ${p['XRP']:.4f}" if p else "Error")
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE): q=u.callback_query; await q.answer(); await q.edit_message_text(texto_balance(),reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"Bot V22.5 OK")
    def log_message(self,*a): pass
def run_web(): HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

def run_web2():
    port=int(os.environ.get("PORT",10000))
    HTTPServer(("0.0.0.0",port),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web2,daemon=True).start()
    print("Iniciando Bot V22.5...")
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("balance",bal))
    app.add_handler(CommandHandler("btc",btc))
    app.add_handler(CommandHandler("eth",eth))
    app.add_handler(CommandHandler("xrp",xrp))
    app.add_handler(CallbackQueryHandler(btn))
    print("Bot V22.5 listo - Kraken fallback")
    app.run_polling(drop_pending_updates=True)
