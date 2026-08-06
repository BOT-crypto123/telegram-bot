import os, requests, threading, json, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
# Para que no se borre en Render, usa /data si tienes disco persistente
HOLD_FILE = "/data/holdings_v27.json" if os.path.exists("/data") else "/tmp/holdings_v25.json"
CHAT_FILE = "/data/chat_id.txt" if os.path.exists("/data") else "/tmp/chat_id.txt"
ALERT_FILE = "/data/alert_cooldown.json" if os.path.exists("/data") else "/tmp/alert_cooldown.json"
CAPITAL_MXN = 1000.0

def get_usd_mxn():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()
        return float(r["rates"]["MXN"])
    except: return 17.34

def get_rsi(symbol="BTCUSDT", period=14):
    try:
        # Trae velas de 1h de Binance
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        klines = requests.get(url, timeout=8).json()
        closes = [float(k[4]) for k in klines]
        if len(closes) < period+1: return 50.0
        deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
        gains = [d if d>0 else 0 for d in deltas[-period:]]
        losses = [-d if d<0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains)/period
        avg_loss = sum(losses)/period
        if avg_loss == 0: return 100.0
        rs = avg_gain/avg_loss
        return 100 - (100/(1+rs))
    except:
        return 50.0

def get_market():
    try:
        data={}
        for sym in ["BTC","ETH","XRP"]:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=6).json()
            data[sym]=[float(r["data"]["amount"]), 0.0, 50.0]
        try:
            for sym_b, name in [("BTCUSDT","BTC"),("ETHUSDT","ETH"),("XRPUSDT","XRP")]:
                r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={sym_b}", timeout=5).json()
                data[name][1]=float(r["priceChangePercent"])
                data[name][2]=get_rsi(sym_b)
        except: pass
        return {k:(v[0],v[1],v[2]) for k,v in data.items()}
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
        cant=h[coin]["cant"]; precio=m[coin][0]; pct=m[coin][1]; rsi=m[coin][2]
        valor=cant*precio*usd_mxn; total+=valor
        emoji = "🟢" if pct>=0 else "🔴"
        rsi_txt = "🔥CARO" if rsi>70 else "💎BARATO" if rsi<35 else f"{rsi:.0f}"
        txt+=f"{emoji} {coin}: {cant:.8f}\n Precio ${precio:,.2f} ({pct:+.2f}%) RSI:{rsi:.1f} {rsi_txt}\n Valor ${valor:.2f} MXN\n"
    gan=total-CAPITAL_MXN
    gan_pct=gan/CAPITAL_MXN*100
    txt+=f"\n💵 TOTAL: ${total:.2f} MXN\n📈 Ganancia: {gan_pct:+.2f}% (${gan:+.2f})\n\n🔔 Alertas -2%/+2% + RSI activas\n✅ V27 INMORTAL"
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

def monitor_alertas():
    while True:
        try:
            time.sleep(300)
            if not os.path.exists(CHAT_FILE): continue
            with open(CHAT_FILE,'r') as f: chat_id=f.read().strip()
            if not chat_id or not TOKEN: continue
            m=get_market()
            if not m: continue
            cooldown=load_cooldown(); now=time.time()
            for coin in ["BTC","ETH","XRP"]:
                pct=m[coin][1]; rsi=m[coin][2]
                # Alerta %
                if pct >= 2.0 and now - cooldown.get(f"{coin}_up",0) > 3600:
                    texto = f"🟢 ALERTA REAL: {coin} subió {pct:+.2f}% RSI:{rsi:.1f}\nPrecio: ${m[coin][0]:,.2f}\n💡 Venta DEMO /vender {coin} 100"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_up"]=now; save_cooldown(cooldown)
                elif pct <= -2.0 and now - cooldown.get(f"{coin}_down",0) > 3600:
                    texto = f"🔴 ALERTA REAL: {coin} cayó {pct:+.2f}% RSI:{rsi:.1f}\nPrecio: ${m[coin][0]:,.2f}\n💡 Compra DEMO /comprar {coin} 100"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_down"]=now; save_cooldown(cooldown)
                # Alerta RSI extremo
                if rsi < 32 and now - cooldown.get(f"{coin}_rsi_low",0) > 14400:
                    texto = f"💎 RSI BARATO: {coin} RSI {rsi:.1f} (sobrevendido)\nPrecio: ${m[coin][0]:,.2f}"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat_id,"text":texto}, timeout=5)
                    cooldown[f"{coin}_rsi_low"]=now; save_cooldown(cooldown)
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
    m=get_market(); rsi_txt="BARATO" if m['BTC'][2]<35 else "CARO" if m['BTC'][2]>70 else "NEUTRO"
    await u.message.reply_text(f"₿ BTC ${m['BTC'][0]:,.2f} ({m['BTC'][1]:+.2f}%)\n📊 RSI:{m['BTC'][2]:.1f} {rsi_txt}", reply_markup=menu())
