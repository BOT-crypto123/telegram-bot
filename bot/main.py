import os, requests, threading, time, asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_FILE = "/tmp/chat_id.txt"
XRP_CANT = 555.55
XRP_COMPRA = 0.60
COMISION_TOTAL = 0.0156

def get_market():
    # 1. Intenta Binance (precio + % 24h)
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]", timeout=8).json()
        if isinstance(r, list):
            d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
            return {"BTC": d['BTCUSDT'], "ETH": d['ETHUSDT'], "XRP": d['XRPUSDT']}
    except: pass

    # 2. CoinGecko (precio + % 24h) - este Render SI lo deja
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,ripple&price_change_percentage=24h"
        r = requests.get(url, timeout=10).json()
        m = {x['id']:(float(x['current_price']), float(x['price_change_percentage_24h'] or 0)) for x in r}
        return {"BTC": m['bitcoin'], "ETH": m['ethereum'], "XRP": m['ripple']}
    except Exception as e:
        print(f"Fallo coingecko: {e}")

    # 3. Kraken solo precio
    try:
        r = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCUSD,ETHUSD,XRPUSD", timeout=8).json()["result"]
        return {
            "BTC": (float(r["XXBTZUSD"]["c"][0]), 0),
            "ETH": (float(r["XETHZUSD"]["c"][0]), 0),
            "XRP": (float(r["XXRPZUSD"]["c"][0]), 0)
        }
    except:
        return None

def texto_balance():
    m = get_market()
    if not m: return "Error precios, intenta /balance de nuevo"
    xrp_p = m["XRP"][0]
    xrp_v = XRP_CANT * xrp_p
    gan = xrp_v - (XRP_CANT*XRP_COMPRA)
    porc = ((xrp_p - XRP_COMPRA)/XRP_COMPRA*100)
    return f"💰 BALANCE V23.1 PRO\n\n📦 {XRP_CANT} XRP\n💵 Valor: ${xrp_v:.2f}\n🎯 Compra: ${XRP_COMPRA}\n📊 Gan: {porc:+.2f}% (${gan:.2f})\n\nBTC: ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)\nETH: ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%)\nXRP: ${m['XRP'][0]:.4f} ({m['XRP'][1]:+.2f}%)"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Comprar XRP", callback_data="t"), InlineKeyboardButton("🔴 Vender XRP", callback_data="t")],
        [InlineKeyboardButton("💰 Ver Todo", callback_data="t")]
    ])

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    except: pass
    await u.message.reply_text(texto_balance() + "\n\n✅ Alertas cada 5min\nSolo -2% compra / +2% neto venta", reply_markup=menu())

async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())

async def cmd_btc(u:Update,c:ContextTypes.DEFAULT_TYPE): m=get_market(); await u.message.reply_text(f"BTC ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)" if m else "Error", reply_markup=menu())
async def cmd_eth(u:Update,c:ContextTypes.DEFAULT_TYPE): m=get_market(); await u.message.reply_text(f"ETH ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%)" if m else "Error", reply_markup=menu())
async def cmd_xrp(u:Update,c:ContextTypes.DEFAULT_TYPE): m=get_market(); await u.message.reply_text(f"XRP ${m['XRP'][0]:.4f} ({m['XRP'][1]:+.2f}%)" if m else "Error", reply_markup=menu())
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); await q.edit_message_text(texto_balance(), reply_markup=menu())

async def revisar_mercado(app):
    while True:
        await asyncio.sleep(300)
        try:
            m = get_market()
            if not m: continue
            try:
                with open(CHAT_FILE,'r') as f: chat_id=f.read().strip()
            except: continue
            if not chat_id: continue
            xrp_price, xrp_change = m["XRP"]
            if xrp_change <= -2.0:
                await app.bot.send_message(chat_id=int(chat_id), text=f"🟢 COMPRA XRP\n📉 Cayó {xrp_change:.2f}% 24h\nPrecio: ${xrp_price:.4f}", reply_markup=menu())
            if XRP_CANT>0:
                gan_neta = ((xrp_price-XRP_COMPRA)/XRP_COMPRA*100) - (COMISION_TOTAL*100)
                if gan_neta >= 2.0:
                    await app.bot.send_message(chat_id=int(chat_id), text=f"🔴 VENDE XRP\n✅ +{gan_neta:.2f}% NETO\nPrecio: ${xrp_price:.4f}\nValor: ${XRP_CANT*xrp_price:.2f}", reply_markup=menu())
            for coin in ["BTC","ETH"]:
                price, change = m[coin]
                if change <= -2.0:
                    await app.bot.send_message(chat_id=int(chat_id), text=f"🟢 COMPRA {coin}\n📉 Cayó {change:.2f}% 24h\nPrecio: ${price:,.2f}", reply_markup=menu())
        except Exception as e:
            print(f"Error alerta: {e}")

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"Bot V23.1 OK")
    def log_message(self,*a): pass
def run_web(): HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web,daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("balance",bal))
    app.add_handler(CommandHandler("btc",cmd_btc))
    app.add_handler(CommandHandler("eth",cmd_eth))
    app.add_handler(CommandHandler("xrp",cmd_xrp))
    app.add_handler(CallbackQueryHandler(btn))
    loop = asyncio.new_event_loop()
    def start_loop():
        asyncio.set_event_loop(loop)
        loop.create_task(revisar_mercado(app))
        loop.run_forever()
    threading.Thread(target=start_loop,daemon=True).start()
    print("Bot V23.1 listo")
    app.run_polling(drop_pending_updates=True)
