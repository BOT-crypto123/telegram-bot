import os, requests, threading, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
HOLD_FILE = "/tmp/holdings_v25.json"
CAPITAL_MXN = 1000.0

def get_usd_mxn():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()
        return float(r["rates"]["MXN"])
    except: return 17.34

def get_market():
    try:
        data={}
        for sym in ["BTC","ETH","XRP"]:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=6).json()
            data[sym]=[float(r["data"]["amount"]), 0.0]
        try:
            for sym_b, name in [("BTCUSDT","BTC"),("ETHUSDT","ETH"),("XRPUSDT","XRP")]:
                r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={sym_b}", timeout=5).json()
                data[name][1]=float(r["priceChangePercent"])
        except:
            try:
                cg=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true", timeout=5).json()
                data["BTC"][1]=float(cg["bitcoin"].get("usd_24h_change",0)or 0)
                data["ETH"][1]=float(cg["ethereum"].get("usd_24h_change",0)or 0)
                data["XRP"][1]=float(cg["ripple"].get("usd_24h_change",0)or 0)
            except: pass
        return {k:(v[0],v[1]) for k,v in data.items()}
    except: return None

def load_holdings():
    if os.path.exists(HOLD_FILE):
        try:
            with open(HOLD_FILE,'r') as f: return json.load(f)
        except: pass
    m=get_market(); usd_mxn=get_usd_mxn()
    if not m: return {"efectivo_mxn":0.0,"BTC":{"cant":0.00030744},"ETH":{"cant":0.01047262},"XRP":{"cant":18.24628696}}
    por=CAPITAL_MXN/3.0
    h={"efectivo_mxn":0.0,"BTC":{"cant":(por/usd_mxn)/m["BTC"][0]},"ETH":{"cant":(por/usd_mxn)/m["ETH"][0]},"XRP":{"cant":(por/usd_mxn)/m["XRP"][0]}}
    with open(HOLD_FILE,'w') as f: json.dump(h,f)
    return h

def save_holdings(h):
    with open(HOLD_FILE,'w') as f: json.dump(h,f)

def texto_balance():
    m=get_market(); h=load_holdings()
    if not m: return "⚠️ Mercado ocupado, toca Actualizar..."
    usd_mxn=get_usd_mxn()
    total=h.get("efectivo_mxn",0)
    txt=f"🎮 **MODO DEMO - SIMULACIÓN**\n💰 Capital ficticio ${CAPITAL_MXN:.0f} MXN\n💱 USD/MXN: ${usd_mxn:.2f}\n💵 Efectivo DEMO: ${h.get('efectivo_mxn',0):.2f} MXN\n\n"
    for coin in ["BTC","ETH","XRP"]:
        cant=h[coin]["cant"]; precio=m[coin][0]; pct=m[coin][1]
        valor=cant*precio*usd_mxn; total+=valor
        emoji = "🟢" if pct>=0 else "🔴"
        txt+=f"{emoji} {coin}: {cant:.8f}\n ${precio:,.2f} ({pct:+.2f}%) -> ${valor:.2f} MXN\n"
    gan=total-CAPITAL_MXN
    txt+=f"\n💵 TOTAL DEMO: ${total:.2f} MXN\n📊 Gan ficticia: {gan/CAPITAL_MXN*100:+.2f}% (${gan:+.2f})"
    txt+=f"\n\n⚠️ SIMULACIÓN - No es dinero real\nCmd: /comprar BTC 100 | /vender XRP 50 | /reset"
    return txt

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Actualizar", callback_data="t")]])
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(texto_balance(), reply_markup=menu())
async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(texto_balance(), reply_markup=menu())
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); await q.edit_message_text(texto_balance(), reply_markup=menu())
async def comprar(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        if h["efectivo_mxn"]>1 and h["efectivo_mxn"] < monto:
            await u.message.reply_text(f"❌ DEMO: Solo tienes ${h['efectivo_mxn']:.2f} ficticios"); return
        cant=(monto/usd_mxn)/m[coin][0]; h[coin]["cant"]+=cant; h["efectivo_mxn"]-=monto
        if h["efectivo_mxn"]<0: h["efectivo_mxn"]=0
        save_holdings(h)
        await u.message.reply_text(f"✅ SIMULACIÓN: Compraste ${monto:.2f} ficticios de {coin}\n +{cant:.8f} {coin}\n💵 Efectivo DEMO: ${h['efectivo_mxn']:.2f}", reply_markup=menu())
    except: await u.message.reply_text("Uso DEMO: /comprar BTC 100")
async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant=(monto/usd_mxn)/m[coin][0]
        if h[coin]["cant"]<cant: await u.message.reply_text(f"❌ DEMO: Solo tienes {h[coin]['cant']:.8f} {coin}"); return
        h[coin]["cant"]-=cant; h["efectivo_mxn"]+=monto; save_holdings(h)
        await u.message.reply_text(f"✅ SIMULACIÓN: Vendiste ${monto:.2f} ficticios de {coin}\n💵 Efectivo DEMO: ${h['efectivo_mxn']:.2f}", reply_markup=menu())
    except: await u.message.reply_text("Uso DEMO: /vender XRP 50")
async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    await u.message.reply_text("🔄 DEMO reseteado a $1000 ficticios\n"+texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V25.3 DEMO OK")
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
    print("V25.3 DEMO listo")
    app.run_polling(drop_pending_updates=True)
