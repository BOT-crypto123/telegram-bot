import os
import requests
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
PRECIO_COMPRA = float(os.getenv("PRECIO_COMPRA", 64364))
MODO_SIMULACION = True  # Ponlo en False cuando quieras operar real

bot = telebot.TeleBot(TOKEN)

def get_btc():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
    return requests.get(url, timeout=10).json()

def crear_botones_bitso():
    # --- AQUÍ SE ARREGLA LO DE BINANCE ---
    markup = types.InlineKeyboardMarkup()
    btn_comprar = types.InlineKeyboardButton("🟢 COMPRAR en Bitso", url="https://bitso.com/trade/btc_mxn")
    btn_vender = types.InlineKeyboardButton("🔴 VENDER en Bitso", url="https://bitso.com/trade/btc_mxn")
    markup.add(btn_comprar, btn_vender)
    return markup

def job():
    data = get_btc()
    btc_price = data['bitcoin']['usd']
    btc_change = data['bitcoin']['usd_24h_change']

    # --- CÁLCULO PARA VER TU TOTAL PERDIDO/GANADO SIEMPRE ---
    com_c = PRECIO_COMPRA * COMISION
    com_v = btc_price * COMISION
    total_comisiones = com_c + com_v
    ganancia_bruta = btc_price - PRECIO_COMPRA
    ganancia_real = ganancia_bruta - total_comisiones
    porc_real = (ganancia_real / PRECIO_COMPRA) * 100
    
    estado = "🟢 GANANCIA" if ganancia_real >= 0 else "🔴 PÉRDIDA"
    resumen_ganancia = f"\n\n---\n{estado} NETA REAL: ${ganancia_real:+,.2f} ({porc_real:+.2f}%)\nBruta: ${ganancia_bruta:+,.2f} - Comisiones: ${total_comisiones:.2f}"
    
    prefijo = "[SIMULACIÓN] " if MODO_SIMULACION else ""

    if btc_change <= -2:
        texto = f"{prefijo}🟢 ALERTA DE COMPRA - OPORTUNIDAD!\n\n📉 BTC bajo {btc_change:.2f}%\n💰 Precio: ${btc_price:,.2f}\n💵 Tu compra: ${PRECIO_COMPRA:,.2f}{resumen_ganancia}"
        bot.send_message(CHAT_ID, texto, reply_markup=crear_botones_bitso())
        return

    if abs(btc_change) < 2:
        # Ahora sí te dice cuánto vas perdiendo/ganando aunque esté estable
        print(f"Estable {btc_change:.2f}% | Neta: ${ganancia_real:.2f} ({porc_real:.2f}%) - no se envia alerta")
        return

    # ALERTA VENTA
    if porc_real < 1: # Solo vende si ganas minimo 1% neto
        print(f"Ganancia real {porc_real:.2f}% - muy baja, esperando")
        return

    texto = f"{prefijo}🔴 ALERTA DE VENTA - CONVIENE VENDER!\n\n📈 BTC subio {btc_change:+.2f}%\n💰 Precio: ${btc_price:,.2f}{resumen_ganancia}"
    bot.send_message(CHAT_ID, texto, reply_markup=crear_botones_bitso())

if __name__ == "__main__":
    job()
