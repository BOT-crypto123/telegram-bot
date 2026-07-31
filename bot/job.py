import os
import requests
import telebot

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
PRECIO_COMPRA = float(os.getenv("PRECIO_COMPRA", 64364))

bot = telebot.TeleBot(TOKEN)

def get_btc():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
    return requests.get(url, timeout=10).json()

def job():
    data = get_btc()
    btc_price = data['bitcoin']['usd']
    btc_change = data['bitcoin']['usd_24h_change']

    if abs(btc_change) < 2:
        print(f"Estable {btc_change:.2f}% - no se envia")
        return

    com_c = PRECIO_COMPRA * COMISION
    com_v = btc_price * COMISION
    ganancia_real = (btc_price - PRECIO_COMPRA) - (com_c + com_v)
    porc_real = (ganancia_real / PRECIO_COMPRA) * 100

    if porc_real < 2:
        print(f"Ganancia real {porc_real:.2f}% - esperando")
        return

    texto = f"🔴 ALERTA VENTA BTC\nSubio {btc_change:+.2f}%\nPrecio: ${btc_price:,.2f}\nGanancia REAL: ${ganancia_real:.2f} ({porc_real:.2f}%)"
    bot.send_message(CHAT_ID, texto)

if __name__ == "__main__":
    job()
