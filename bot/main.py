import os, json, requests, threading, math, time
from flask import Flask
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v35-2-final-7porciento"

app = Flask(__name__)
@app.route('/')
def home(): return "V35.2 FINAL -7% OK"

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
    btc_p, eth_p, xrp_p, usdmxn = 64254.34, 1901.30, 1.03, 17.20
    bp, ep, xp, br, er, xr = 0.0, 0.0, -2.5, 40.0, 40.0, 32.0
    try:
        btc_p = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth_p = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp_p = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        usdmxn = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        def pct(s):
            h=yf.Ticker(s).history(period="2d")['Close']
            return float((h.iloc[-1]/h.iloc[-2]-1)*100) if len(h)>=2 else 0.0
        bp, ep, xp = pct("BTC-USD"), pct("ETH-USD"), pct("XRP-USD")
        def rsi(s):
            h=yf.Ticker(s).history(period="1mo")['Close']
            if len(h)<15: return 40.0
            d=h.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
            rs=g.iloc[-1]/l.iloc[-1] if l.iloc[-1]!=0 else 0
            r=100-(100/(1+rs)) if rs!=0 else 50.0
            return 40.0 if math.isnan(r) else round(float(r),1)
        br, er, xr = rsi("BTC-USD"), rsi("ETH-USD"), rsi("XRP-USD")
    except: pass
    return btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc_p, eth_p, xrp_p, usdmxn, *_ = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/usdmxn)/btc_p,"eth":(333.33/usdmxn)/eth_p,"xrp":(333.33/usdmxn)/xrp_p,"inicial":1000.0,"stoploss":7.0, "auto":False, "ultima_auto":0, "precio_compra":{"btc":btc_p,"eth":eth_p,"xrp":xrp_p}}
        save_data(data)
    u=data["users"][uid]
    if "stoploss" not in u: u["stoploss"]=7.0
    if "auto" not in u: u["auto"]=False
    if "ultima_auto" not in u: u["ultima_auto"]=0
    if "precio_compra" not in u:
        btc_p, eth_p, xrp_p, *_ = get_market()
        u["precio_compra"]={"btc":btc_p,"eth":eth_p,"xrp":xrp_p}
    return u

def texto(u):
    btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr = get_market()
    total = u['efectivo']+u['btc']*btc_p*usdmxn+u['eth']*eth_p*usdmxn+u['xrp']*xrp_p*usdmxn
    gan = (total-u['inicial'])/u['inicial']*100
    modo = "🤖 AUTO ON" if u['auto'] else "💤 AUTO OFF"
    return f"DEMO $1000 | SL:-{u['stoploss']:.0f}% | {modo}\nUSD/MXN: ${usdmxn:.2f} | Efec: ${u['efectivo']:.2f}\n\nBTC ${btc_p:,.2f} RSI:{br}\nETH ${eth_p:,.2f} RSI:{er}\nXRP ${xrp_p:.2f} RSI:{xr} {'🔥 BARATO' if xr<35 else ''}\n\nTOTAL: ${total:.2f} ({gan:+.1f}%)\nV35.2 FINAL RECOMENDADO"

