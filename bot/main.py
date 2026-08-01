import os, requests, threading, asyncio, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_FILE = "/tmp/chat_id.txt"
HOLD_FILE = "/tmp/holdings_v25.json"
CAPITAL_MXN = 1000.0

def get_usd_mxn():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=8).json()
        return float(r["rates"]["MXN"])
    except: return 18.5

def get_market():
    try:
        # Binance es mucho más estable en Render
        data = {}
        for sym, name in [("BTCUSDT","BTC"), ("ETHUSDT","ETH"), ("XRPUSDT","XRP")]:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}", timeout=10).json()
            price = float(r["lastPrice"])
            change = float(r["priceChangePercent"])
            data[name] = (price, change)
        return data
    except Exception as e:
        print(f"Error market: {e}")
        return None

def load_holdings():
    if os.path.exists(HOLD_FILE):
        try:
            with open(HOLD_FILE,'r') as f: return json.load(f)
        except: pass
    usd_mxn = get_usd_mxn()
    m = get_market()
    if not m:
        # si falla mercado, crea con 0 para no quedarse en Cargando
        return {"efectivo_mxn":0.0, "BTC":{"cant":0.000285}, "ETH":{"cant":0.009}, "XRP":{"cant":17.2}}
    por_mxn = CAPITAL_MXN / 3.0
    h = {
        "efectivo_mxn": 0.0,
        "BTC": {"cant": (por_mxn/usd_mxn)/m["BTC"][0]},
        "ETH": {"cant": (por_mxn/usd_mxn)/m["ETH"][0]},
        "XRP": {"cant": (por_mxn/usd_mxn)/m["XRP"][0]},
    }
    with open(HOLD_FILE,'w') as f: json.dump(h,f)
    return h

def save_holdings(h):
    with open(HOLD_FILE,'w') as f: json.dump(h,f)

def texto_balance():
    m = get_market()
    h = load_holdings()
    if not m: return "⚠️ Mercado ocupado, toca Actualizar en 5s..."
    usd_mxn = get_usd_mxn()
    total = h.get("efectivo_mxn",0)
    txt = f"💰 DEMO TRADING ${CAPITAL_MXN:.0f} MXN\n💱 USD/MXN: ${usd_mxn:.2f}\n💵 Efectivo: ${h.get('efectivo_mxn',0):.2f} MXN\n\n"
    for coin in ["BTC","ETH","XRP"]:
        cant = h[coin]["cant"]
        precio = m[coin][0]
        valor_mxn = cant * precio * usd_mxn
        total += valor_mxn
        txt += f"{coin}: {cant:.8f}\n ${precio:.4f} ({m[coin][1]:+.2f}%) -> ${valor_mxn:.2f} MXN\n"
    gan = total - CAPITAL_MXN
    txt += f"\n💵 TOTAL: ${total:.2f} MXN\n📊 Gan: {gan/CAPITAL_MXN*100:+.2f}% (${gan:+.2f})"
    txt += f"\n\nCmd: /comprar BTC 100 | /vender XRP 50 | /reset"
    return txt

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Actualizar", callback_data="t")]])

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())
async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); await q.edit_message_text(texto_balance(), reply_markup=menu())
async def comprar(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin=c.args[0].upper(); monto=float(c.args[1])
        m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        if h["efectivo_mxn"] < monto and h["efectivo_mxn"] > 1:
            await u.message.reply_text(f"❌ Efectivo insuficiente: ${h['efectivo_mxn']:.2f}"); return
        cant = (monto/usd_mxn)/m[coin][0]
        h[coin]["cant"]+=cant
        h["efectivo_mxn"]-=monto
        if h["efectivo_mxn"]<0: h["efectivo_mxn"]=0
        save_holdings(h)
        await u.message.reply_text(f"✅ Compraste ${monto} de {coin} = {cant:.8f}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /comprar BTC 100")
async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin=c.args[0].upper(); monto=float(c.args[1])
        m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant = (monto/usd_mxn)/m[coin][0]
        if h[coin]["cant"] < cant:
            await u.message.reply_text(f"❌ Solo tienes {h[coin]['cant']:.8f} {coin}"); return
        h[coin]["cant"]-=cant; h["efectivo_mxn"]+=monto; save_holdings(h)
        await u.message.reply_text(f"✅ Vendiste ${monto} de {coin}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /vender XRP 100")
async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    await u.message.reply_text("🔄 Reseteado\n"+texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V25.1 OK")
    def log_message(self,*a): pass
def run_web(): HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web,daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("balance",bal))
    app.add_handler(CommandHandler("comprar",comprar))
    app.add_handler(CommandHandler("vender",vender))
    app.add_handler(CommandHandler("reset",reset))
    app.add_handler(CallbackQueryHandler(btn))
    print("Bot V25.1 Binance Fix listo")
    app.run_polling(drop_pending_updates=True)
