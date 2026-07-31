import os, json, time, threading, requests
from flask import Flask
from datetime import datetime, timezone, timedelta
import telebot
from telebot import types

print("INICIANDO BTC VICENTE ALERT PRO + REPORTE 10PM...", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
PRECIO_COMPRA_REAL = 64364

bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"
ultima_alerta_compra = 0
ultima_alerta_venta = 0
ultimo_reporte_fecha = ""

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
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
    if not precio:
        bot.reply_to(m, "Error precio")
        return
    cartera = load_cartera()
    total = cartera["usd"] + (cartera["btc"] * precio)
    ganancia_bruta = total - 1000
    com_c = cartera["btc"] * cartera["precio_prom"] * COMISION if cartera["btc"]>0 else 0
    com_v = cartera["btc"] * precio * COMISION if cartera["btc"]>0 else 0
    ganancia_neta = ganancia_bruta - com_c - com_v if cartera["btc"]>0 else ganancia_bruta
    porc_neta = (ganancia_neta / 1000 * 100) if total!=1000 else 0
    txt = f"⚡ *BTC VICENTE - SIMULADOR $1000*\n\n💰 BTC: ${precio:,.2f} ({cambio:+.2f}%)\n💵 USD: ${cartera['usd']:.2f}\n₿ BTC: {cartera['btc']:.6f}\n📊 Total: ${total:.2f}\nComisión compra: ${com_c:.2f}\nComisión venta: ${com_v:.2f}\n*NETA: ${ganancia_neta:+.2f} ({porc_neta:+.2f}%)*"
    bot.send_message(m.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cartera = load_cartera()
    precio, _ = get_btc()
    if not precio: return
    if call.data == "comprar":
        if cartera["usd"] < 10:
            bot.answer_callback_query(call.id, "Sin USD"); return
        usd = cartera["usd"] * 0.5
        com = usd * COMISION
        btc_comp = (usd - com) / precio
        cartera["btc"] += btc_comp
        cartera["usd"] -= usd
        cartera["precio_prom"] = precio
        save_cartera(cartera)
        bot.send_message(call.message.chat.id, f"✅ COMPRA: {btc_comp:.6f} BTC - Comisión ${com:.2f}", reply_markup=get_keyboard())
    elif call.data == "vender":
        if cartera["btc"] <= 0:
            bot.answer_callback_query(call.id, "Sin BTC"); return
        com_v = cartera["btc"] * precio * COMISION
        usd_obt = cartera["btc"] * precio - com_v
        cartera["usd"] += usd_obt
        cartera["btc"] = 0
        save_cartera(cartera)
        bot.send_message(call.message.chat.id, f"✅ VENTA: ${usd_obt:.2f} - Comisión ${com_v:.2f}", reply_markup=get_keyboard())

def alerta_oportunidad():
    global ultima_alerta_compra, ultima_alerta_venta
    while True:
        time.sleep(180)
        try:
            precio, cambio = get_btc()
            if not precio or not CHAT_ID: continue
            ahora = time.time()
            if cambio <= -2.0 and (ahora - ultima_alerta_compra) > 7200:
                bot.send_message(int(CHAT_ID), f"🟢 *OPORTUNIDAD COMPRA!*\n📉 BTC {cambio:.2f}% - ${precio:,.2f}", reply_markup=get_keyboard(), parse_mode="Markdown")
                ultima_alerta_compra = ahora
            com_c = PRECIO_COMPRA_REAL * COMISION
            com_v = precio * COMISION
            ganancia_real = (precio - PRECIO_COMPRA_REAL) - (com_c + com_v)
            porc_real = (ganancia_real / PRECIO_COMPRA_REAL * 100)
            if porc_real >= 2.0 and (ahora - ultima_alerta_venta) > 7200:
                bot.send_message(int(CHAT_ID), f"🔴 *OPORTUNIDAD VENTA GANANDO!*\n💰 ${precio:,.2f}\n✅ NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)", reply_markup=get_keyboard(), parse_mode="Markdown")
                ultima_alerta_venta = ahora
        except: pass

def reporte_diario():
    global ultimo_reporte_fecha
    while True:
        try:
            # Hora Nogales = UTC-6
            ahora_mx = datetime.now(timezone(timedelta(hours=-6)))
            if ahora_mx.hour == 22 and ahora_mx.minute == 0:
                fecha_hoy = ahora_mx.strftime("%Y-%m-%d")
                if fecha_hoy != ultimo_reporte_fecha:
                    precio, cambio = get_btc()
                    cartera = load_cartera()
                    total = cartera["usd"] + (cartera["btc"] * (precio or 0))
                    ganancia_bruta = total - 1000
                    com_c = cartera["btc"] * cartera["precio_prom"] * COMISION if cartera["btc"]>0 else 0
                    com_v = cartera["btc"] * precio * COMISION if precio and cartera["btc"]>0 else 0
                    ganancia_neta = ganancia_bruta - com_c - com_v if cartera["btc"]>0 else ganancia_bruta
                    porc_neta = (ganancia_neta / 1000 * 100)
                    com_real_c = PRECIO_COMPRA_REAL * COMISION
                    com_real_v = precio * COMISION if precio else 0
                    ganancia_real = (precio - PRECIO_COMPRA_REAL) - com_real_c - com_real_v if precio else 0
                    porc_real = (ganancia_real / PRECIO_COMPRA_REAL * 100) if precio else 0
                    reporte = f"📅 *REPORTE 10PM {ahora_mx.strftime('%d/%m')}*\n\n💰 BTC: ${precio:,.2f} ({cambio:+.2f}%)\n\n*SIMULADOR $1000:*\nTotal: ${total:.2f}\nNETA: ${ganancia_neta:+.2f} ({porc_neta:+.2f}%)\n\n*REAL:*\nCompra: ${PRECIO_COMPRA_REAL:,.2f}\nActual: ${precio:,.2f}\nNETA: ${ganancia_real:+.2f} ({porc_real:+.2f}%)"
                    bot.send_message(int(CHAT_ID), reporte, parse_mode="Markdown")
                    ultimo_reporte_fecha = fecha_hoy
            time.sleep(60)
        except:
            time.sleep(60)

threading.Thread(target=alerta_oportunidad, daemon=True).start()
threading.Thread(target=reporte_diario, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

app = Flask(__name__)
@app.route('/')
def home():
    return "BTC Vicente - Live - Oportunidades + Reporte 10PM"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
