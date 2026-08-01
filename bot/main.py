import os, json, threading, time, sys
print("=== V20 FINAL VICENTE - BTC ETH XRP SEPARADO ===", flush=True)
from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_FILE = "/tmp/chat_id.txt"
BALANCE_FILE = "/tmp/balance.json"
CACHE = {"t":0, "data":None}
INIT = 1000.0
COMISION = 0.0078

app = Flask(__name__)

# --- WEB CON 3 MONEDAS SEPARADAS ---
@app.route('/')
def home():
    return """
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0b0e11;color:white;font-family:Arial;text-align:center;margin:0;padding:8px}
.card{background:#1e2329;padding:12px;border-radius:12px;margin:8px}
.price{font-size:28px;font-weight:bold}
iframe{width:100%;height:480px;border:0;border-radius:12px}
.btn{padding:10px 18px;margin:4px;border-radius:8px;border:0;font-weight:bold;cursor:pointer}
.xrp{color:#0ecb81}.btc{color:#f3ba2f}.eth{color:#627eea}
</style></head><body>
<h3>🤖 Bot Vicente - XRP BTC ETH - VIVO</h3>
<div style="display:flex;justify-content:center;flex-wrap:wrap">
<div class="card" style="min-width:110px"><div>XRP</div><div class="price xrp" id="xrp">$ --</div></div>
<div class="card" style="min-width:110px"><div>BTC</div><div class="price btc" id="btc">$ --</div></div>
<div class="card" style="min-width:110px"><div>ETH</div><div class="price eth" id="eth">$ --</div></div>
</div>
<div class="card">
<button class="btn" id="bXRP" onclick="show('XRPUSDT','bXRP')" style="background:#f3ba2f;color:black">XRP</button>
<button class="btn" id="bBTC" onclick="show('BTCUSDT','bBTC')" style="background:#2b3139;color:white">BTC</button>
<button class="btn" id="bETH" onclick="show('ETHUSDT','bETH')" style="background:#2b3139;color:white">ETH</button>
<div style="margin-top:10px"><iframe id="tv" src="https://s.tradingview.com/widgetembed/?symbol=BINANCE%3AXRPUSDT&interval=5&theme=dark&style=1&locale=es"></iframe></div>
<div style="margin-top:8px;font-size:12px;opacity:0.7">EMA 20/50 + RSI en la grafica</div>
</div>
<script>
function show(sym,btn){
 document.getElementById('tv').src='https://s.tradingview.com/widgetembed/?symbol=BINANCE%3A'+sym+'&interval=5&theme=dark&style=1&locale=es';
 ['bXRP','bBTC','bETH'].forEach(b=>{document.getElementById(b).style.background='#2b3139';document.getElementById(b).style.color='white'});
 document.getElementById(btn).style.background='#f3ba2f';document.getElementById(btn).style.color='black';
}
async function upd(){
 try{
  let rx=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT'); let jx=await rx.json();
  document.getElementById('xrp').innerText='$'+parseFloat(jx.price).toFixed(4);
  let rb=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'); let jb=await rb.json();
  document.getElementById('btc').innerText='$'+parseFloat(jb.price).toFixed(0);
  let re=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT'); let je=await re.json();
  document.getElementById('eth').innerText='$'+parseFloat(je.price).toFixed(0);
 }catch(e){}
}
setInterval(upd,2000);upd();
</script></body></html>
"""
@app.route('/health')
def hl(): return "OK"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

# --- BOT LOGICA ---
def get_prices():
    global CACHE
    if time.time() - CACHE["t"] < 60 and CACHE["data"]: return CACHE["data"]
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22XRPUSDT%22]"
        r = requests.get(url, timeout=10).json()
        d = {x['symbol']: (float(x['lastPrice']), float(x['priceChangePercent'])) for x in r}
        data = {"btc": d['BTCUSDT'], "eth": d['ETHUSDT'], "xrp": d['XRPUSDT']}
        CACHE = {"t": time.time(), "data": data}
        return data
    except: return CACHE["data"]

def load_bal():
    try:
        with open(BALANCE_FILE,'r') as f: return json.load(f)
    except:
        return {"btc": (INIT/3)/68000, "eth": (INIT/3)/3400, "xrp": (INIT/3)/0.6, "usd":0, "init":INIT, "p_btc":68000,"p_eth":3400,"p_xrp":0.6}
def save_bal(b):
    with open(BALANCE_FILE,'w') as f: json.dump(b,f)

def fmt_one(m):
    p = get_prices()
    if not p: return "Actualizando..."
    price, change = p[m]
    bal = load_bal()
    qty = bal[m]
    return f"🟢 {m.upper()}: ${price:,.4f} ({change:+.2f}%)\nTienes: {qty:.6f}\nValor: ${qty*price:.2f}\nCompra: ${bal.get(f'p_{m}',price):,.2f}"