async def eth_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"Ξ ETH ${m['ETH'][0]:,.2f} ({m['ETH'][1]:+.2f}%) RSI:{m['ETH'][2]:.1f}", reply_markup=menu())
async def xrp_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    m=get_market()
    await u.message.reply_text(f"✖️ XRP ${m['XRP'][0]:,.2f} ({m['XRP'][1]:+.2f}%) RSI:{m['XRP'][2]:.1f}", reply_markup=menu())
async def alertas_cmd(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    await u.message.reply_text("🔔 Alertas:\n-2%/+2% cada 1h\nRSI<32 cada 4h\nReviso cada 5 min", reply_markup=menu())
async def comprar(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        if h["efectivo_mxn"]>1 and h["efectivo_mxn"] < monto:
            await u.message.reply_text(f"❌ Solo ${h['efectivo_mxn']:.2f}"); return
        cant=(monto/usd_mxn)/m[coin][0]; h[coin]["cant"]+=cant; h["efectivo_mxn"]-=monto
        if h["efectivo_mxn"]<0: h["efectivo_mxn"]=0
        save_holdings(h)
        await u.message.reply_text(f"✅ Compraste ${monto:.2f} {coin} RSI:{m[coin][2]:.1f}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /comprar BTC 100")
async def vender(u:Update,c:ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
        coin=c.args[0].upper(); monto=float(c.args[1]); m=get_market(); h=load_holdings(); usd_mxn=get_usd_mxn()
        cant=(monto/usd_mxn)/m[coin][0]
        if h[coin]["cant"]<cant: await u.message.reply_text(f"❌ Solo {h[coin]['cant']:.8f} {coin}"); return
        h[coin]["cant"]-=cant; h["efectivo_mxn"]+=monto; save_holdings(h)
        await u.message.reply_text(f"✅ Vendiste ${monto:.2f} {coin} RSI:{m[coin][2]:.1f}", reply_markup=menu())
    except: await u.message.reply_text("Uso: /vender XRP 50")
async def reset(u:Update,c:ContextTypes.DEFAULT_TYPE):
    with open(CHAT_FILE,'w') as f: f.write(str(u.effective_chat.id))
    if os.path.exists(HOLD_FILE): os.remove(HOLD_FILE)
    await u.message.reply_text("🔄 Reset\n"+texto_balance(), reply_markup=menu())

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200);self.end_headers();self.wfile.write(b"V27 INMORTAL RSI OK")
    def log_message(self,*a): pass
def run_web(): HTTPServer(("0.0.0.0",int(os.environ.get("PORT",10000))),H).serve_forever()

if __name__=="__main__":
    threading.Thread(target=run_web,daemon=True).start()
    threading.Thread(target=monitor_alertas, daemon=True).start()
    # BUCLE INMORTAL
    while True:
        try:
            print("V27 INMORTAL iniciando...")
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
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"Bot crasheo: {e} - Reiniciando en 10s")
            time.sleep(10)
