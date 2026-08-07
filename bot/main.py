import os, json, requests, threading
from flask import Flask
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v32-botones"

app = Flask(__name__)
@app.route('/')
def home(): return "V32.1 BOTONES OK"

def load_data():
    try:
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res = r.json().get("result")
        if res: return json.loads(res)
    except: pass
    return {"users":{}}

def save_data(data):
    try:
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, json.dumps(data)], timeout=10)
    except: pass

def get_market():
    try:
        btc_p = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth_p = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp_p = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        # RSI simple
        def get_rsi(sym):
            try:
                h = yf.Ticker(sym).history(period="7d")['Close']
                d = h.diff()
                g = d.where(d>0,0).rolling(14).mean().iloc[-1]
                l = -d.where(d<0,0).rolling(14).mean().iloc[-1]
                if l==0: return 50.0
                rs = g/l
                return round(100-(100/(1+rs)),1)
            except: return 40.0
        br, er, xr = get_rsi("BTC-USD"), get_rsi("ETH-USD"), get_rsi("XRP-USD")
        # % dia
        def get_pct(sym):
            try:
                h = yf.Ticker(sym).history(period="2d")['Close']
                return float((h.iloc[-1]/h.iloc[-2]-1)*100)
            except: return 0.0
        bp, ep, xp = get_pct("BTC-USD"), get_pct("ETH-USD"), get_pct("XRP-USD")
        return btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr
    except:
        return 64264.07, 1901.75, 1.03, 17.20, -0.5, -0.2, -2.4, 40.0, 40.0, 40.0

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc_p, eth_p, xrp_p, usdmxn, _,_,_, _,_,_ = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/usdmxn)/btc_p,"eth":(333.33/usdmxn)/eth_p,"xrp":(333.33/usdmxn)/xrp_p,"inicial":1000.0}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr = get_market()
    total = u['efectivo']+u['btc']*btc_p*usdmxn+u['eth']*eth_p*usdmxn+u['xrp']*xrp_p*usdmxn
    gan = (total-u['inicial'])/u['inicial']*100
    return f"DEMO $1000 MXN\nUSD/MXN: ${usdmxn:.2f}\nEfectivo: ${u['efectivo']:.2f} MXN\n\nBTC: {u['btc']:.8f} | ${u['btc']*btc_p*usdmxn:.2f}\nPrecio ${btc_p:,.2f} ({bp:.2f}%) RSI:{br}\nETH: {u['eth']:.8f} | ${u['eth']*eth_p*usdmxn:.2f}\nPrecio ${eth_p:,.2f} ({ep:.2f}%) RSI:{er}\nXRP: {u['xrp']:.4f} | ${u['xrp']*xrp_p*usdmxn:.2f}\nPrecio ${xrp_p:.2f} ({xp:.2f}%) RSI:{xr}\n\nTOTAL: ${total:.2f} MXN\nGanancia: {gan:+.2f}%\nV32.1 BOTONES"

def kb_main(): return InlineKeyboardMarkup([ [InlineKeyboardButton("🟢 COMPRAR", callback_data="menu_c"), InlineKeyboardButton("🔴 VENDER", callback_data="menu_v")], [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="act")] ])
def kb_c(): return InlineKeyboardMarkup([ [InlineKeyboardButton("BTC $100", callback_data="c_btc_100"), InlineKeyboardButton("ETH $100", callback_data="c_eth_100")], [InlineKeyboardButton("XRP $100", callback_data="c_xrp_100")], [InlineKeyboardButton("⬅️ Volver", callback_data="act")] ])
def kb_v(): return InlineKeyboardMarkup([ [InlineKeyboardButton("BTC $100", callback_data="v_btc_100"), InlineKeyboardButton("ETH $100", callback_data="v_eth_100")], [InlineKeyboardButton("XRP $100", callback_data="v_xrp_100"), InlineKeyboardButton("VENDER TODO BTC", callback_data="v_btc_todo")], [InlineKeyboardButton("⬅️ Volver", callback_data="act")] ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=load_data(); u=get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u), reply_markup=kb_main())

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=load_data(); uid=str(q.from_user.id); u=get_user(uid, data)
    btc_p, eth_p, xrp_p, usdmxn, _,_,_, _,_,_ = get_market()
    precios={"btc":btc_p,"eth":eth_p,"xrp":xrp_p}
    d=q.data
    if d=="act": await q.edit_message_text(texto(u), reply_markup=kb_main()); return
    if d=="menu_c": await q.edit_message_text("¿Qué COMPRAS?", reply_markup=kb_c()); return
    if d=="menu_v": await q.edit_message_text("¿Qué VENDES?", reply_markup=kb_v()); return
    try:
        acc, mon, mont = d.split("_")
        mxn = 100 if mont=="100" else 0
        if mont=="todo": mxn = u[mon]*precios[mon]*usdmxn
        if acc=="c":
            # Si no hay efectivo, no compra (para que no quede negativo)
            if u['efectivo'] < mxn and u['efectivo'] < 10 and mon in ["btc","eth","xrp"]:
                # Primera vez: permitimos usar el valor de otra moneda? No, avisamos
                if u['efectivo']==0:
                    await q.edit_message_text(f"⚠️ No tienes efectivo. Vende primero algo para tener efectivo.\n\n{texto(u)}", reply_markup=kb_main()); return
            if u['efectivo'] < mxn: mxn = u['efectivo']
            if mxn <=0: await q.edit_message_text(f"Sin efectivo\n\n{texto(u)}", reply_markup=kb_main()); return
            qty=(mxn/usdmxn)/precios[mon]; u[mon]+=qty; u['efectivo']-=mxn; msg=f"✅ COMPRASTE ${mxn:.0f} de {mon.upper()}"
        else:
            qty=(mxn/usdmxn)/precios[mon]
            if mon=="btc" and mont=="todo": qty=u['btc']; mxn=qty*precios[mon]*usdmxn
            if u[mon] < qty: qty=u[mon]; mxn=qty*precios[mon]*usdmxn
            u[mon]-=qty; u['efectivo']+=mxn; msg=f"✅ VENDISTE ${mxn:.0f} de {mon.upper()}"
        data["users"][uid]=u; save_data(data)
        await q.edit_message_text(f"{msg}\n\n{texto(u)}", reply_markup=kb_main())
    except Exception as e:
        await q.edit_message_text(f"{texto(u)}", reply_markup=kb_main())

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("actualizar", start))
    application.add_handler(CommandHandler("balance", start))
    application.add_handler(CallbackQueryHandler(btn))
    print("V32.1 BOTONES OK")
    application.run_polling()
