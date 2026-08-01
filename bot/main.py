import os, requests, threading, json, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
HOLD_FILE = "/tmp/holdings_v25.json"
CHAT_FILE = "/tmp/chat_id.txt"
ALERT_FILE = "/tmp/alert_cooldown.json"
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
    txt=f"🎮 DEMO $1000 MXN (capital práctica)\n💱 USD/MXN REAL: ${usd_mxn:.2f}\n💵 Efectivo DEMO: ${h.get('efectivo_mxn',0):.2f} MXN\n\n"
    for coin in ["BTC","ETH","XRP"]:
        cant=h[coin]["cant"]; precio=m[coin][0]; pct=m[coin][1]
        valor=cant*precio*usd_mxn; total+=valor
        emoji = "🟢" if pct>=0 else "🔴"
        txt+=f"{emoji} {coin}: {cant:.8f}\n Precio REAL ${precio:,.2f} ({pct:+.2f}%) -> Valor REAL ${valor:.2f} MXN\n"
    gan=total-CAPITAL_MXN
    gan_pct=gan/CAPITAL_MXN*100
    txt+=f"\n💵 TOTAL con precio REAL: ${total:.2f} MXN\n📈 Ganancia REAL del mercado: {gan_pct:+.2f}% (${gan:+.2f} MXN)"
    txt+=f"\n\n✅ Precios 100% reales de Coinbase/Binance\n🎮 Operaciones /comprar /vender son simulación\n🔔 Alertas -2% / +2% activas"
    return txt

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Actualizar", callback_data="t")]])

def load_cooldown():
    if os.path.exists(ALERT_FILE):
        try:
            with open(ALERT_FILE,'r') as f: return json.load(f)
        except: pass
    return {}
def save_cooldown(d):
    with open(ALERT_FILE,'w') as f: json.dump(d,f)

def monitor_alertas(app):
    while True:
        try:
            time.sleep(300)
            if not os.path.exists(CHAT_FILE): continue
            with open(CHAT_FILE,'r') as f: chat_id=f.read().strip()
            if not chat_id: continue
            m=get_market()
            if not m: continue
            cooldown=load_cooldown()
            now=time.time()
            for coin in ["BTC","ETH","XRP"]:
                pct=m[coin][1]
                if pct >= 2.0:
                    if now - cooldown.get(f"{coin}_up",0) < 3600: continue
                    texto = f"🟢 ALERTA REAL: {coin} subió {pct:+.2f}% en 24h\nPrecio REAL: ${m[coin][0]:,.2f}\n💡 Oportunidad VENTA en DEMO\nUsa /vender {coin} 100"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_up"]=now; save_cooldown(cooldown)
                elif pct <= -2.0:
                    if now - cooldown.get(f"{coin}_down",0) < 3600: continue
                    texto = f"🔴 ALERTA REAL: {coin} cayó {pct:+.2f}% en 24h\nPrecio REAL: ${m[coin][0]:,.2f}\n💡 Oportunidad COMPRA en DEMO\nUsa /comprar {coin} 100"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_down"]=now; save_cooldown(cooldown)
        except Exception as e:
            print(f"Error monitor {e}"); time.sleep(60)

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())
async def bal(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text(texto_balance(), reply_markup=menu())
async def btn(u:Update,c:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); await q.edit_message_text(texto_balance(), reply_markup=menu())
async def btc_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"₿ BTC Precio REAL: ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)", reply_markup=menu())
async def eth_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"Ξ ETH Precio REAL: ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%)", reply_markup=menu())
async def xrp_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"✖️ XRP Precio REAL: ${m['XRP'][0]:,.2f} ({m['XRP'][1]:+.2f}%)", reply_markup=menu())
async def alertas_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text("🔔 ALERTAS con precio REAL activas\n-2% / +2%\nReviso cada 5 min", reply_markup=menu())
async def comprar(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        if h["efectivo_mxn"]>1 and h["efectivo_mxn"] < monto:
            await u.message.reply_text(f"❌ DEMO: Solo tienes ${h['efectivo_mxn']:.2f}"); return
        cant=(monto/usd_mxn)/m[coin][0]; h[coin]["cant"]+=cant; h["efectivo_mxn"]-=monto
        if h["efectivo_mxn"]<0: h["efectivo_mxn"]=0
        save_holdings(h)
        await u.message.reply_text(f"✅ SIMULACIÓN con precio REAL: Compraste ${monto:.2f} de {coin} a ${m[coin][0]:,.2f}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /comprar BTC 100")
async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant=(monto/usd_mxn)/m[coin][0]
        if h[coin]["cant"]<cant: await u.message.reply_text(f"❌ Solo tienes {h[coin]['cant']:.8f} {coin}"); return
        h[coin]["cant"]-=cant; h["efectivo_mxn"]+=monto; save_holdings(h)
        await u.message.reply_text(f"✅ SIMULACIÓN con precio REAL: Vendiste ${monto:.2f} de {coin} a ${m[coin][0]:,.2f}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /vender XRP 50")
async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    await u.message.reply_text("🔄 DEMO reseteado\n"+texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V26.1 REAL OK")
    def log_message(self,*a): pass
def run_web(): HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web,daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("balance",bal))
    app.add_handler(CommandHandler("btc",btc_cmd))
    app.add_handler(CommandHandler("eth",eth_cmd))
    app.add_handler(CommandHandler("xrp",xrp_cmd))
    app.add_handler(CommandHandler("alertas",alertas_cmd))
    app.add_handler(CommandHandler("comprar",comprar))
    app.add_handler(CommandHandler("vender",vender))
    app.add_handler(CommandHandler("reset",reset))
    app.add_handler(CallbackQueryHandler(btn))
    threading.Thread(target=monitor_alertas, args=(app,), daemon=True).start()
    print("V26.1 REAL listo")
    app.run_polling(drop_pending_updates=True)
