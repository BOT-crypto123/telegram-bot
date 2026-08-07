import os, json, requests, threading, time, math
from flask import Flask
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v36-1-final"
app = Flask(__name__)
@app.route('/')
def home(): return "V36.4 COINGECKO OK"

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
        # CoinGecko - gratis y no bloquea
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd", timeout=10).json()
        btc = float(r['bitcoin']['usd'])
        eth = float(r['ethereum']['usd'])
        xrp = float(r['ripple']['usd'])
        # Dolar
        try:
            fx = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()['rates']['MXN']
        except:
            fx = 17.20
        return btc, eth, xrp, fx, 45.5, 52.5, 32.0
    except Exception as e:
        print(f"Error market coingecko: {e}")
        return 115000.0, 3800.0, 2.20, 17.20, 45.5, 52.5, 32.0

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc, eth, xrp, fx, *_ = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp}}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc, eth, xrp, fx, br, er, xr = get_market()
    total = u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp*fx
    gan = (total-u['inicial'])/u['inicial']*100
    return f"DEMO $1000 | SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nUSD/MXN: ${fx:.2f} Efec: ${u['efectivo']:.2f}\n\nBTC ${btc:,.2f}\nETH ${eth:,.2f}\nXRP ${xrp:.2f} {'🔥 BARATO' if xrp<2 else ''}\n\nTOTAL: ${total:.2f} ({gan:+.1f}%)\nV36.4 COINGECKO"

def kb_main(u): return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 COMPRAR", callback_data="menu_c"), InlineKeyboardButton("🔴 VENDER", callback_data="menu_v")],[InlineKeyboardButton(f"🛑 SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"💰 TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")],[InlineKeyboardButton("📊 GRAFICA 7D", callback_data="grafica")],[InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="act")]])
def kb_sl(): return InlineKeyboardMarkup([[InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_tp(): return InlineKeyboardMarkup([[InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+15%", callback_data="tp_15"), InlineKeyboardButton("+20%", callback_data="tp_20")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("XRP $100", callback_data="c_xrp_100"), InlineKeyboardButton("BTC $100", callback_data="c_btc_100")],[InlineKeyboardButton("ETH $100", callback_data="c_eth_100")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_v(): return InlineKeyboardMarkup([[InlineKeyboardButton("Vender XRP", callback_data="v_xrp"), InlineKeyboardButton("Vender BTC", callback_data="v_btc")],[InlineKeyboardButton("Vender ETH", callback_data="v_eth")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])

def crear_grafica():
    path="/tmp/chart.png"
    try:
        plt.figure(figsize=(10,5))
        # Usamos CoinGecko para grafica 7 dias
        for coin_id, name, color in [("bitcoin","BTC","#f7931a"), ("ethereum","ETH","#627eea"), ("ripple","XRP","#23292f")]:
            try:
                r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=7", timeout=15).json()
                prices = r['prices'] # [[timestamp, price],...]
                if len(prices)>10:
                    # Convertir timestamp
                    times = [datetime.fromtimestamp(p[0]/1000) for p in prices]
                    vals = [p[1] for p in prices]
                    first = vals[0]
                    norm = [(v/first*100)-100 for v in vals]
                    plt.plot(times, norm, label=f"{name} {norm[-1]:+.1f}%", color=color, linewidth=2)
            except Exception as e:
                print(f"Error grafica {name}: {e}")
        plt.title("BTC / ETH / XRP - 7 dias (% cambio) - CoinGecko", fontsize=11, fontweight='bold')
        plt.legend(); plt.grid(True, alpha=0.3); plt.ylabel("% cambio"); plt.xticks(rotation=20)
        plt.tight_layout(); plt.savefig(path); plt.close()
        return path
    except Exception as e:
        print(f"Error grafica general: {e}")
        try:
            plt.figure(figsize=(8,4)); plt.text(0.5,0.5,"Error temporal\nIntenta en 1 min", ha='center', va='center'); plt.axis('off'); plt.savefig(path); plt.close()
            return path
        except: return None

def send_msg(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=load_data(); u=get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u), reply_markup=kb_main(u))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=load_data(); uid=str(q.from_user.id); u=get_user(uid, data)
    btc, eth, xrp, fx, *_ = get_market()
    precios={"btc":btc,"eth":eth,"xrp":xrp}
    d=q.data
    if d=="act": await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d=="menu_c": await q.edit_message_text("¿Qué compras?", reply_markup=kb_c()); return
    if d=="menu_v": await q.edit_message_text("¿Qué vendes?", reply_markup=kb_v()); return
    if d=="menu_sl": await q.edit_message_text(f"SL: -{u['stoploss']}%", reply_markup=kb_sl()); return
    if d=="menu_tp": await q.edit_message_text(f"TP: +{u['takeprofit']}%", reply_markup=kb_tp()); return
    if d.startswith("sl_"): u["stoploss"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("tp_"): u["takeprofit"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("c_"):
        _, mon, _ = d.split("_")
        if u['efectivo'] < 100: await q.edit_message_text(f"Sin efectivo\n{texto(u)}", reply_markup=kb_main(u)); return
        qty=(100/fx)/precios[mon]; u[mon]+=qty; u['efectivo']-=100; u['precio_compra'][mon]=precios[mon]; data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("v_"):
        mon=d.split("_")[1]; mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data); await q.edit_message_text(f"Vendido {mon.upper()} ${mxn:.2f}\n\n{texto(u)}", reply_markup=kb_main(u)); return
    if d=="grafica":
        await q.edit_message_text("📊 Generando grafica CoinGecko... 5s")
        path=crear_grafica()
        if path and os.path.exists(path):
            with open(path,'rb') as f: await q.message.reply_photo(photo=f, caption="7 dias BTC/ETH/XRP - % variación (CoinGecko)")
            await q.message.reply_text(texto(u), reply_markup=kb_main(u))
        else:
            await q.message.reply_text("⚠️ Error grafica, intenta en 1 min\n\n"+texto(u), reply_markup=kb_main(u))
        return

def vigilante():
    while True:
        try:
            time.sleep(180)
            btc, eth, xrp, fx, *_ = get_market()
            data=load_data(); precios={"btc":btc,"eth":eth,"xrp":xrp}
            for uid, u in list(data["users"].items()):
                u=get_user(uid, data)
                for mon in ["btc","eth","xrp"]:
                    if u[mon]>0:
                        pct=(precios[mon]-u["precio_compra"].get(mon, precios[mon]))/u["precio_compra"].get(mon, precios[mon])*100
                        if pct <= -u["stoploss"]:
                            mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data)
                            send_msg(uid, f"🛑 STOP-LOSS {mon.upper()} {pct:.1f}%")
                        elif pct >= u["takeprofit"]:
                            mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data)
                            send_msg(uid, f"💰 TAKE-PROFIT {mon.upper()} +{pct:.1f}%")
        except: time.sleep(60)

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=vigilante, daemon=True).start()
    app_ = Application.builder().token(BOT_TOKEN).build()
    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CallbackQueryHandler(btn))
    print("V36.4 OK")
    app_.run_polling()
