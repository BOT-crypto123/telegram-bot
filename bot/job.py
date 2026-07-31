import os, json, requests
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
ARCHIVO_TRADES = "trades.json"

PRECIO_BTC = float(os.getenv("PRECIO_BTC") or os.getenv("PRECIO_COMPRA") or 64364)
PRECIO_ETH = float(os.getenv("PRECIO_ETH") or 3500)
PRECIO_XRP = float(os.getenv("PRECIO_XRP") or 2.5)

bot = telebot.TeleBot(TOKEN)

MONEDAS = {
    "bitcoin": {"simbolo": "BTC", "precio_compra": PRECIO_BTC},
    "ethereum": {"simbolo": "ETH", "precio_compra": PRECIO_ETH},
    "ripple": {"simbolo": "XRP", "precio_compra": PRECIO_XRP},
}

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
    return requests.get(url, timeout=10).json()

def cargar_trades():
    if not os.path.exists(ARCHIVO_TRADES):
        return {}
    try:
        with open(ARCHIVO_TRADES, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_trades(trades):
    with open(ARCHIVO_TRADES, "w") as f:
        json.dump(trades, f)

def job():
    data = get_prices()
    trades = cargar_trades()

    for coin_id, info in MONEDAS.items():
        price = data[coin_id]['usd']
        change = data[coin_id]['usd_24h_change']
        simbolo = info["simbolo"]
        precio_compra_real = trades.get(simbolo, {}).get("precio", info["precio_compra"])

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"🟢 COMPRAR {simbolo} (Sim)", callback_data=f"buy_{simbolo}"),
            types.InlineKeyboardButton(f"🔴 VENDER {simbolo} (Sim)", callback_data=f"sell_{simbolo}"),
            types.InlineKeyboardButton(f"📊 Balance", callback_data=f"balance_{simbolo}")
        )

        com_c = precio_compra_real * COMISION
        com_v = price * COMISION
        ganancia_real = (price - precio_compra_real) - (com_c + com_v)
        porc_real = (ganancia_real / precio_compra_real) * 100 if precio_compra_real > 0 else 0

        if change <= -2:
            texto = f"🟢 ALERTA COMPRA {simbolo}!\n📉 Bajo {change:.2f}%\n💰 Precio: ${price:,.2f}\n💵 Tu compra sim: ${precio_compra_real:,.2f}\n\nPÉRDIDA/GANANCIA: ${ganancia_real:+,.2f} ({porc_real:+.2f}%)"
            bot.send_message(CHAT_ID, texto, reply_markup=markup)
            continue

        if porc_real >= 2:
            texto = f"🔴 ALERTA VENTA {simbolo}!\n📈 Subio {change:+.2f}%\n💰 Precio: ${price:,.2f}\n✅ GANANCIA NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)"
            bot.send_message(CHAT_ID, texto, reply_markup=markup)
        else:
            print(f"{simbolo} estable {change:.2f}% / ganancia {porc_real:.2f}%")

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    trades = cargar_trades()
    data = get_prices()
    try:
        if call.data.startswith("buy_"):
            simbolo = call.data.split("_")[1]
            coin_id = [k for k,v in MONEDAS.items() if v["simbolo"]==simbolo][0]
            precio_actual = data[coin_id]['usd']
            trades[simbolo] = {"precio": precio_actual}
            guardar_trades(trades)
            bot.answer_callback_query(call.id, f"Compra simulada {simbolo}")
            bot.send_message(CHAT_ID, f"✅ SIMULASTE COMPRA {simbolo} a ${precio_actual:,.2f}\nAhora veras tu ganancia/perdida real.")

        elif call.data.startswith("sell_"):
            simbolo = call.data.split("_")[1]
            coin_id = [k for k,v in MONEDAS.items() if v["simbolo"]==simbolo][0]
            precio_actual = data[coin_id]['usd']
            precio_compra = trades.get(simbolo, {}).get("precio", MONEDAS[coin_id]["precio_compra"])
            ganancia = (precio_actual - precio_compra) - (precio_compra*COMISION + precio_actual*COMISION)
            porc = (ganancia/precio_compra)*100
            bot.answer_callback_query(call.id, "Venta simulada")
            bot.send_message(CHAT_ID, f"💰 VENTA SIMULADA {simbolo}\nCompra: ${precio_compra:,.2f}\nVenta: ${precio_actual:,.2f}\nTOTAL NETO: ${ganancia:+,.2f} ({porc:+.2f}%)")

        elif call.data.startswith("balance_"):
            simbolo = call.data.split("_")[1]
            coin_id = [k for k,v in MONEDAS.items() if v["simbolo"]==simbolo][0]
            precio_actual = data[coin_id]['usd']
            precio_compra = trades.get(simbolo, {}).get("precio", MONEDAS[coin_id]["precio_compra"])
            ganancia = (precio_actual - precio_compra) - (precio_compra*COMISION + precio_actual*COMISION)
            porc = (ganancia/precio_compra)*100
            bot.send_message(CHAT_ID, f"📊 BALANCE {simbolo}\nActual: ${precio_actual:,.2f}\nCompra: ${precio_compra:,.2f}\nTotal: ${ganancia:+,.2f} ({porc:+.2f}%)")
    except Exception as e:
        print(f"Error callback: {e}")

if __name__ == "__main__":
    job()
