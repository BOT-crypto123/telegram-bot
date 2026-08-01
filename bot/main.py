import os, requests, threading, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_FILE = "/tmp/chat_id.txt"
HOLD_FILE = "/tmp/holdings_v25.json"
CAPITAL_MXN = 1000.0

def get_usd_mxn():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()
        return float(r["rates"]["MXN"])
    except: return 18.5

def get_market():
    # Intenta 4 fuentes distintas
    # 1. Coinbase (la que menos bloquea Render)
    try:
        data={}
        for sym in ["BTC","ETH","XRP"]:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=6).json()
            price = float(r["data"]["amount"])
            data[sym]=(price,0.0) # sin % pero funciona
        if len(data)==3:
            # saca % de coingecko si puede, si no 0
            try:
                cg=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true", timeout=5).json()
                data["BTC"]=(data["BTC"][0], float(cg["bitcoin"].get("usd_24h_change",0)))
                data["ETH"]=(data["ETH"][0], float(cg["ethereum"].get("usd_24h_change",0)))
                data["XRP"]=(data["XRP"][0], float(cg["ripple"].get("usd_24h_change",0)))
            except: pass
            return data
    except Exception as e: print(f"coinbase fail {e}")

    # 2. Kraken
    try:
        r=requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCUSD,ETHUSD,XRPUSD", timeout=6).json()
        return {
            "BTC":(float(r["result"]["XXBTZUSD"]["c"][0]),0.0),
            "ETH":(float(r["result"]["XETHZUSD"]["c"][0]),0.0),
            "XRP":(float(r["result"]["XXRPZUSD"]["c"][0]),0.0),
        }
    except Exception as e: print(f"kraken fail {e}")

    # 3. Binance Vision
    try:
        data={}
        for sym,name in [("BTCUSDT","BTC"),("ETHUSDT","ETH"),("XRPUSDT","XRP")]:
            r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}", timeout=6).json()
            data[name]=(float(r["price"]),0.0)
        return data
    except Exception as e: print(f"binance vision fail {e}")
    return None

def load_holdings():
    if os.path.exists(HOLD_FILE):
        try:
            with open(HOLD_FILE,'r') as f: return json.load(f)
        except: pass
    # Si no hay, crea demo
    m=get_market()
    usd_mxn=get_usd_mxn()
    if not m:
        return {"efectivo_mxn":0.0,"BTC":{"cant":0.00000285},"ETH":{"cant":0.00018},"XRP":{"cant":8.0}}
    por= CAPITAL_MXN/3.0
    h={"efectivo_mxn":0.0,"BTC":{"cant":(por/usd_mxn)/m["BTC"][0]},"ETH":{"cant":(por/usd_mxn)/m["ETH"][0]},"XRP":{"cant":(por/usd_mxn)/m["XRP"][0]}}
    with open(HOLD_FILE,'w') as f: json.dump(h,f)
    return h

def save_holdings(h):
    with open(HOLD_FILE,'w') as f: json.dump(h,f)

def texto_balance():
    m=get_market(); h=load_holdings()
    if not m: return "⚠️ Aún bloqueado, toca Actualizar en 3s... (voy a seguir intentando)"
    usd_mxn=get_usd_mxn()
    total=h.get("efectivo_mxn",0)
    txt=f"💰 DEMO TRADING ${CAPITAL_MXN:.0f} MXN\n💱 USD/MXN: ${usd_mxn:.2f}\n💵 Efectivo: ${h.get('efectivo_mxn',0):.2f} MXN\n\n"
    for coin in ["BTC","ETH","XRP"]:
        cant=h[coin]["cant"]; precio=m[coin][0]
        valor=cant*precio*usd_mxn; total+=valor
        txt+=f"{coin}: {cant:.8f}\n ${precio:.2f} ({m[coin][1]:+.2f}%) -> ${valor:.2f} MXN\n"
    gan=total-CAPITAL_MXN
    txt+=f"\n💵 TOTAL: ${total:.2f} MXN\n📊 Gan: {gan/CAPITAL_MXN*100:+.2f}% (${gan:+.2f})"
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
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant=(monto/usd_mxn)/m[coin][0]; h[coin]["cant"]+=cant; h["efectivo_mxn"]-=monto
        if h["efectivo_mxn"]<0: h["efectivo_mxn"]=0; save_holdings(h)
        await u.message.reply_text(f"✅ Compraste ${monto} de {coin}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /comprar BTC 100")
async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant=(monto/usd_mxn)/m[coin][0]
        if h[coin]["cant"]<cant: await u.message.reply_text("❌ No alcanza"); return
        h[coin]["cant"]-=cant; h["efectivo_mxn"]+=monto; save_holdings(h)
        await u.message.reply_text(f"✅ Vendiste ${monto} de {coin}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /vender XRP 100")
async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    await u.message.reply_text("🔄 Reseteado\n"+texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V25.2 OK")
    def log_message(self,*a): pass
def run_web(): HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    import asyncio
    threading.Thread(target=run_web,daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("balance",bal))
    app.add_handler(CommandHandler("comprar",comprar))
    app.add_handler(CommandHandler("vender",vender))
    app.add_handler(CommandHandler("reset",reset))
    app.add_handler(CallbackQueryHandler(btn))
    print("V25.2 listo")
    app.run_polling(drop_pending_updates=True)