def kb_main(u):
    auto_txt = "💤 APAGAR AUTO" if u['auto'] else "🤖 PRENDER AUTO"
    return InlineKeyboardMarkup([ [InlineKeyboardButton("🟢 COMPRAR", callback_data="menu_c"), InlineKeyboardButton("🔴 VENDER", callback_data="menu_v")], [InlineKeyboardButton(f"🛑 SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(auto_txt, callback_data="toggle_auto")], [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="act")] ])
def kb_c(): return InlineKeyboardMarkup([ [InlineKeyboardButton("XRP $100", callback_data="c_xrp_100"), InlineKeyboardButton("BTC $100", callback_data="c_btc_100")], [InlineKeyboardButton("⬅️ Volver", callback_data="act")] ])
def kb_sl(): return InlineKeyboardMarkup([ [InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7% RECOM", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")], [InlineKeyboardButton("⬅️ Volver", callback_data="act")] ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=load_data(); u=get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u), reply_markup=kb_main(u))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=load_data(); uid=str(q.from_user.id); u=get_user(uid, data)
    btc_p, eth_p, xrp_p, usdmxn, *_ = get_market()
    precios={"btc":btc_p,"eth":eth_p,"xrp":xrp_p}
    d=q.data
    if d=="act": await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d=="menu_c": await q.edit_message_text("¿Qué COMPRAS?", reply_markup=kb_c()); return
    if d=="menu_v": await q.edit_message_text("Usa /vender xrp todo para vender", reply_markup=kb_main(u)); return
    if d=="menu_sl": await q.edit_message_text(f"Tu Stop-Loss: -{u['stoploss']}%\nRecomendado -7% para cripto", reply_markup=kb_sl()); return
    if d=="toggle_auto":
        u["auto"]=not u["auto"]; data["users"][uid]=u; save_data(data)
        txt="✅ AUTO PRENDIDO" if u["auto"] else "💤 AUTO APAGADO - Recomendado dejar OFF por ahora"
        await q.edit_message_text(f"{txt}\n\n{texto(u)}", reply_markup=kb_main(u)); return
    if d.startswith("sl_"):
        v=float(d.split("_")[1]); u["stoploss"]=v; data["users"][uid]=u; save_data(data)
        await q.edit_message_text(f"✅ Stop-Loss: -{v}%\n\n{texto(u)}", reply_markup=kb_main(u)); return
    if d.startswith("c_"):
        _, mon, _ = d.split("_")
        if u['efectivo'] < 100: await q.edit_message_text(f"Sin efectivo\n\n{texto(u)}", reply_markup=kb_main(u)); return
        qty=(100/usdmxn)/precios[mon]; u[mon]+=qty; u['efectivo']-=100; u['precio_compra'][mon]=precios[mon]
        data["users"][uid]=u; save_data(data)
        await q.edit_message_text(texto(u), reply_markup=kb_main(u))

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

def vigilante():
    while True:
        try:
            time.sleep(180)
            btc_p, eth_p, xrp_p, usdmxn, bp, ep, xp, br, er, xr = get_market()
            data=load_data()
            precios={"btc":btc_p,"eth":eth_p,"xrp":xrp_p}
            rsis={"btc":br,"eth":er,"xrp":xr}
            for uid, u in list(data["users"].items()):
                u=get_user(uid, data)
                for mon in ["btc","eth","xrp"]:
                    if u[mon] > 0:
                        compra = u["precio_compra"].get(mon, precios[mon])
                        perdida = (precios[mon]-compra)/compra*100
                        if perdida <= -u["stoploss"]:
                            qty=u[mon]; mxn=qty*precios[mon]*usdmxn
                            u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data)
                            send_telegram(uid, f"🛑 STOP-LOSS {mon.upper()} {perdida:.1f}%\nSalvaste ${mxn:.2f}\n\n{texto(u)}")
                if u["auto"] and (time.time() - u.get("ultima_auto",0) > 3600):
                    for mon in ["xrp","btc","eth"]:
                        rsi = rsis[mon]
                        if rsi < 28 and u['efectivo'] >= 100:
                            qty=(100/usdmxn)/precios[mon]
                            u[mon]+=qty; u['efectivo']-=100; u['precio_compra'][mon]=precios[mon]; u["ultima_auto"]=time.time()
                            data["users"][uid]=u; save_data(data)
                            send_telegram(uid, f"🤖 AUTO-COMPRA {mon.upper()} $100 RSI {rsi} <28\n{texto(u)}")
                            break
                        if rsi > 72 and u[mon] > 0:
                            qty=u[mon]; mxn=qty*precios[mon]*usdmxn
                            u[mon]=0; u['efectivo']+=mxn; u["ultima_auto"]=time.time()
                            data["users"][uid]=u; save_data(data)
                            send_telegram(uid, f"🤖 AUTO-VENTA {mon.upper()} RSI {rsi} >72\n{texto(u)}")
                            break
        except: time.sleep(60)

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=vigilante, daemon=True).start()
    app_ = Application.builder().token(BOT_TOKEN).build()
    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CommandHandler("balance", start))
    app_.add_handler(CallbackQueryHandler(btn))
    print("V35.2 FINAL -7% OK")
    app_.run_polling()
