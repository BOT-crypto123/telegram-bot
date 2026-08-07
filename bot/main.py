import os, sys, traceback, json, requests, threading, time, asyncio
from flask import Flask
from datetime import datetime
print("=== V39.4 FIX ===")
BOT_TOKEN=None
for k,v in os.environ.items():
    if "TELE" in k.upper() and "TOKEN" in k.upper():
        BOT_TOKEN=v
        break
if not BOT_TOKEN:
    BOT_TOKEN=os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
    if "UPSTASH" in k.upper() and "URL" in k.upper(): URL=v
    if "UPSTASH" in k.upper() and "TOKEN" in k.upper() and "REDIS" in k.upper() and v!=BOT_TOKEN: REST_TOKEN=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route('/')
def home(): return "V39.4 LIVE"
def load_data():
    try:
        if not URL or not REST_TOKEN: return {"users":{}}
        r=requests.post(URL, headers={"Authorization": f"Bearer {REST_TOKEN}"}, json=["GET", KEY], timeout=10)
        res=r.json().get("result")
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
        btc=float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=8).json()['data']['amount'])
        eth=float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=8).json()['data']['amount'])
        xrp=float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", timeout=8).json()['data']['amount'])
        fx=17.22
        try: fx=requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()['rates']['MXN']
        except: pass
        return btc,eth,xrp,fx
    except: return 64280.0,1898.0,1.02,17.22
def get_user(uid,data):
    uid=str(uid)
    if uid not in data["users"]:
        btc,eth,xrp,fx=get_market()
        data["users"][uid]={"efectivo":0.0,"btc":(333.33/fx)/btc,"eth":(333.33/fx)/eth,"xrp":(333.33/fx)/xrp,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":btc,"eth":eth,"xrp":xrp},"alertas":True,"ultima_alerta":{}}
        save_data(data)
    u=data["users"][uid]
    if "alertas" not in u: u["alertas"]=True
    if "ultima_alerta" not in u: u["ultima_alerta"]={}
    if "precio_compra" not in u:
        btc,eth,xrp,fx=get_market()
        u["precio_compra"]={"btc":btc,"eth":eth,"xrp":xrp}
    return u
def texto(u):
    btc,eth,xrp,fx=get_market()
    total=u['efectivo']+u['btc']*btc*fx+u['eth']*eth*fx+u['xrp']*xrp*fx
    gan=(total-u['inicial'])/u['inicial']*100
    al="ON" if u.get("alertas") else "OFF"
    return f"V39.4 {al} SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nUSD/MXN:${fx:.2f} Efec:${u['efectivo']:.2f}\nBTC ${btc:,.0f} ETH ${eth:,.0f} XRP ${xrp:.2f}\nTOTAL:${total:.2f} ({gan:+.1f}%)"
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
def kb_main(u):
    txt="Apagar" if u.get("alertas") else "Prender"
    return InlineKeyboardMarkup([ [InlineKeyboardButton("COMPRAR", callback_data="menu_c"), InlineKeyboardButton("VENDER", callback_data="menu_v")], [InlineKeyboardButton(f"SL -{u['stoploss']:.0f}%", callback_data="menu_sl"), InlineKeyboardButton(f"TP +{u['takeprofit']:.0f}%", callback_data="menu_tp")], [InlineKeyboardButton("GRAFICA 7D", callback_data="grafica"), InlineKeyboardButton("PRO MAX", callback_data="pro")], [InlineKeyboardButton(txt, callback_data="toggle_alert")], [InlineKeyboardButton("ACTUALIZAR", callback_data="act")] ])
def kb_pro(): return InlineKeyboardMarkup([ [InlineKeyboardButton("BTC PRO", callback_data="pro_btc"), InlineKeyboardButton("ETH PRO", callback_data="pro_eth")], [InlineKeyboardButton("XRP PRO", callback_data="pro_xrp")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_sl(): return InlineKeyboardMarkup([ [InlineKeyboardButton("-5%", callback_data="sl_5"), InlineKeyboardButton("-7%", callback_data="sl_7"), InlineKeyboardButton("-10%", callback_data="sl_10")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_tp(): return InlineKeyboardMarkup([ [InlineKeyboardButton("+10%", callback_data="tp_10"), InlineKeyboardButton("+15%", callback_data="tp_15"), InlineKeyboardButton("+20%", callback_data="tp_20")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_c(): return InlineKeyboardMarkup([ [InlineKeyboardButton("XRP $100", callback_data="c_xrp_100"), InlineKeyboardButton("BTC $100", callback_data="c_btc_100")], [InlineKeyboardButton("ETH $100", callback_data="c_eth_100")], [InlineKeyboardButton("Volver", callback_data="act")] ])
def kb_v(): return InlineKeyboardMarkup([ [InlineKeyboardButton("Vender XRP", callback_data="v_xrp"), InlineKeyboardButton("Vender BTC", callback_data="v_btc")], [InlineKeyboard
