import os, json, requests, threading, time
from flask import Flask
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY = "btc-vicente-v36-ok"
app = Flask(__name__)
@app.route('/')
def home(): return "V36 OK"

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
        btc = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        fx = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        return btc, eth, xrp, fx
    except:
        return 64408.0, 1904.0, 1.04, 17.20

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc, eth, xrp, fx = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":15.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp}}
        save_data(data)
    u=data["users"][uid]
    if "takeprofit" not in u: u["takeprofit"]=15.0
    if "precio_compra" not in u:
        btc, eth, xrp, fx = get_market()
        u["precio_compra"]={"btc":btc,"eth":eth,"xrp":xrp}
    return u

def texto(u):
    btc, eth, xrp, fx = get_market()
    total = u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp*fx
    gan = (total-u['inicial'])/u['inicial']*100
    return f"DEMO $1000 | SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nUSD/MXN: ${fx:.2f}\nBTC ${btc:,.2f}\nETH ${eth:,.2f}\nXRP ${xrp:.2f}\nTOTAL: ${total:.2f} ({gan:+.1f}%)\nV36 TP 15%"

def kb_main(u):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🛑 SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"💰 TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="act")]
    ])

def kb_sl(): return InlineKeyboardMarkup([[InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_tp(): return InlineKeyboardMarkup([[InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+15%", callback_data="tp_15"), InlineKeyboardButton("+20%", callback_data="tp_20")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])

def send_msg(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=load_data(); u=get_user(update.effective_user.id, data)
    await update.message.reply_text(texto(u), reply_markup=kb_main(u))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=load_data(); uid=str(q.from_user.id); u=get_user(uid, data)
    d=q.data
    if d=="act": await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d=="menu_sl": await q.edit_message_text(f"SL: -{u['stoploss']}%", reply_markup=kb_sl()); return
    if d=="menu_tp": await q.edit_message_text(f"TP: +{u['takeprofit']}%", reply_markup=kb_tp()); return
    if d.startswith("sl_"): u["stoploss"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return
    if d.startswith("tp_"): u["takeprofit"]=float(d.split("_")[1]); data["users"][uid]=u; save_data(data); await q.edit_message_text(texto(u), reply_markup=kb_main(u)); return

def vigilante():
    while True:
        try:
            time.sleep(180)
