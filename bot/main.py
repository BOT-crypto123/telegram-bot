import os
import requests
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078

# Si quieres poner tu precio de compra real, crea estos 3 Secrets en GitHub:
# PRECIO_BTC, PRECIO_ETH, PRECIO_XRP
PRECIO_BTC = float(os.getenv("PRECIO_COMPRA") or os.getenv("PRECIO_BTC") or 64364)
PRECIO_ETH = float(os.getenv("PRECIO_ETH") or 3500)
PRECIO_XRP = float(os.getenv("PRECIO_XRP") or 2.5)

bot = telebot.TeleBot(TOKEN)

MONEDAS = {
    "bitcoin": {"simbolo": "BTC", "precio_compra": PRECIO_BTC, "link": "https://bitso.com/trade/btc_mxn"},
    "ethereum": {"simbolo": "ETH", "precio_compra": PRECIO_ETH, "link": "https://bitso.com/trade/eth_mxn"},
    "ripple": {"simbolo": "XRP", "precio_compra": PRECIO_XRP, "link": "https://bitso.com/trade/xrp_mxn"},
}

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
    return requests.get(url, timeout=10).json()

def job():
    data = get_prices()

    for coin_id, info in MONEDAS.items():
        price = data[coin_id]['usd']
        change = data[coin_id]['usd_24h_change']
        simbolo = info["simbolo"]
        link = info["link"]
        precio_compra = info["precio_compra"]

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"🟢 COMPRAR {simbolo}", url=link),
            types.InlineKeyboardButton(f"🔴 VENDER {simbolo}", url=link)
        )

        # COMPRA si baja 2% o mas
        if change <= -2:
            texto = f"🟢 ALERTA COMPRA {simbolo}!\n\n📉 {simbolo} bajo {change:.2f}%\n💰 Precio: ${price:,.2f}\nOportunidad para comprar barato."
            bot.send_message(CHAT_ID, texto, reply_markup=markup)
            continue

        # VENTA si ganancia real > 2%
        com_c = precio_compra * COMISION
        com_v = price * COMISION
        ganancia_real = (price - precio_compra) - (com_c + com_v)
        porc_real = (ganancia_real / precio_compra) * 100 if precio_compra > 0 else 0

        if porc_real >= 2:
            texto = f"🔴 ALERTA VENTA {simbolo}!\n\n📈 {simbolo} subio {change:+.2f}%\n💰 Precio: ${price:,.2f}\n✅ GANANCIA REAL NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)"
            bot.send_message(CHAT_ID, texto, reply_markup=markup)
        else:
            print(f"{simbolo} estable {change:.2f}% / ganancia {porc_real:.2f}% - no se envia")

if __name__ == "__main__":
    job()
