import os, json, requests, threading, time
from flask import Flask
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v36-1-final"
app = Flask(__name__)

@app.route('/')
def home():
    return "V36.6 COINBASE OK - LIVE"

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
        btc = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=8).json()['data']['amount'])
        eth = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=8).json()['data']['amount'])
        xrp = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", timeout=8).json()['data']['amount'])
        fx = 18.5
        try:
            fx = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()['rates']['MXN']
        except: pass
        return btc, eth, xrp, fx
    except Exception as e:
        print(f"Market error: {e}")
        return 115000.0, 3800.0, 2.2, 18.5

def get_user(uid, data):
    uid = str(uid)
    if uid not in data["users"]:
        btc, eth, xrp, fx = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp}}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc, eth, xrp, fx = get_market()
    total = u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp*fx
    gan = (total-u['inicial'])/u['inicial']*100
    return f"DEMO $1000 | SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nUSD/MXN: ${fx:.2f} Efec: ${u['efectivo']:.2f}\n\nBTC ${btc:,.2f}\nETH ${eth:,.2f}\nXRP ${xrp:.2f}\n\nTOTAL: ${total:.2f} ({gan:+.1f}%)\nV36.6 COINBASE"

def kb_main(u): return InlineKeyboardMarkup([[InlineKeyboardButton("COMPRAR", callback_data="menu_c"), InlineKeyboardButton("VENDER", callback_data="menu_v")],[InlineKeyboardButton(f"SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")],[InlineKeyboardButton("GRAFICA 7D", callback_data="grafica")],[InlineKeyboardButton("ACTUALIZAR", callback_data="act")]])
def kb_sl(): return InlineKeyboardMarkup([[InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")],[InlineKeyboardButton("Volver", callback_data="act")]])
def kb_tp(): return InlineKeyboardMarkup([[InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+15%", callback_data="tp_15"), InlineKeyboardButton("+20%", callback_data="tp_20")],[InlineKeyboardButton("Volver", callback_data="act")]])
def kb_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("XRP $100", callback_data="c_xrp_100"), InlineKeyboardButton("BTC $100", callback_data="c_btc_100")],[InlineKeyboardButton("ETH $100", callback_data="c_eth_100")],[InlineKeyboardButton("Volver", callback_data="act")]])
def kb_v(): return InlineKeyboardMarkup([[InlineKeyboardButton("Vender XRP", callback_data="v_xrp"), InlineKeyboardButton("Vender BTC", callback_data="v_btc")],[InlineKeyboardButton("Vender ETH", callback_data="v_eth")],[InlineKeyboardButton("Volver", callback_data="act")]])

def crear_grafica():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    path = "/tmp/chart.png"
    try:
        plt.figure(figsize=(10,5))
        for prod, name, color in [("BTC-USD","BTC","#f7931a"), ("ETH-USD","ETH","#627eea"), ("XRP-USD","XRP","#000000")]:
            url = f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=21600"
            data = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
            data = sorted(data, key=lambda x: x[0])
            times = [datetime.fromtimestamp(d[0]) for d in data]
            closes = [float(d[4]) for d in data]
            first = closes[0]
            norm = [(c/first*100)-100 for c in closes]
            plt.plot(times, norm, label=f"{name} {norm[-1]:+.2f}%", color=color, linewidth=2)
        plt.title("BTC/ETH/XRP 7 dias % - Coinbase")
        plt.legend(); plt.grid(True, alpha=0.3); plt.ylabel("%"); plt.xticks(rotation=20); plt.tight_layout()
        plt.savefig(path, dpi=150); plt.close()
        return path
    except Exception as e:
        print(f"Grafica error: {e}")
        return None

def send_msg(cid, txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt}, timeout=10)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data(); u = get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u), reply_markup=kb_main(u))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    data = load_data(); uid = str(q.from_user.id); u = get_user(uid, data)
    btc, eth, xrp, fx = get_market()
    precios = {"btc":btc,"eth":eth,"xrp":xrp}
    d = q.data
    if d == "act": await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d == "menu_c": await q.edit_message_text("Que compras?", reply_markup=kb_c()); return
    if d == "menu_v": await q.edit_message_text("Que vendes?", reply_markup=kb_v()); return
    if d == "menu_sl": await q.edit_message_text(f"SL: -{u['stoploss']}%", reply_markup=kb_sl()); return
    if d == "menu_tp": await q.edit_message_text(f"TP: +{u['takeprofit']}%", reply_markup=kb_tp()); return
    if d.startswith("sl_"): u["stoploss"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("tp_"): u["takeprofit"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("c_"):
        mon=d.split("_")[1]
        if u['efectivo']<100: await q.edit_message_text(f"Sin efectivo\n{texto(u)}", reply_markup=kb_main(u)); return
        qty=(100/fx)/precios[mon]; u[mon]+=qty; u['efectivo']-=100; u['precio_compra'][mon]=precios[mon]; data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("v_"):
        mon=d.split("_")[1]; mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data); await q.edit_message_text(f"Vendido {mon.upper()} ${mxn:.2f}\n\n{texto(u)}", reply_markup=kb_main(u)); return
    if d == "grafica":
        await q.edit_message_text("Generando grafica Coinbase... 5s")
        path=crear_grafica()
        if path:
            with open(path,'rb') as f: await q.message.reply_photo(photo=f, caption="7 dias BTC/ETH/XRP % - Coinbase")
            await q.message.reply_text(texto(u), reply_markup=kb_main(u))
        else: await q.message.reply_text("Error grafica\n\n"+texto(u), reply_markup=kb_main(u))
        return

def run_flask():
    # Flask en hilo aparte
    port = int(os.environ.get("PORT", 10000))
    print(f"Flask en puerto {port}")
    app.run(host='0.0.0.0', port=port)

def main_bot():
    # Bot con auto-reinicio si falla
    while True:
        try:
            print("Iniciando bot Telegram...")
            app_ = Application.builder().token(BOT_TOKEN).build()
            app_.add_handler(CommandHandler("start", start))
            app_.add_handler(CallbackQueryHandler(btn))
            print("Bot corriendo")
            app_.run_polling(close_loop=False, stop_signals=None)
        except Exception as e:
            print(f"Bot crash: {e} - reiniciando en 10s")
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    # vigilante en hilo
    def vigilante():
        while True:
            try:
                time.sleep(180)
                btc, eth, xrp, fx = get_market()
                data=load_data(); precios={"btc":btc,"eth":eth,"xrp":xrp}
                for uid, u in list(data["users"].items()):
                    u=get_user(uid, data)
                    for mon in ["btc","eth","xrp"]:
                        if u[mon]>0:
                            pct=(precios[mon]-u["precio_compra"].get(mon, precios[mon]))/u["precio_compra"].get(mon, precios[mon])*100
                            if pct <= -u["stoploss"]:
                                mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data); send_msg(uid, f"STOP {mon.upper()} {pct:.1f}%")
                            elif pct >= u["takeprofit"]:
                                mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data); send_msg(uid, f"TP {mon.upper()} +{pct:.1f}%")
            except: time.sleep(60)
    threading.Thread(target=vigilante, daemon=True).start()
    main_bot()
