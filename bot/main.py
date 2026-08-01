import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO VICENTE V8 - NUNCA FALLA 1000MXN", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"
DOLAR = 18.65

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                d=json.load(f)
                if "btc" in d and "mxn" in d["btc"]:
                    return d
        except: pass
    return {"btc": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},"eth": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},"xrp": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0}}

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def get_precios():
    headers = {"User-Agent": "Mozilla/5.0"}

    # Intenta Binance Vision - esta nunca la bloquean
    try:
        url = "https://data-api.binance.vision/api/v3/ticker/24hr?symbols=[\"BTCUSDT\",\"ETHUSDT\",\"XRPUSDT\"]"
        r = requests.get(url, headers=headers, timeout=10).json()
        # r es lista
        btc = next(x for x in r if x['symbol']=='BTCUSDT')
        eth = next(x for x in r if x['symbol']=='ETHUSDT')
        xrp = next(x for x in r if x['symbol']=='XRPUSDT')
        return {
            "btc": (float(btc['lastPrice'])*DOLAR, float(btc['priceChangePercent']), float(btc['lastPrice'])),
            "eth": (float(eth['lastPrice'])*DOLAR, float(eth['priceChangePercent']), float(eth['lastPrice'])),
            "xrp": (float(xrp['lastPrice'])*DOLAR, float(xrp['priceChangePercent']), float(xrp['lastPrice'])),
            "dolar": DOLAR, "fuente": "BINANCE-VISION"
        }
    except Exception as e:
        print(f"fail vision: {e}", flush=True)

    # Intenta Kraken
    try:
        r = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCUSD,ETHUSD,XRPUSD", headers=headers, timeout=10).json()
        btc_u = float(r['result']['XXBTZUSD']['c'][0])
        eth_u = float(r['result']['XETHZUSD']['c'][0])
        xrp_u = float(r['result']['XXRPZUSD']['c'][0])
        return {"btc":(btc_u*DOLAR,0,btc_u),"eth":(eth_u*DOLAR,0,eth_u),"xrp":(xrp_u*DOLAR,0,xrp_u),"dolar":DOLAR,"fuente":"KRAKEN"}
    except Exception as e:
        print(f"fail kraken: {e}", flush=True)

    # FALLBACK FINAL - nunca falla, te da precios para que /start siempre jale
    print("USANDO PRECIOS DE EMERGENCIA", flush=True)
    return {
        "btc": (2180000.0, 0.5, 117000.0),
        "eth": (72000.0, -0.3, 3850.0),
        "xrp": (58.0, 1.2, 3.10),
        "dolar": DOLAR,
        "fuente": "EMERGENCIA"
    }

def get_keyboard():
    m = types.InlineKeyboardMarkup()
    m.row(types.InlineKeyboardButton("🟢 BTC", callback_data="comprar_btc"), types.InlineKeyboardButton("🟢 ETH", callback_data="comprar_eth"), types.InlineKeyboardButton("🟢 XRP", callback_data="comprar_xrp"))
    m.row(types.InlineKeyboardButton("🔴 BTC", callback_data="vender_btc"), types.InlineKeyboardButton("🔴 ETH", callback_data="vender_eth"), types.InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp"))
    return m

@bot.message_handler(commands=['start','balance'])
def start(msg):
    p = get_precios() # este nunca es None ahora
    c = load_cartera()
    txt = f"⚡ *VICENTE - 3x $1,000 MXN ({p['fuente']})*\nDolar: ${p['dolar']:.2f}\n\n"
    total_global = 0
    for mon in ["btc","eth","xrp"]:
        precio_mxn, cambio, precio_usd = p[mon]
        mxn = c[mon]["mxn"]; coin = c[mon]["coin"]
        valor = coin * precio_mxn + mxn
        total_global += valor
        linea = f"*{mon.upper()}*: ${precio_mxn:,.0f} MXN (${precio_usd:,.2f}) ({cambio:+.2f}%)\n Saldo: ${mxn:.0f} MXN | {coin:.6f}\n TOTAL {mon.upper()}: ${valor:.0f} MXN"
        if coin>0 and c[mon]["buy"]>0:
            gan = (precio_mxn - c[mon]["buy"])/c[mon]["buy"]*100 - 1.56
            linea += f" Gan: {gan:+.1f}%"
        txt += linea + "\n\n"
    txt += f"💰 *TOTAL: ${total_global:.0f} / $3000 MXN*"
    bot.send_message(msg.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda x: True)
def cbq(call):
    c = load_cartera(); pr = get_precios()
    acc, mon = call.data.split("_")
    precio_mxn = pr[mon][0]
    if acc=="comprar":
        if c[mon]["mxn"] < 5: bot.answer_callback_query(call.id, f"Sin MXN en {mon.upper()}"); return
        cant = (c[mon]["mxn"] * (1-COMISION)) / precio_mxn
        c[mon]["mxn"]=0; c[mon]["coin"]=cant; c[mon]["buy"]=precio_mxn; save_cartera(c)
        bot.send_message(call.message.chat.id, f"✅ COMPRA {mon.upper()}: {cant:.6f} a ${precio_mxn:,.0f} MXN")
    else:
        if c[mon]["coin"]==0: bot.answer_callback_query(call.id, f"No tienes {mon.upper()}"); return
        mxn_obt = c[mon]["coin"] * precio_mxn * (1-COMISION)
        c[mon]["mxn"]=mxn_obt; c[mon]["coin"]=0; save_cartera(c)
        bot.send_message(call.message.chat.id, f"✅ VENTA {mon.upper()}: ${mxn_obt:.0f} MXN", reply_markup=get_keyboard())
    bot.answer_callback_query(call.id, "Hecho")

def alertas():
    while True:
        time.sleep(300)
        try:
            pr=get_precios()
            if not pr or not CHAT_ID or pr['fuente']=='EMERGENCIA': continue
            c=load_cartera()
            for mon in ["btc","eth","xrp"]:
                precio_mxn, cambio, _ = pr[mon]
                if cambio <= -2 and c[mon]["mxn"]>10:
                    bot.send_message(CHAT_ID, f"🟢 *COMPRA {mon.upper()}!* Cayó {cambio:.2f}% - ${precio_mxn:,.0f} MXN", reply_markup=get_keyboard(), parse_mode="Markdown")
                if c[mon]["coin"]>0 and c[mon]["buy"]>0:
                    gan=(precio_mxn - c[mon]["buy"])/c[mon]["buy"]*100 - 1.56
                    if gan>=2:
                        bot.send_message(CHAT_ID, f"🔴 *VENDE {mon.upper()}!* +{gan:.1f}% NETA", reply_markup=get_keyboard(), parse_mode="Markdown")
        except Exception as e: print(e)

threading.Thread(target=alertas, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return "Vicente V8 NUNCA FALLA Live"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
