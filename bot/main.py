import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO VICENTE V5 - 1000 MXN CADA UNO", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {
        "btc": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},
        "eth": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0},
        "xrp": {"mxn": 1000.0, "coin": 0.0, "buy": 0.0}
    }

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def get_dolar_mxn():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5).json()
        return r['rates']['MXN']
    except:
        return 18.5 # respaldo

def get_precios():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,XRP&tsyms=USD", headers=headers, timeout=10).json()
        dolar = get_dolar_mxn()
        return {
            "btc": (r['RAW']['BTC']['USD']['PRICE'] * dolar, r['RAW']['BTC']['USD']['CHANGEPCT24HOUR'], r['RAW']['BTC']['USD']['PRICE']),
            "eth": (r['RAW']['ETH']['USD']['PRICE'] * dolar, r['RAW']['ETH']['USD']['CHANGEPCT24HOUR'], r['RAW']['ETH']['USD']['PRICE']),
            "xrp": (r['RAW']['XRP']['USD']['PRICE'] * dolar, r['RAW']['XRP']['USD']['CHANGEPCT24HOUR'], r['RAW']['XRP']['USD']['PRICE']),
            "dolar": dolar
        }
    except Exception as e:
        print(f"Fallo precios: {e}", flush=True)
        return None

def get_keyboard():
    m = types.InlineKeyboardMarkup()
    m.row(types.InlineKeyboardButton("🟢 BTC", callback_data="comprar_btc"), types.InlineKeyboardButton("🟢 ETH", callback_data="comprar_eth"), types.InlineKeyboardButton("🟢 XRP", callback_data="comprar_xrp"))
    m.row(types.InlineKeyboardButton("🔴 BTC", callback_data="vender_btc"), types.InlineKeyboardButton("🔴 ETH", callback_data="vender_eth"), types.InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp"))
    return m

@bot.message_handler(commands=['start','balance'])
def start(msg):
    p = get_precios()
    if not p:
        bot.send_message(msg.chat.id, "⏳ API ocupada, intenta en 20 seg"); return
    c = load_cartera()
    txt = f"⚡ *VICENTE CRYPTO - 3x $1,000 MXN (5min)*\nDólar: ${p['dolar']:.2f} MXN\n\n"
    total_global = 0
    for mon in ["btc","eth","xrp"]:
        precio_mxn, cambio, precio_usd = p[mon]
        mxn = c[mon]["mxn"]
        coin = c[mon]["coin"]
        valor = coin * precio_mxn + mxn
        total_global += valor
        linea = f"*{mon.upper()}*: ${precio_mxn:,.2f} MXN (${precio_usd:,.2f} USD) ({cambio:+.2f}%)\n"
        linea += f" Saldo: ${mxn:.2f} MXN | {coin:.6f} {mon.upper()}\n Total {mon.upper()}: ${valor:.2f} MXN"
        if coin>0 and c[mon]["buy"]>0:
            gan = (precio_mxn - c[mon]["buy"])/c[mon]["buy"]*100 - 1.56
            linea += f"\n Gan NETA: {gan:+.2f}%"
        txt += linea + "\n\n"
    txt += f"💰 *TOTAL GLOBAL: ${total_global:.2f} MXN*\nInicio: $3,000 MXN"
    bot.send_message(msg.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda x: True)
def cbq(call):
    c = load_cartera(); pr = get_precios()
    if not pr: bot.answer_callback_query(call.id, "Error precios"); return
    acc, mon = call.data.split("_")
    precio_mxn = pr[mon][0]
    if acc=="comprar":
        if c[mon]["mxn"] < 10:
            bot.answer_callback_query(call.id, f"Sin MXN en {mon.upper()}"); return
        mxn = c[mon]["mxn"]
        cant = (mxn * (1-COMISION)) / precio_mxn
        c[mon]["mxn"] = 0; c[mon]["coin"] = cant; c[mon]["buy"] = precio_mxn
        save_cartera(c)
        bot.send_message(call.message.chat.id, f"✅ COMPRA {mon.upper()}: {cant:.6f} a ${precio_mxn:,.2f} MXN")
    else:
        if c[mon]["coin"] == 0:
            bot.answer_callback_query(call.id, f"No tienes {mon.upper()}"); return
        mxn_obt = c[mon]["coin"] * precio_mxn * (1-COMISION)
        c[mon]["mxn"] = mxn_obt; c[mon]["coin"] = 0
        save_cartera(c)
        bot.send_message(call.message.chat.id, f"✅ VENTA {mon.upper()}: ${mxn_obt:.2f} MXN", reply_markup=get_keyboard())
    bot.answer_callback_query(call.id, "Hecho")

def alertas():
    while True:
        time.sleep(300)
        try:
            pr = get_precios()
            if not pr or not CHAT_ID: continue
            c = load_cartera()
            for mon in ["btc","eth","xrp"]:
                precio_mxn, cambio, _ = pr[mon]
                if cambio <= -2:
                    bot.send_message(CHAT_ID, f"🟢 *COMPRA {mon.upper()}!* Cayó {cambio:.2f}% - ${precio_mxn:,.2f} MXN\nSaldo: ${c[mon]['mxn']:.2f} MXN", reply_markup=get_keyboard(), parse_mode="Markdown")
                if c[mon]["coin"]>0 and c[mon]["buy"]>0:
                    gan = (precio_mxn - c[mon]["buy"])/c[mon]["buy"]*100 - 1.56
                    if gan >= 2:
                        bot.send_message(CHAT_ID, f"🔴 *VENDE {mon.upper()}!* +{gan:.2f}% NETA - ${precio_mxn:,.2f} MXN", reply_markup=get_keyboard(), parse_mode="Markdown")
        except Exception as e: print(e)

threading.Thread(target=alertas, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
app = Flask(__name__)
@app.route('/')
def home(): return "Vicente V5 1000 MXN Live"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
