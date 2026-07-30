import os, threading, requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACION PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return "BOT DEMO REAL - BTC ETH XRP VIVO"

# --- CONFIGURACION DE TU DEMO REAL ---
TOKEN = os.environ.get("BOT_TOKEN")
INVERSION_INICIAL = 1000
MONEDAS = ["BTC", "ETH", "XRP"]
DINERO_POR_MONEDA = INVERSION_INICIAL / len(MONEDAS) # 333.33

portfolio = {} # Aqui se guardara cuantas monedas compraste
precios_entrada = {} # A cuanto compraste

def get_precio_real(simbolo):
    try:
        # Precio real de Binance
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={simbolo}USDT"
        r = requests.get(url, timeout=5).json()
        return float(r['price'])
    except:
        # Respaldo por si Binance falla
        return 0

def inicializar_portafolio():
    global portfolio, precios_entrada
    if portfolio: return
    print("INICIALIZANDO PORTAFOLIO DEMO REAL...")
    for moneda in MONEDAS:
        precio_actual = get_precio_real(moneda)
        cantidad = DINERO_POR_MONEDA / precio_actual
        portfolio[moneda] = cantidad
        precios_entrada[moneda] = precio_actual
        print(f"COMPRADO {cantidad} {moneda} a ${precio_actual}")
    print("PORTAFOLIO LISTO")

# --- COMANDOS DE TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inicializar_portafolio()
    await update.message.reply_text("✅ Bot Demo Real Activo\nBTC + ETH + XRP\nEscribe 'precio' para ver tu ganancia REAL")

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inicializar_portafolio()
    texto = "📊 *PORTAFOLIO DEMO $1000 - GANANCIA REAL*\n\n"
    total_actual = 0
    total_entrada = 0
    
    for moneda in MONEDAS:
        precio_ahora = get_precio_real(moneda)
        cantidad = portfolio[moneda]
        valor_ahora = cantidad * precio_ahora
        valor_entrada = cantidad * precios_entrada[moneda]
        
        total_actual += valor_ahora
        total_entrada += valor_entrada
        
        ganancia = valor_ahora - valor_entrada
        emoji = "🟢" if ganancia >=0 else "🔴"
        
        texto += f"{emoji} *{moneda}:* ${precio_ahora:,.2f}\n"
        texto += f"   Tienes: {cantidad:.4f} | Valor: ${valor_ahora:.2f} ({ganancia:+.2f})\n\n"

    ganancia_total = total_actual - INVERSION_INICIAL
    porcentaje = (ganancia_total / INVERSION_INICIAL) * 100
    
    texto += f"💰 *Total Actual: ${total_actual:.2f}*\n"
    texto += f"📈 *Ganancia REAL: ${ganancia_total:+.2f} ({porcentaje:+.2f}%)*\n"
    texto += f"_Precios reales de Binance_"
    
    await update.message.reply_text(texto, parse_mode='Markdown')

def run_bot():
    inicializar_portafolio()
    app_telegram = Application.builder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, precio))
    print("BOT 3 CRYPTOS INICIADO - Web server OK")
    app_telegram.run_polling()

# --- INICIO ---
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
