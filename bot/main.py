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
KEY = "btc-vicente-v36-grafica-tp"

app = Flask(__name__)
@app.route('/')
def home(): return "V36 GRAFICA TP OK"

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
    btc_p, eth_p, xrp_p, usdmxn = 64312.0, 1902.0, 1.04, 17.20
    bp, ep, xp, br, er, xr = 0.0, 0.0, 0.0, 45.9, 53.1, 32.2
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
        data["users"][uid] = {"efectivo":0.0,"btc":(333.33/usdmxn)/btc_p,"eth":(333.33/usdmxn)/eth_p,"xrp":(333.33/usdmxn)/xrp_p,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0, "auto":False, "ultima_auto":0, "precio_compra":{"btc":btc_p,"eth":eth_p,"xrp":xrp_p}}
        save_data(data)
    u=data["users"][uid]
    if "stoploss" not in u: u["stoploss"]=7.0
    if "takeprofit" not in u: u["takeprofit"]=10.0
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
    modo = "🤖 ON" if u['auto'] else "OFF"
    return f"DEMO $1000 | SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}% | AUTO {modo}\nUSD/MXN: ${usdmxn:.2f} | Efec: ${u['efectivo']:.2f}\n\nBTC ${btc_p:,.2f} RSI:{br}\nETH ${eth_p:,.2f} RSI:{er}\nXRP ${xrp_p:.2f} RSI:{xr} {'🔥' if xr<35 else ''}\n\nTOTAL: ${total:.2f} ({gan:+.1f}%)\nV36 GRAFICA+TP"

def kb_main(u):
    auto_txt = "💤 AUTO OFF" if not u['auto'] else "🤖 AUTO ON"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 COMPRAR", callback_data="menu_c"), InlineKeyboardButton("🔴 VENDER", callback_data="menu_v")],
        [InlineKeyboardButton(f"🛑 SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"💰 TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")],
        [InlineKeyboardButton("📊 GRAFICA", callback_data="grafica"), InlineKeyboardButton(auto_txt, callback_data="toggle_auto")],
        [InlineKeyboardButton("🔄 ACTUALIZAR", callback_data="act")]
    ])
def kb_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("XRP $100", callback_data="c_xrp_100"), InlineKeyboardButton("BTC $100", callback_data="c_btc_100")], [InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_sl(): return InlineKeyboardMarkup([[InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")], [InlineKeyboardButton("⬅️ Volver", callback_data="act")]])
def kb_tp(): return InlineKeyboardMarkup([[InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+
