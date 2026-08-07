import os, json, requests, threading, time, math
from flask import Flask
import yfinance as yf
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
def home(): return "V36.2 GRAFICA FIX OK"

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

def calc_rsi(symbol):
    try:
        h = yf.Ticker(symbol).history(period="1mo")['Close']
        if len(h) < 15: return 40.0
        d = h.diff()
        g = d.where(d>0,0).rolling(14).mean()
        l = -d.where(d<0,0).rolling(14).mean()
        rs = g.iloc[-1]/l.iloc[-1] if l.iloc[-1]!=0 else 0
        rsi = 100-(100/(1+rs)) if rs!=0 else 50.0
        return round(float(rsi),1) if not math.isnan(rsi) else 40.0
    except:
        return 40.0

def get_market():
    try:
        btc = float(yf.Ticker("BTC-USD").fast_info['last_price'])
        eth = float(yf.Ticker("ETH-USD").fast_info['last_price'])
        xrp = float(yf.Ticker("XRP-USD").fast_info['last_price'])
        fx = float(yf.Ticker("USDMXN=X").fast_info['last_price'])
        br = calc_rsi("BTC-USD")
        er = calc_rsi("ETH-USD")
        xr = calc_rsi("XRP-USD")
        return btc, eth, xrp, fx, br, er, xr
    except:
        return 64241.0, 1897.0, 1.03, 17.20, 45.5, 52.5, 32.0

def get_user(uid, data):
    uid=str(uid)
    if uid not in data["users"]:
        btc, eth, xrp, fx, *_ = get_market()
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp}}
        save_data(data)
    u=data["users"][uid]
    if "takeprofit" not in u: u["takeprofit"]=10.0
    return u

def texto(u):
    btc, eth, xrp, fx, br, er, xr = get_market()
    total = u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp*fx
    gan = (total-u['inicial'])/u['inicial']*100
    return f"DEMO $1000 | SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nUSD/MXN: ${fx:.2f} | Efec: ${u['efectivo']:.2f}\n\nBTC ${btc:,.2f} RSI:{br}\nETH ${eth:,.2f} RSI:{er}\nXRP ${xrp:.2f} RSI:{xr} {'🔥 BARATO' if xr<35 else ''}\n\nTOTAL: ${total:.2f} ({gan:+.1f}%)\nV36.2 GRAFICA FIX"

def kb_main(u):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 COMPRAR", callback_data="menu_c"), InlineKeyboardButton("🔴 VENDER", callback_data="menu_v")],
        [InlineKeyboardButton(f"🛑 SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"💰 TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")],
        [InlineKeyboardButton("📊 GRAFICA 7D", callback_data="grafica")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="act")]
    ])

def kb_sl(): return InlineKeyboardMarkup([[InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_tp(): return InlineKeyboardMarkup([[InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+15%", callback_data="tp_15"), InlineKeyboardButton("+20%", callback_data="tp_20")],[InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("XRP $100", callback_data="c_xrp_
