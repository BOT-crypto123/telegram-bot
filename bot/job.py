import os
import requests
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078  # 0.78% Bitso Taker
PRECIO_COMPRA_GUARDADO = float(os.getenv("PRECIO_COMPRA", 64364))

bot = telebot.TeleBot(TOKEN)

def get_btc():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
    r = requests.get(url, timeout=10).json()
    return r

def job():
    data = get_btc()
    btc_price = data['bitcoin']['usd']
    btc_change = data['bitcoin']['usd_24h_change']

    # 1. FILTRO DE VOLATILIDAD: Si no llega a +-2%, no hacer nada
    if abs(btc_change) < 2:
        print(f"[JOB] Mercado estable {btc_change:.2f}% - No se envía nada")
        return

    # 2. FILTRO DE GANANCIA REAL CON COMISION
    com_compra = PRECIO_COMPRA_GUARDADO * COMISION
    com_venta = btc_price * COMISION
    ganancia_real = (btc_price - PRECIO_COMPRA_GUARDADO) - (com_compra + com_venta)
    porc_real = (ganancia_real / PRECIO_COMPRA_GUARDADO) * 100

    # Si subió 2% pero la ganancia real es menor a 2%, tampoco avisamos
    if porc_real < 2:
        print(f"[JOB] Subió {btc_change:.2f}% pero ganancia real {porc_real:.2f}% - Esperando")
        return

    # 3. SOLO AQUÍ SI CONVIENE, MANDA LA ALERTA
    texto = f"""🔴 ALERTA DE VENTA BTC - ¡CONVIENE!

📈 Volatilidad: {btc_change:+.2f}%
💰 Precio actual: ${btc_price:,.2f}
Precio compra: ${PRECIO_COMPRA_GUARDADO:,.2f}

💸 Comisión compra: ${com_compra:.2f}
💸 Comisión venta: ${com_venta:.2f}

✅ GANANCIA REAL NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔴 VENDER AHORA", callback_data="vender"))
    markup.add(types.InlineKeyboardButton("📊 Ver gráfica", url="https://www.coingecko.com/en/coins/bitcoin"))

    bot.send_message(CHAT_ID, texto, reply_markup=markup)
    print(f"[JOB] Alerta enviada! Ganancia real {porc_real:.2f}%")

if __name__ == "__main__":
    job()
