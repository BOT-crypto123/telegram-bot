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
    txt=f"🎮 **MODO DEMO - SIMULACIÓN**\n💰 Capital ficticio ${CAPITAL_MXN:.0f} MXN\n💱 USD/MXN: ${usd_mxn:.2f}\n💵 Efectivo DEMO: ${h.get('efectivo_mxn',0):.2f} MXN\n\n"
    for coin in ["BTC","ETH","XRP"]:
        cant=h[coin]["cant"]; precio=m[coin][0]; pct=m[coin][1]
        valor=cant*precio*usd_mxn; total+=valor
        emoji = "🟢" if pct>=0 else "🔴"
        txt+=f"{emoji} {coin}: {cant:.8f}\n ${precio:,.2f} ({pct:+.2f}%) -> ${valor:.2f} MXN\n"
    gan=total-CAPITAL_MXN
    txt+=f"\n💵 TOTAL DEMO: ${total:.2f} MXN\n📊 Gan ficticia: {gan/CAPITAL_MXN*100:+.2f}% (${gan:+.2f})"
    txt+=f"\n\n⚠️ SIMULACIÓN - No es dinero real\n🔔 Alertas: -2% / +2% activas\nCmd: /comprar BTC 100 | /vender XRP 50 | /reset | /alertas"
    return txt

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Actualizar", callback_data="t")]])

# --- ALERTAS AUTOMATICAS ---
def load_cooldown():
    if os.path.exists(ALERT_FILE):
        try:
            with open(ALERT_FILE,'r') as f: return json.load(f)
        except: pass
    return {}

def save_cooldown(d):
    with open(ALERT_FILE,'w') as f: json.dump(d,f)

def monitor_alertas(app):
    print("Monitor alertas iniciado -2% +2%")
    while True:
        try:
            time.sleep(300) # 5 min
            if not os.path.exists(CHAT_FILE): continue
            with open(CHAT_FILE,'r') as f: chat_id=f.read().strip()
            if not chat_id: continue
            m=get_market()
            if not m: continue
            cooldown=load_cooldown()
            now=time.time()
            for coin in ["BTC","ETH","XRP"]:
                pct=m[coin][1]
                key=f"{coin}_{'up' if pct>=2 else 'down' if pct<=-2 else 'none'}"
                # Solo alerta si supera umbral
                if pct >= 2.0:
                    if now - cooldown.get(f"{coin}_up",0) < 3600: continue # no spamear, 1h
                    texto = f"🟢 ALERTA DEMO: {coin} subió {pct:+.2f}% en 24h\n💰 Precio: ${m[coin][0]:,.2f}\n💡 Oportunidad VENTA simulación\nUsa /vender {coin} 100\n⚠️ SIMULACIÓN - No es dinero real"
                    try:
                        import asyncio
                        asyncio.run_coroutine_threadsafe(app.bot.send_message(chat_id=chat_id, text=texto), app.loop).result()
                    except:
                        # fallback sync
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_up"]=now
                    save_cooldown(cooldown)
                elif pct <= -2.0:
                    if now - cooldown.get(f"{coin}_down",0) < 3600: continue
                    texto = f"🔴 ALERTA DEMO: {coin} cayó {pct:+.2f}% en 24h\n💰 Precio: ${m[coin][0]:,.2f}\n💡 Oportunidad COMPRA simulación\nUsa /comprar {coin} 100\n⚠️ SIMULACIÓN - No es dinero real"
                    try:
                        import asyncio
                        asyncio.run_coroutine_threadsafe(app.bot.send_message(chat_id=chat_id, text=texto), app.loop).result()
                    except:
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_down"]=now
                    save_cooldown(cooldown)
        except Exception as e:
            print(f"Error monitor {e}")
            time.sleep(60)

# --- COMANDOS ---
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
    await u.message.reply_text(f"🎮 DEMO\n₿ BTC: ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)", reply_markup=menu())
async def eth_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"🎮 DEMO\nΞ ETH: ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%)", reply_markup=menu())
async def xrp_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"🎮 DEMO\n✖️ XRP: ${m['XRP'][0]:,.2f} ({m['XRP'][1]:+.2f}%)", reply_markup=menu())
async def alertas_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text("🔔 **ALERTAS DEMO ACTIVAS**\n\n- Te aviso si cualquier moneda baja -2% o más (oportunidad compra ficticia)\n- Te aviso si sube +2% o más (oportunidad venta ficticia)\n- Reviso cada 5 min\n- No repito la misma alerta por 1 hora para no spamear\n\nTodo es SIMULACIÓN con tu capital ficticio $1000 MXN\n\nComandos:\n/balance - ver tu portafolio DEMO\n/alertas - ver esto\n/reset - reiniciar DEMO", reply_markup=menu())
async def comprar(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        if h["efectivo_mxn"]>1 and h["efectivo_mxn"] < monto:
            await u.message.reply_text(f"❌ DEMO: Solo tienes ${h['efectivo_mxn']:.2f} ficticios"); return
        cant=(monto/usd_mxn)/m[coin][0]; h[coin]["cant"]+=cant; h["efectivo_mxn"]-=monto
        if h["efectivo_mxn"]<0: h["efectivo_mxn"]=0
        save_holdings(h)
        await u.message.reply_text(f"✅ SIMULACIÓN: Compraste ${monto:.2f} ficticios de {coin}\n +{cant:.8f} {coin}", reply_markup=menu())
    except: await u.message.reply_text("Uso DEMO: /comprar BTC 100")
async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant=(monto/usd_mxn)/m[coin][0]
        if h[coin]["cant"]<cant: await u.message.reply_text(f"❌ DEMO: Solo tienes {h[coin]['cant']:.8f} {coin}"); return
        h[coin]["cant"]-=cant; h["efectivo_mxn"]+=monto; save_holdings(h)
        await u.message.reply_text(f"✅ SIMULACIÓN: Vendiste ${monto:.2f} ficticios de {coin}", reply_markup=menu())
    except: await u.message.reply_text("Uso DEMO: /vender XRP 50")
async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    await u.message.reply_text("🔄 DEMO reseteado a $1000 ficticios\n"+texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V26 ALERTAS OK")
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
    # hilo alertas
    threading.Thread(target=monitor_alertas, args=(app,), daemon=True).start()
    print("V26 con alertas -2% +2% listo")
    app.run_polling(drop_pending_updates=True)
