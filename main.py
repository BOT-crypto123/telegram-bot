import os, threading, requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- SERVIDOR PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return "BOT DEMO REAL - BTC ETH XRP VIVO"

# --- CONFIGURACION ---
TOKEN = os.environ.get("BOT_TOKEN")
INVERSION_INICIAL = 1000
MONEDAS = ["BTC", "ETH", "XRP"]
DINERO_POR_MONEDA = INVERSION_INICIAL / len(MONEDAS)

portfolio = {}
precios_entrada = {}

def get_precio_real(simbolo):
    try:
        mapa = {"BTC": "bitcoin", "ETH": "ethereum", "XRP": "ripple"}
        id_cg = mapa[simbolo]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={id_cg}&vs_currencies=usd"
        r = requests.get(url, timeout=10).json()
        precio = float(r[id_cg]['usd'])
        print(f"Precio real {simbolo}: ${precio}")
        return precio
    except Exception as e:
        print(f"Error precio {simbolo}: {e}")
        respaldo = {"BTC": 68000.0, "ETH": 3500.0, "XRP": 0.60}
        return respaldo[simbolo]

def inicializar_portafolio():
    global portfolio, precios_entrada
    if portfolio:
        return
    print("INICIALIZANDO PORTAFOLIO DEMO REAL...")
    for moneda in MONEDAS:
        precio_actual = get_precio_real(moneda)
        if precio_actual == 0:
            precio_actual = 1
        cantidad = DINERO_POR_MONEDA / precio_actual
        portfolio[moneda] = cantidad
        precios_entrada[moneda] = precio_actual
        print(f"COMPRADO {cantidad} {moneda} a ${precio_actual}")
    print("PORTAFOLIO LISTO")

# --- TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inicializar_portafolio()
    await update.message.reply_text("✅ Bot Demo Real Activo\nBTC + ETH + XRP\nEscribe 'precio' para ver tu ganancia REAL")

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inicializar_portafolio()
    texto = "📊 *PORTAFOLIO DEMO $1000 - GANANCIA REAL*\n\n"
    total_actual = 0

    for moneda in MONEDAS:
        precio_ahora = get_precio_real(moneda)
        cantidad = portfolio[moneda]
        valor_ahora = cantidad * precio_ahora
        valor_entrada = cantidad * precios_entrada[moneda]
        total_actual += valor_ahora
        ganancia = valor_ahora - valor_entrada
        emoji = "🟢" if ganancia >= 0 else "🔴"
        texto += f"{emoji} *{moneda}:* ${precio_ahora:,.4f}\n"
        texto += f" Tienes: {cantidad:.4f} | Valor: ${valor_ahora:.2f} ({ganancia:+.2f})\n\n"

    ganancia_total = total_actual - INVERSION_INICIAL
    porcentaje = (ganancia_total / INVERSION_INICIAL) * 100
    texto += f"💰 *Total Actual: ${total_actual:.2f}*\n"
    texto += f"📈 *Ganancia REAL: ${ganancia_total:+.2f} ({porcentaje:+.2f}%)*\n"
    texto += f"_Precios reales de CoinGecko_"
    await update.message.reply_text(texto, parse_mode='Markdown')

def run_bot():
    inicializar_portafolio()
    app_tg = Application.builder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, precio))
    print("BOT 3 CRYPTOS INICIADO - Web server OK")
    app_tg.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
