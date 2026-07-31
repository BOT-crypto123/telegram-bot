import os
import requests
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
COMISION = 0.0078

bot = telebot.TeleBot(TOKEN)

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true"
    try:
        data = requests.get(url, timeout=10).json()
        return data
    except:
        return {'bitcoin': {'usd': 64364, 'usd_24h_change': 0.74}, 'ethereum': {'usd': 1906.84, 'usd_24h_change': 0.40}, 'ripple': {'usd': 1.08, 'usd_24h_change': 0.86}}

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Bot activo Vicente! 🚀\n/precio - precio ahora\n/prueba - prueba ganancia real 0.78%\n/reporte - reporte manual")

@bot.message_handler(commands=['precio'])
def precio(m):
    data = get_prices()
    btc = data['bitcoin']['usd']
    btc_c = data['bitcoin']['usd_24h_change']
    bot.send_message(m.chat.id, f"💰 BTC ahora: ${btc:,.2f} ({btc_c:+.2f}%)")

@bot.message_handler(commands=['prueba'])
def prueba(m):
    compra = 64364
    venta = compra * 1.035
    com_c = compra * COMISION
    com_v = venta * COMISION
    ganancia_real = (venta - compra) - (com_c + com_v)
    porc_real = (ganancia_real / compra) * 100
    bot.send_message(m.chat.id, f"🤖 PRUEBA GANANCIA REAL\n\nCompra: ${compra}\nVenta: ${venta:.2f} (+3.5% bruto)\n\nComisión compra: ${com_c:.2f}\nComisión venta: ${com_v:.2f}\nTotal: ${com_c+com_v:.2f}\n\n✅ GANANCIA NETA: ${ganancia_real:.2f} ({porc_real:.2f}%)")

@bot.message_handler(commands=['reporte'])
def reporte_cmd(m):
    data = get_prices()
    txt = f"⏰ REPORTE\n- BTC: ${data['bitcoin']['usd']:,.2f} ({data['bitcoin']['usd_24h_change']:+.2f}%)\n- ETH: ${data['ethereum']['usd']:,.2f}\n- XRP: ${data['ripple']['usd']:.2f}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Ver gráfica", url="https://www.coingecko.com/en/coins/bitcoin"))
    bot.send_message(m.chat.id, txt, reply_markup=markup)

print("Bot iniciado con BOT_TOKEN...")
bot.infinity_polling()
