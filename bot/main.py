import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO BTC ETH XRP VICENTE PRO 5MIN...", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078

bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        with open(CARTERA_FILE, "r") as f:
            return json.load(f)
    return {
        "usd": 1000.0,
        "btc": 0.0, "eth": 0.0, "xrp": 0.0,
        "precio_btc": 0.0, "precio_eth": 0.0, "precio_xrp": 0.0
    }

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def get_precios():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true",
            timeout=10).json()
        return {
            "btc": (r['bitcoin']['usd'], r['bitcoin']['usd_24h_change']),
            "eth": (r['ethereum']['usd'], r['ethereum']['usd_24h_change']),
            "xrp": (r['ripple']['usd'], r['ripple']['usd_24h_change'])
        }
    except:
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
    markup.row(
        types.InlineKeyboardButton("📊 Ver Gráfica BTC", url="https://www.tradingview.com/symbols/BTCUSDT/"),
    )
    return markup

@bot.message_handler(commands=['start', 'balance'])
def start(m):
    precios = get_precios()
    if not precios:
        bot.send_message(m.chat.id, "Error obteniendo precios, intenta en 10 seg")
        return
    cartera = load_cartera()

    p_btc, c_btc = precios['btc']
    p_eth, c_eth = precios['eth']
    p_xrp, c_xrp = precios['xrp']

    total = cartera["usd"] + cartera["btc"]*p_btc + cartera["eth"]*p_eth + cartera["xrp"]*p_xrp

    txt = (
        f"⚡ *VICENTE CRYPTO PRO - 3 MONEDAS (5min)*\n\n"
        f"BTC: ${p_btc:,.2f} ({c_btc:+.2f}%)\n"
        f"ETH: ${p_eth:,.2f} ({c_eth:+.2f}%)\n"
        f"XRP: ${p_xrp:,.4f} ({c_xrp:+.2f}%)\n\n"
        f"USD Virtual: ${cartera['usd']:.2f}\n"
        f"BTC: {cartera['btc']:.6f}\n"
        f"ETH: {cartera['eth']:.6f}\n"
        f"XRP: {cartera['xrp']:.2f}\n"
        f"*TOTAL: ${total:.2f}*\n"
        f"Comisión: 0.78% por operación"
    )
    bot.send_message(m.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cartera = load_cartera()
    precios = get_precios()
    if not precios:
        bot.answer_callback_query(call.id, "Error precios")
        return

    moneda = call.data.split("_")[1] # btc, eth, xrp
    accion = call.data.split("_")[0] # comprar, vender
    precio = precios[moneda][0]

    if accion == "comprar":
        if cartera["usd"] < 10:
            bot.answer_callback_query(call.id, "Sin USD virtual")
            return
        usd = cartera["usd"] * 0.33 # compra 33% del saldo para poder comprar las 3
        cant = (usd * (1-COMISION)) / precio
        cartera["usd"] -= usd
        cartera[moneda] += cant
        cartera[f"precio_{moneda}"] = precio
        save_cartera(cartera)
        bot.answer_callback_query(call.id, f"Compraste {cant:.6f} {moneda.upper()}")
        bot.send_message(call.message.chat.id, f"✅ COMPRA {moneda.upper()}: {cant:.6f} a ${precio:,.2f}")

    elif accion == "vender":
        if cartera[moneda] == 0:
            bot.answer_callback_query(call.id, f"No tienes {moneda.upper()}")
            return
        usd_obt = cartera[moneda] * precio * (1-COMISION)
        cartera["usd"] += usd_obt
        cartera[moneda] = 0
        save_cartera(cartera)
        bot.answer_callback_query(call.id, f"Vendiste {moneda.upper()} por ${usd_obt:.2f}")
        bot.send_message(call.message.chat.id, f"✅ VENTA {moneda.upper()}: ${usd_obt:.2f}", reply_markup=get_keyboard())

def alerta_automatica():
    while True:
        time.sleep(300) # 5 MINUTOS
        try:
            precios = get_precios()
            if not precios or not CHAT_ID:
                continue
            for moneda in ["btc", "eth", "xrp"]:
                precio, cambio = precios[moneda]
                if cambio is None: continue

                # ALERTA COMPRA SI BAJA -2% O MAS
                if cambio <= -2:
                    bot.send_message(CHAT_ID,
                        f"🟢 *ALERTA COMPRA {moneda.upper()}!*\n\n📉 Se desplomó {cambio:.2f}%\n💰 Precio: ${precio:,.4f}\n¡Oportunidad de comprar barato!",
                        reply_markup=get_keyboard(), parse_mode="Markdown")

                # ALERTA VENTA SI TIENES LA MONEDA Y GANAS +2% NETO
                cartera = load_cartera()
                if cartera[moneda] > 0:
                    precio_compra = cartera[f"precio_{moneda}"]
                    if precio_compra > 0:
                        ganancia = (precio - precio_compra) / precio_compra * 100
                        com_total = COMISION*2*100 # aprox
                        ganancia_neta = ganancia - com_total
                        if ganancia_neta >= 2:
                            bot.send_message(CHAT_ID,
                                f"🔴 *ALERTA VENTA {moneda.upper()}!*\n\n📈 Precio: ${precio:,.4f} ({cambio:+.2f}%)\n✅ *Ganancia NETA: {ganancia_neta:.2f}%*\n¡Conviene vender!",
                                reply_markup=get_keyboard(), parse_mode="Markdown")
        except Exception as e:
            print(f"Error alerta: {e}")

threading.Thread(target=alerta_automatica, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

app = Flask(__name__)
@app.route('/')
def home():
    return "Vicente PRO - BTC ETH XRP - 5min"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
