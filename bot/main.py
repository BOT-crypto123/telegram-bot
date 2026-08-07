import os, sys, traceback, json, requests, threading, time, asyncio
from flask import Flask
from datetime import datetime

print("=== V38.3 AUTO-DETECT ===")
# AUTO DETECTA TOKEN - busca cualquier variable que tenga TELEGRAM y TOKEN
BOT_TOKEN = None
for k,v in os.environ.items():
    if "TELE" in k.upper() and "TOKEN" in k.upper():
        BOT_TOKEN = v
        print(f"Encontrado token en {k}")
        break
    if k.upper() == "BOT_TOKEN":
        BOT_TOKEN = v
        break
if not BOT_TOKEN:
    BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")

URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
# Auto detecta si estan en minusculas
if not URL:
    for k,v in os.environ.items():
        if "UPSTASH" in k.upper() and "URL" in k.upper():
            URL=v
for k,v in os.environ.items():
    if "UPSTASH" in k.upper() and "TOKEN" in k.upper() and "REDIS" in k.upper():
        if v!=BOT_TOKEN:
            REST_TOKEN=v

print(f"BOT_TOKEN: {bool(BOT_TOKEN)} URL: {bool(URL)} TOKEN: {bool(REST_TOKEN)}")

KEY = "btc-vicente-v36-1-final"
app = Flask(__name__)
@app.route('/')
def home():
    return f"V38.3 LIVE - BOT:{bool(BOT_TOKEN)} URL:{bool(URL)}"

def load_data():
    try:
        if not URL or not REST_TOKEN: return {"users":{}}
        r = requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res = r.json().get("result")
        if res: return json.loads(res)
    except: pass
    return {"users":{}}

def save_data(data):
    try:
        if not URL or not REST_TOKEN: return
        requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["SET", KEY, json.dumps(data)], timeout=10)
    except: pass

def get_market():
    try:
        btc = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=8).json()['data']['amount'])
        eth = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=8).json()['data']['amount'])
        xrp = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", timeout=8).json()['data']['amount'])
        fx=17.22
        try: fx=requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()['rates']['MXN']
        except: pass
        return btc,eth,xrp,fx
    except: return 64273.0,1900.0,1.03,17.22