def fmt_all():
    p = get_prices()
    if not p: return "Actualizando..."
    bal = load_bal()
    total = bal['btc']*p['btc'][0] + bal['eth']*p['eth'][0] + bal['xrp']*p['xrp'][0] + bal['usd']
    return f"📊 TOTAL: ${total:.2f} ({(total-INIT)/INIT*100:+.2f}%)\n\nBTC: ${bal['btc']*p['btc'][0]:.2f} ({p['btc'][1]:+.1f}%)\nETH: ${bal['eth']*p['eth'][0]:.2f} ({p['eth'][1]:+.1f}%)\nXRP: ${bal['xrp']*p['xrp'][0]:.2f} ({p['xrp'][1]:+.1f}%)"

def get_buttons(m=None):
    if m:
        return InlineKeyboardMarkup([[InlineKeyboardButton(f"🟢 Comprar {m.upper()}", callback_data=f"comprar_{m}"), InlineKeyboardButton(f"🔴 Vender {m.upper()}", callback_data=f"vender_{m}")],[InlineKeyboardButton("💰 Total", callback_data="todo")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 BTC", callback_data="ver_btc"), InlineKeyboardButton("🔴 BTC", callback_data="vender_btc")],[InlineKeyboardButton("🟢 ETH", callback_data="ver_eth"), InlineKeyboardButton("🔴 ETH", callback_data="vender_eth")],[InlineKeyboardButton("🟢 XRP", callback_data="ver_xrp"), InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp")],[InlineKeyboardButton("💰 Balance Total", callback_data="todo")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CHAT_ID_FILE,'w') as f: f.write(str(update.effective_chat.id))
    await update.message.reply_text("✅ V20 FINAL - 3 monedas separadas\n/btc /eth /xrp /balance", reply_markup=get_buttons())
async def cmd_btc(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_one("btc"), reply_markup=get_buttons("btc"))
async def cmd_eth(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_one("eth"), reply_markup=get_buttons("eth"))
async def cmd_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_one("xrp"), reply_markup=get_buttons("xrp"))
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(fmt_all(), reply_markup=get_buttons())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    bal = load_bal(); precios = get_prices()
    if not precios: return
    data = q.data
    if data.startswith("ver_"):
        m = data.split("_")[1]
        await q.edit_message_text(fmt_one(m), reply_markup=get_buttons(m)); return
    if data == "todo":
        await q.edit_message_text(fmt_all(), reply_markup=get_buttons()); return
    accion, moneda = data.split("_")
    precio = precios[moneda][0]
    if accion == "comprar":
        cant = (50*(1-COMISION))/precio; bal[moneda]+=cant; bal[f"p_{moneda}"]=precio; save_bal(bal)
        await q.edit_message_text(f"✅ COMPRA {moneda.upper()}\n\n"+fmt_one(moneda), reply_markup=get_buttons(moneda))
    else:
        if bal[moneda]<=0:
            await q.answer(f"No tienes {moneda.upper()}"); return
        usd = bal[moneda]*precio*(1-COMISION); bal['usd']+=usd; bal[moneda]=0; save_bal(bal)
        await q.edit_message_text(f"✅ VENTA {moneda.upper()} ${usd:.2f}\n\n"+fmt_all(), reply_markup=get_buttons())

async def alerta_inteligente(context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(CHAT_ID_FILE,'r') as f: cid = f.read().strip()
        if not cid: return
        precios = get_prices()
        if not precios: return
        bal = load_bal()
        for moneda in ["btc","eth","xrp"]:
            precio, cambio = precios[moneda]
            if cambio <= -2.0:
                await context.bot.send_message(chat_id=int(cid), text=f"🟢 OPORTUNIDAD COMPRA {moneda.upper()}!\n📉 Cayó {cambio:.2f}%\n${precio:,.4f}", reply_markup=get_buttons(moneda))
            if bal[moneda]>0:
                p_compra = bal.get(f"p_{moneda}",0)
                if p_compra>0:
                    gan = (precio - p_compra)/p_compra*100 - 1.56
                    if gan >= 2.0:
                        await context.bot.send_message(chat_id=int(cid), text=f"🔴 OPORTUNIDAD VENTA {moneda.upper()}!\n✅ +{gan:.2f}% NETO\n${precio:,.4f}", reply_markup=get_buttons(moneda))
    except: pass

def main():
    threading.Thread(target=run_web, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("btc", cmd_btc))
    application.add_handler(CommandHandler("eth", cmd_eth))
    application.add_handler(CommandHandler("xrp", cmd_xrp))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CallbackQueryHandler(buttons))
    application.job_queue.run_repeating(alerta_inteligente, interval=300, first=30)
    application.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
