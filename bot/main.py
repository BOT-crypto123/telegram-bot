import os
import requests
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
PRECIO_COMPRA = float(os.getenv("PRECIO_COMPRA") or 64364)

bot = telebot.TeleBot(TOKEN)

def get_btc():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
    return requests.get(url, timeout=10).json()

def job():
    data = get_btc()
    btc_price = data['bitcoin']['usd']
    btc_change = data['bitcoin']['usd_24h_change']

    if abs(btc_change) < 2:
        print(f"Estable {btc_change:.2f}% - no se envia")
        return

    if btc_change <= -2:
        texto = f"🟢 ALERTA DE COMPRA - OPORTUNIDAD!\n\n📉 BTC bajo {btc_change:.2f}%\n💰 Precio: ${btc_price:,.2f}\nEs buen momento para comprar barato."
        bot.send_message(CHAT_ID, texto)
        return

    com_c = PRECIO_COMPRA * COMISION
    com_v = btc_price * COMISION
    ganancia_real = (btc_price - PRECIO_COMPRA) - (com_c + com_v)
    porc_real = (ganancia_real / PRECIO_COMPRA) * 100

    if porc_real < 2:
        print(f"Ganancia real {porc_real:.2f}% - esperando")
        return

    texto = f"🔴 ALERTA DE VENTA - CONVIENE VENDER!\n\n📈 BTC subio {btc_change:+.2f}%\n💰 Precio: ${btc_price:,.2f}\n✅ GANANCIA REAL NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)"
    bot.send_message(CHAT_ID, texto)

if __name__ == "__main__":
    job()
