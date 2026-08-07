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
def home(): return "V36.6 COINBASE OK"

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
        # COINBASE - funciona desde USA / Render
        btc = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5).json()['data']['amount'])
        eth = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=5).json()['data']['amount'])
        xrp = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", timeout=5).json()['data']['amount'])
        fx = 18.5
        try:
            fx = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()['rates']['MXN']
        except: pass
        print(f"Precios Coinbase: BTC {btc} ETH {eth} XRP {xrp}")
        return btc, eth, xrp, fx
    except Exception as e:
        print(f"Error market: {e}")
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
        # Coinbase candles - 7 dias, cada 6 horas
        for prod, name, color in [("BTC-USD","BTC","#f7931a"), ("ETH-USD","ETH","#627eea"), ("XRP-USD","XRP","#000000")]:
            try:
                url = f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=21600"
                headers = {"User-Agent":"Mozilla/5.0"}
                data = requests.get(url, headers=headers, timeout=10).json()
                # data = [[time, low, high, open, close, volume],...] mas reciente primero
                data = sorted(data, key=lambda x: x[0])
                if len(data) > 10:
                    times = [datetime.fromtimestamp(d[0]) for d in data]
                    closes = [float(d[4]) for d in data]
                    first = closes[0]
                    norm = [(c/first*100)-100 for c in closes]
                    plt.plot(times, norm, label=f"{name} {norm[-1]:+.2f}%", color=color, linewidth=2)
                    print(f"{name} {len(closes)} ok")
            except Exception as e:
                print(f"Error {name}: {e}")
        plt.title("BTC/ETH/XRP 7 dias % - Coinbase")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylabel("% cambio")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        return path
    except Exception as e:
        print(f"Error grafica general: {e}")
        return None

def send_msg(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data(); u = get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u), reply_markup=kb_main(u))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q
