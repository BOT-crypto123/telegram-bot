import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO VICENTE PRO 3 MONEDAS FIX...", flush=True)

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
    return {"usd": 1000.0, "btc": 0.0, "eth": 0.0, "xrp": 0.0, "precio_btc": 0.0, "precio_eth": 0.0, "precio_xrp": 0.0}

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def get_precios():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # Intentamos con CoinGecko con headers
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true",
            headers=headers, timeout=15).json()
        return {
            "btc": (r['bitcoin']['usd'], r['bitcoin']['usd_24h_change']),
            "eth": (r['ethereum']['usd'], r['ethereum']['usd_24h_change']),
            "xrp": (r['ripple']['usd'], r['ripple']['usd_24h_change'])
        }
    except Exception as e:
        print(f"Error coingecko: {e}, probando binance", flush=True)
    try:
        # Respaldo Binance
        def get_binance(sym):
            d = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}", headers=headers, timeout=10).json()
            return float(d['lastPrice']), float(d['priceChangePercent'])
        return {
            "btc": get_binance("BTCUSDT"),
            "eth": get_binance("ETHUSDT"),
            "xrp": get_binance("XRPUSDT")
        }
    except Exception as e:
        print(f"Error binance tambien: {e}", flush=True)
        return None

def get_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🟢 BTC", callback_data="comprar_btc"),
        types.InlineKeyboardButton("🟢 ETH", callback_data="comprar_eth"),
        types.InlineKeyboardButton("🟢 XRP", callback_data="comprar_xrp")
    )
    markup.row(
        types.InlineKeyboardButton("🔴 BTC", callback_data="vender_btc"),
        types.InlineKeyboardButton("🔴 ETH", callback_data="vender_eth"),
        types.InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp")
    )
    return markup

@bot.message_handler(commands=['start', 'balance'])
def start(m):
    precios = get_precios()
    if not precios:
        bot.send_message(m.chat.id, "⚠️ API de precios saturada, intenta en 15 seg")
        return
    c = load_cartera()
    total = c["usd"] + c["btc"]*precios['btc'][0] + c["eth"]*precios['eth'][0] + c["xrp"]*precios['xrp'][0]
    txt = (f"⚡ *VICENTE CRYPTO PRO - 3 MONEDAS (5min)*\n\n"
           f"BTC: ${precios['btc'][0]:,.2f} ({precios['btc'][1]:+.2f}%)\n"
           f"ETH: ${precios['eth'][0]:,.2f} ({precios['eth'][1]:+.2f}%)\n"
           f"XRP: ${precios['xrp'][0]:,.4f} ({precios['xrp'][1]:+.2f}%)\n\n"
           f"USD: ${c['usd']:.2f} | TOTAL: ${total:.2f}")
    bot.send_message(m.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    c = load_cartera()
    precios = get_precios()
    if not precios: return
    accion, moneda = call.data.split("_")
    precio = precios[moneda][0]
    if accion == "comprar":
        if c["usd"] < 5:
            bot.answer_callback_query(call.id, "Sin USD"); return
        usd = c["usd"] * 0.33
        cant = (usd * (1-COMISION)) / precio
        c["usd"] -= usd; c[moneda] += cant; c[f"precio_{moneda}"] = precio
        save_cartera(c)
        bot.send_message(call.message.chat.id, f"✅ COMPRA {moneda.upper()}: {cant:.6f} a ${precio:,.2f}")
    else:
        if c[moneda] == 0:
            bot.answer_callback_query(call.id, f"No tienes {moneda.upper()}"); return
        usd_obt = c[moneda] * precio * (1-COMISION)
        c["usd"] += usd_obt; c[moneda] = 0
        save_cartera(c)
        bot.send_message(call.message.chat.id, f"✅ VENTA {moneda.upper()}: ${usd_obt:.2f}", reply_markup=get_keyboard())
    bot.answer_callback_query(call.id, "Hecho")

def alerta_automatica():
    while True:
        time.sleep(300)
        try:
            precios = get_precios()
            if not precios or not CHAT_ID: continue
            c = load_cartera()
            for mon in ["btc","eth","xrp"]:
                precio, cambio = precios[mon]
                if cambio <= -2:
                    bot.send_message(CHAT_ID, f"🟢 *COMPRA {mon.upper()}!* Cayó {cambio:.2f}% - ${precio:,.4f}", reply_markup=get_keyboard(), parse_mode="Markdown")
                if c[mon] > 0 and c[f"precio_{mon}"] > 0:
                    gan = (precio - c[f"precio_{mon}"]) / c[f"precio_{mon}"] * 100 - 1.56
                    if gan >= 2:
                        bot.send_message(CHAT_ID, f"🔴 *VENDE {mon.upper()}!* Neta +{gan:.2f}% - ${precio:,.4f}", reply_markup=get_keyboard(), parse_mode="Markdown")
        except Exception as e:
            print(e)

threading.Thread(target=alerta_automatica, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
app = Flask(__name__)
@app.route('/')
def home(): return "Vicente PRO 3 FIX - Live"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
