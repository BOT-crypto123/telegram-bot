import os, requests, threading, time, asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_FILE = "/tmp/chat_id.txt"
# TUS DATOS
XRP_CANT = 555.55
XRP_COMPRA = 0.60
COMISION_TOTAL = 0.0156 # 0.78 + 0.78

# --- PRECIOS CON FALLBACK ---
def get_market():
    # Intenta Binance para tener el % de 24h
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]", timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        return {"BTC": d['BTCUSDT'], "ETH": d['ETHUSDT'], "XRP": d['XRPUSDT']}
    except:
        pass
    # Fallback Kraken + CoinGecko sin % (usa 0)
    try:
        r = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCUSD,ETHUSD,XRPUSD", timeout=10).json()
        res = r["result"]
        return {
            "BTC": (float(res["XXBTZUSD"]["c"][0]), 0),
            "ETH": (float(res["XETHZUSD"]["c"][0]), 0),
            "XRP": (float(res["XXRPZUSD"]["c"][0]), 0)
        }
    except:
        return None

def get_prices_simple():
    m = get_market()
    if not m: return None
    return {"BTC": m["BTC"][0], "ETH": m["ETH"][0], "XRP": m["XRP"][0]}

def texto_balance():
    m = get_market()
    if not m: return "Error precios, intenta /balance de nuevo"
    xrp_p = m["XRP"][0]
    xrp_v = XRP_CANT * xrp_p
    gan = xrp_v - (XRP_CANT*XRP_COMPRA)
    porc = ((xrp_p - XRP_COMPRA)/XRP_COMPRA*100)
    txt = f"💰 BALANCE V23 PRO\n\n📦 {XRP_CANT} XRP\n💵 Valor: ${xrp_v:.2f}\n🎯 Compra: ${XRP_COMPRA}\n📊 Gan: {porc:+.2f}% (${gan:.2f})\n\n"
    txt += f"BTC: ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)\nETH: ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%)\nXRP: ${m['XRP'][0]:.4f} ({m['XRP'][1]:+.2f}%)"
    return txt

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Comprar XRP", callback_data="c"), InlineKeyboardButton("🔴 Vender XRP", callback_data="v")],
        [InlineKeyboardButton("💰 Ver Todo", callback_data="t")]
    ])

# --- COMANDOS ---
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    except: pass
    await u.message.reply_text(texto_balance() + "\n\n✅ Alertas activas cada 5min\nSolo aviso si es -2% compra o +2% neto venta", reply_markup=menu())

async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())

async def cmd_btc(u:Update,c:ContextTypes.DEFAULT_TYPE):
    m=get_market()
    await u.message.reply_text(f"BTC ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)" if m else "Error", reply_markup=menu())
async def cmd_eth(u:Update,c:ContextTypes.DEFAULT_TYPE):
    m=get_market()
    await u.message.reply_text(f"ETH ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%)" if m else "Error", reply_markup=menu())
async def cmd_xrp(u:Update,c:ContextTypes.DEFAULT_TYPE):
    m=get_market()
    await u.message.reply_text(f"XRP ${m['XRP'][0]:.4f} ({m['XRP'][1]:+.2f}%)" if m else "Error", reply_markup=menu())
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer()
    await q.edit_message_text(texto_balance(), reply_markup=menu())

# --- CEREBRO DE ALERTAS CADA 5 MIN ---
async def revisar_mercado(app):
    while True:
        await asyncio.sleep(300) # 5 min
        try:
            m = get_market()
            if not m: continue
            try:
                with open(CHAT_FILE,'r') as f: chat_id = f.read().strip()
            except: continue
            if not chat_id: continue

            # LOGICA XRP - COMPRA -2%
            xrp_price, xrp_change = m["XRP"]
            if xrp_change <= -2.0:
                await app.bot.send_message(chat_id=int(chat_id), text=f"🟢 OPORTUNIDAD COMPRA XRP\n📉 Cayó {xrp_change:.2f}% en 24h\nPrecio: ${xrp_price:.4f}\nTu gan actual: {((xrp_price-XRP_COMPRA)/XRP_COMPRA*100):+.2f}%", reply_markup=menu())

            # LOGICA XRP - VENTA +2% NETO
            if XRP_CANT > 0:
                gan_neta = ((xrp_price - XRP_COMPRA)/XRP_COMPRA*100) - (COMISION_TOTAL*100)
                if gan_neta >= 2.0:
                    await app.bot.send_message(chat_id=int(chat_id), text=f"🔴 OPORTUNIDAD VENTA XRP\n✅ Ganancia NETA +{gan_neta:.2f}%\nPrecio: ${xrp_price:.4f}\nValor: ${XRP_CANT*xrp_price:.2f}\nGanancia: ${(XRP_CANT*xrp_price)-(XRP_CANT*XRP_COMPRA):.2f}", reply_markup=menu())

            # LOGICA BTC/ETH para comprar
            for coin in ["BTC","ETH"]:
                price, change = m[coin]
                if change <= -2.0:
                    await app.bot.send_message(chat_id=int(chat_id), text=f"🟢 OPORTUNIDAD COMPRA {coin}\n📉 Cayó {change:.2f}% en 24h\nPrecio: ${price:,.2f}", reply_markup=menu())

        except Exception as e:
            print(f"Error alerta: {e}")

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"Bot V23 PRO OK")
    def log_message(self,*a): pass
def run_web():
    HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web,daemon=True).start()
    print("Iniciando Bot V23 PRO...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", bal))
    app.add_handler(CommandHandler("btc", cmd_btc))
    app.add_handler(CommandHandler("eth", cmd_eth))
    app.add_handler(CommandHandler("xrp", cmd_xrp))
    app.add_handler(CallbackQueryHandler(btn))

    # Lanzar loop de alertas
    loop = asyncio.new_event_loop()
    def start_loop():
        asyncio.set_event_loop(loop)
        loop.create_task(revisar_mercado(app))
        loop.run_forever()
    threading.Thread(target=start_loop, daemon=True).start()

    print("Bot V23 listo - polling + alertas 5min")
    app.run_polling(drop_pending_updates=True)
