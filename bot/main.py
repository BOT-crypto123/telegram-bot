import os, requests, threading, asyncio, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_FILE = "/tmp/chat_id.txt"
HOLD_FILE = "/tmp/holdings_v25.json"
CAPITAL_MXN = 1000.0
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_usd_mxn():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=8).json()
        return float(r["rates"]["MXN"])
    except: return 18.5

def get_market():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, headers=HEADERS, timeout=12).json()
        return {
            "BTC": (float(r["bitcoin"]["usd"]), float(r["bitcoin"].get("usd_24h_change",0)or 0)),
            "ETH": (float(r["ethereum"]["usd"]), float(r["ethereum"].get("usd_24h_change",0)or 0)),
            "XRP": (float(r["ripple"]["usd"]), float(r["ripple"].get("usd_24h_change",0)or 0))
        }
    except: return None

def load_holdings():
    if os.path.exists(HOLD_FILE):
        try:
            with open(HOLD_FILE,'r') as f: return json.load(f)
        except: pass
    # Crear primera vez: divide 1000 en 3
    usd_mxn = get_usd_mxn()
    m = get_market()
    if not m: return None
    por_mxn = CAPITAL_MXN / 3.0
    h = {
        "efectivo_mxn": 0.0,
        "BTC": {"cant": (por_mxn/usd_mxn)/m["BTC"][0]},
        "ETH": {"cant": (por_mxn/usd_mxn)/m["ETH"][0]},
        "XRP": {"cant": (por_mxn/usd_mxn)/m["XRP"][0]},
    }
    save_holdings(h)
    return h

def save_holdings(h):
    with open(HOLD_FILE,'w') as f: json.dump(h,f)

def texto_balance():
    m = get_market(); h = load_holdings()
    if not m or not h: return "Cargando mercado..."
    usd_mxn = get_usd_mxn()
    total = h.get("efectivo_mxn",0)
    txt = f"💰 DEMO TRADING ${CAPITAL_MXN:.0f} MXN\n💱 USD/MXN: ${usd_mxn:.2f}\n💵 Efectivo: ${h.get('efectivo_mxn',0):.2f} MXN\n\n"
    for coin in ["BTC","ETH","XRP"]:
        cant = h[coin]["cant"]
        precio = m[coin][0]
        valor_usd = cant * precio
        valor_mxn = valor_usd * usd_mxn
        total += valor_mxn
        txt += f"{coin}: {cant:.8f}\n Valor: ${valor_mxn:.2f} MXN ({m[coin][1]:+.2f}%)\n"
    gan = total - CAPITAL_MXN
    txt += f"\n💵 TOTAL: ${total:.2f} MXN\n📊 Gan: {gan/CAPITAL_MXN*100:+.2f}% (${gan:+.2f})"
    txt += f"\n\nUsa: /comprar BTC 100\n /vender XRP 50"
    return txt

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Actualizar", callback_data="t")]])

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    load_holdings()
    await u.message.reply_text(texto_balance(), reply_markup=menu())

async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())

async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); await q.edit_message_text(texto_balance(), reply_markup=menu())

async def comprar(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin = c.args[0].upper()
        monto_mxn = float(c.args[1])
        if coin not in ["BTC","ETH","XRP"]: raise Exception()
        m = get_market(); h = load_holdings(); usd_mxn = get_usd_mxn()
        if h["efectivo_mxn"] < monto_mxn and h["efectivo_mxn"]!= 0 and sum([h[x]["cant"] for x in ["BTC","ETH","XRP"]])>0:
            # Si ya gastaste todo, permitimos comprar aunque efectivo sea 0 reseteando? No, pide vender primero
            if h["efectivo_mxn"] < monto_mxn:
                await u.message.reply_text(f"❌ No tienes suficiente efectivo. Tienes ${h['efectivo_mxn']:.2f} MXN. Vende algo primero: /vender {coin} 50")
                return
        precio = m[coin][0]
        cant_comprada = (monto_mxn / usd_mxn) / precio
        h[coin]["cant"] += cant_comprada
        h["efectivo_mxn"] -= monto_mxn
        if h["efectivo_mxn"] < 0: h["efectivo_mxn"] = 0 # primera compra inicial tenia 0
        save_holdings(h)
        await u.message.reply_text(f"✅ COMPRASTE {coin}\n${monto_mxn:.2f} MXN = {cant_comprada:.8f} {coin}\nPrecio: ${precio}", reply_markup=menu())
    except:
        await u.message.reply_text("Uso: /comprar BTC 100\nEjemplo: /comprar XRP 100")

async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin = c.args[0].upper()
        monto_mxn = float(c.args[1])
        m = get_market(); h = load_holdings(); usd_mxn = get_usd_mxn()
        precio = m[coin][0]
        cant_a_vender = (monto_mxn / usd_mxn) / precio
        if h[coin]["cant"] < cant_a_vender:
            await u.message.reply_text(f"❌ No tienes suficiente {coin}. Tienes {h[coin]['cant']:.8f}")
            return
        h[coin]["cant"] -= cant_a_vender
        h["efectivo_mxn"] += monto_mxn
        save_holdings(h)
        await u.message.reply_text(f"✅ VENDISTE {coin}\n${monto_mxn:.2f} MXN = {cant_a_vender:.8f} {coin}", reply_markup=menu())
    except:
        await u.message.reply_text("Uso: /vender BTC 100\nEjemplo: /vender XRP 50")

async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    load_holdings()
    await u.message.reply_text("🔄 Demo reseteado a $1000 dividido en 3\n" + texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V25 OK")
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
    print("Bot V25 Trading Demo listo")
    app.run_polling(drop_pending_updates=True)