def get_user(uid,data):
    uid=str(uid)
    if uid not in data["users"]:
        btc,eth,xrp,fx=get_market()
        data["users"][uid]={"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp}}
        save_data(data)
    return data["users"][uid]

def texto(u):
    btc,eth,xrp,fx=get_market()
    total=u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp*fx
    gan=(total-u['inicial'])/u['inicial']*100
    return f"V38.3 PRO MAX AUTO\nSL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nUSD/MXN:${fx:.2f} Efec:${u['efectivo']:.2f}\nBTC ${btc:,.0f} ETH ${eth:,.0f} XRP ${xrp:.2f}\nTOTAL:${total:.2f} ({gan:+.1f}%)"

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
def kb_main(u):
    return InlineKeyboardMarkup([ [InlineKeyboardButton("COMPRAR", callback_data="menu_c"), InlineKeyboardButton("VENDER", callback_data="menu_v")], [InlineKeyboardButton(f"SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")], [InlineKeyboardButton("GRAFICA 7D", callback_data="grafica"), InlineKeyboardButton("PRO MAX", callback_data="pro")], [InlineKeyboardButton("ACTUALIZAR", callback_data="act")] ])
def kb_pro():
    return InlineKeyboardMarkup([ [InlineKeyboardButton("BTC PRO", callback_data="pro_btc"), InlineKeyboardButton("ETH PRO", callback_data="pro_eth")], [InlineKeyboardButton("XRP PRO", callback_data="pro_xrp")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_sl():
    return InlineKeyboardMarkup([ [InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_tp():
    return InlineKeyboardMarkup([ [InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+15%", callback_data="tp_15"), InlineKeyboardButton("+20%", callback_data="tp_20")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_c():
    return InlineKeyboardMarkup([ [InlineKeyboardButton("XRP $100", callback_data="c_xrp_100"), InlineKeyboardButton("BTC $100", callback_data="c_btc_100")], [InlineKeyboardButton("ETH $100", callback_data="c_eth_100")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_v():
    return InlineKeyboardMarkup([ [InlineKeyboardButton("Vender XRP", callback_data="v_xrp"), InlineKeyboardButton("Vender BTC", callback_data="v_btc")], [InlineKeyboardButton("Vender ETH", callback_data="v_eth")], [InlineKeyboardButton("Volver", callback_data="act")] ])

def crear_grafica_pro(moneda="BTC-USD"):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    path="/tmp/pro.png"
    url=f"https://api.exchange.coinbase.com/products/{moneda}/candles?granularity=3600"
    data=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
    data=sorted(data, key=lambda x:x[0])[-168:]
    times=[datetime.fromtimestamp(d[0]) for d in data]
    closes=[float(d[4]) for d in data]
    ma7=[sum(closes[i-7:i])/7 if i>=7 else closes[i] for i in range(len(closes))]
    ma25=[sum(closes[i-25:i])/25 if i>=25 else closes[i] for i in range(len(closes))]
    deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains=[max(0,d) for d in deltas]; losses=[max(0,-d) for d in deltas]
    avg_g=sum(gains[:14])/14; avg_l=sum(losses[:14])/14
    rsi=[50]*14
    for i in range(14,len(deltas)):
        avg_g=(avg_g*13+gains[i])/14; avg_l=(avg_l*13+losses[i])/14
        rs=avg_g/(avg_l if avg_l!=0 else 0.001); rsi.append(100-(100/(1+rs)))
    plt.style.use('dark_background')
    fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,7),gridspec_kw={'height_ratios':[3,1]})
    fig.patch.set_facecolor('#0e0e0e'); ax1.set_facecolor('#0e0e0e'); ax2.set_facecolor('#0e0e0e')
    ax1.plot(times,closes,color='#00ff88',linewidth=2,label=moneda); ax1.plot(times,ma7,color='#ffaa00',linewidth=1,label='MA7'); ax1.plot(times,ma25,color='#ff00ff',linewidth=1,label='MA25')
    ax1.legend(); ax1.grid(True,alpha=0.2); ax1.set_title(f"{moneda} PRO MAX DARK",color='white')
    ax2.plot(times[-len(rsi):],rsi,color='#00aaff',linewidth=2); ax2.axhline(70,color='red',linestyle='--'); ax2.axhline(30,color='green',linestyle='--'); ax2.set_ylim(0,100); ax2.set_title(f"RSI {rsi[-1]:.1f} - {'SOBRECOMPRADO' if rsi[-1]>70 else 'SOBREVENDIDO' if rsi[-1]<30 else 'NEUTRAL'}",color='white'); ax2.grid(True,alpha=0.2)
    plt.tight_layout(); plt.savefig(path,dpi=150,facecolor='#0e0e0e'); plt.close(); plt.style.use('default')
    return path,rsi[-1]

def crear_grafica_7d():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    path="/tmp/chart.png"; plt.figure(figsize=(10,5))
    for prod,name,color in [("BTC-USD","BTC","#f7931a"),("ETH-USD","ETH","#627eea"),("XRP-USD","XRP","black")]:
        url=f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=3600"
        data=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=15).json()
        data=sorted(data,key=lambda x:x[0])[-168:]; times=[datetime.fromtimestamp(d[0]) for d in data]; closes=[float(d[4]) for d in data]; norm=[(c/closes[0]*100)-100 for c in closes]
        plt.plot(times,norm,label=f"{name} {norm[-1]:+.2f}%",color=color,linewidth=2)
    plt.title("7 Dias %"); plt.legend(); plt.grid(True,alpha=0.3); plt.tight_layout(); plt.savefig(path,dpi=150); plt.close()
    return path

def start_bot_thread():
    if not BOT_TOKEN:
        print("ERROR: No se encontro BOT_TOKEN")
        return
    loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    from telegram import Update
    async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
        data=load_data(); u=get_user(update.effective_user.id,data)
        await update.message.reply_text(texto(u),reply_markup=kb_main(u))
    async def btn(update:Update,context:ContextTypes.DEFAULT_TYPE):
        q=update.callback_query; await q.answer()
        data=load_data(); uid=str(q.from_user.id); u=get_user(uid,data)
        btc,eth,xrp,fx=get_market(); precios={"btc":btc,"eth":eth,"xrp":xrp}; d=q.data
        if d=="act": await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
        if d=="menu_c": await q.edit_message_text("Que compras?",reply_markup=kb_c()); return
        if d=="menu_v": await q.edit_message_text("Que vendes?",reply_markup=kb_v()); return
        if d=="menu_sl": await q.edit_message_text(f"SL -{u['stoploss']}%",reply_markup=kb_sl()); return
        if d=="menu_tp": await q.edit_message_text(f"TP +{u['takeprofit']}%",reply_markup=kb_tp()); return
        if d=="pro": await q.edit_message_text("PRO MAX:",reply_markup=kb_pro()); return
        if d.startswith("sl_"): u["stoploss"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
        if d.startswith("tp_"): u["takeprofit"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
        if d.startswith("c_"):
            mon=d.split("_")[1]
            if u['efectivo']<100: await q.edit_message_text(f"Sin efectivo\n{texto(u)}",reply_markup=kb_main(u)); return
            qty=(100/fx)/precios[mon]; u[mon]+=qty; u['efectivo']-=100; data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
        if d.startswith("v_"):
            mon=d.split("_")[1]; mxn=u[mon]*precios[mon]*fx; u[mon]=0; u['efectivo']+=mxn; data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
        if d=="grafica":
            try:
                await q.edit_message_text("Generando 7D...")
                path=crear_grafica_7d()
                with open(path,'rb') as f: await q.message.reply_photo(photo=f,caption="7D %")
                await q.message.reply_text(texto(u),reply_markup=kb_main(u))
            except Exception as e: await q.edit_message_text(f"Error: {e}\n{texto(u)}",reply_markup=kb_main(u))
            return
        if d.startswith("pro_"):
            try:
                mon=d.split("_")[1]; mapa={"btc":"BTC-USD","eth":"ETH-USD","xrp":"XRP-USD"}
                await q.edit_message_text(f"Generando {mon.upper()} PRO...")
                path,rsi_val=crear_grafica_pro(mapa[mon])
                with open(path,'rb') as f: await q.message.reply_photo(photo=f,caption=f"{mon.upper()} RSI {rsi_val:.1f}")
                await q.message.reply_text(texto(u),reply_markup=kb_main(u))
            except Exception as e: traceback.print_exc(); await q.edit_message_text(f"Error PRO: {e}\n{texto(u)}",reply_markup=kb_main(u))
            return
    async def main_async():
        app_bot=Application.builder().token(BOT_TOKEN).build()
        app_bot.add_handler(CommandHandler("start",start))
        app_bot.add_handler(CallbackQueryHandler(btn))
        await app_bot.initialize(); await app_bot.start(); await app_bot.updater.start_polling()
        print("Bot V38.3 OK")
        while True: await asyncio.sleep(3600)
    while True:
        try: loop.run_until_complete(main_async())
        except Exception as e: print(f"Crash: {e}"); traceback.print_exc(); time.sleep(5)

threading.Thread(target=start_bot_thread,daemon=True).start()
print("Thread lanzado")
if __name__ == "__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host='0.0.0.0',port=port)
