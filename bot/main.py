import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO BTC VICENTE ALERT PRO...", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
PRECIO_COMPRA_REAL = 64364

bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        with open(CARTERA_FILE, "r") as f:
            return json.load(f)
    return {"usd": 1000.0, "btc": 0.0, "precio_prom": 0.0}

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def get_btc():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=10).json()
        return r['bitcoin']['usd'], r['bitcoin']['usd_24h_change']
    except:
        return None, None

def get_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🟢 COMPRAR", callback_data="comprar"),
        types.InlineKeyboardButton("🔴 VENDER", callback_data="vender")
    )
    markup.row(
        types.InlineKeyboardButton("📊 Ver Gráfica", url="https://www.tradingview.com/symbols/BTCUSDT/")
    )
    return markup

@bot.message_handler(commands=['start', 'balance'])
def start(m):
    precio, cambio = get_btc()
    cartera = load_cartera()
    total = cartera["usd"] + (cartera["btc"] * (precio or 0))
    com_c = cartera["btc"] * cartera["precio_prom"] * COMISION if cartera["btc"]>0 else 0
    com_v = cartera["btc"] * precio * COMISION if precio and cartera["btc"]>0 else 0
    ganancia_neta = (total - 1000) - com_c - com_v

    txt = (
        f"⚡ *BTC VICENTE ALERT - PRO*\n\n"
        f"BTC: ${precio:,.2f} ({cambio:+.2f}%)\n"
        f"USD Virtual: ${cartera['usd']:.2f}\n"
        f"BTC Virtual: {cartera['btc']:.6f}\n"
        f"Total: ${total:.2f}\n\n"
        f"Comisión compra: ${com_c:.2f} (0.78%)\n"
        f"Comisión venta: ${com_v:.2f} (0.78%)\n"
        f"*Ganancia NETA: ${ganancia_neta:+.2f}*"
    )
    bot.send_message(m.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cartera = load_cartera()
    precio, _ = get_btc()
    if call.data == "comprar":
        if cartera["usd"] < 10:
            bot.answer_callback_query(call.id, "Sin USD virtual")
            return
        usd = cartera["usd"] * 0.5
        btc_comp = (usd * (1-COMISION)) / precio
        cartera["btc"] += btc_comp
        cartera["usd"] -= usd
        cartera["precio_prom"] = precio
        save_cartera(cartera)
        bot.send_message(call.message.chat.id, f"✅ COMPRA: {btc_comp:.6f} BTC a ${precio:,.2f}\nQuedan ${cartera['usd']:.2f}")
    elif call.data == "vender":
        if cartera["btc"] == 0:
            bot.answer_callback_query(call.id, "No tienes BTC")
            return
        usd_obt = cartera["btc"] * precio * (1-COMISION)
        ganancia = usd_obt - (cartera["btc"] * cartera["precio_prom"])
        cartera["usd"] += usd_obt
        cartera["btc"] = 0
        save_cartera(cartera)
        bot.send_message(call.message.chat.id, f"✅ VENTA: ${usd_obt:.2f}\nGanancia NETA: ${ganancia:+.2f}", reply_markup=get_keyboard())

def alerta_automatica():
    while True:
        time.sleep(3600)
        try:
            precio, cambio = get_btc()
            if not precio or not CHAT_ID:
                continue
            if cambio <= -2:
                bot.send_message(CHAT_ID, 
                    f"🟢 *ALERTA COMPRA - OPORTUNIDAD!*\n\n📉 Bajó {cambio:.2f}%\n💰 ${precio:,.2f}\nEs buen momento para comprar barato.",
                    reply_markup=get_keyboard(), parse_mode="Markdown")
            com_c = PRECIO_COMPRA_REAL * COMISION
            com_v = precio * COMISION
            ganancia_real = (precio - PRECIO_COMPRA_REAL) - (com_c + com_v)
            porc_real = (ganancia_real / PRECIO_COMPRA_REAL) * 100
            if porc_real >= 2:
                bot.send_message(CHAT_ID,
                    f"🔴 *ALERTA VENTA - VENDE GANANDO!*\n\n📈 BTC: ${precio:,.2f} ({cambio:+.2f}%)\nComisión compra: ${com_c:.2f}\nComisión venta: ${com_v:.2f}\n✅ *Ganancia NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)*",
                    reply_markup=get_keyboard(), parse_mode="Markdown")
        except Exception as e:
            print(f"Error alerta: {e}")

threading.Thread(target=alerta_automatica, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

app = Flask(__name__)
@app.route('/')
def home():
    return "BTC Vicente Alert PRO - Live"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
