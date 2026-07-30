import os, requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")

# Tu portafolio DEMO de $1000
PORTAFOLIO = {
    "BTC": {"cantidad": 0.01, "entrada": 65000},
    "ETH": {"cantidad": 0.1, "entrada": 3200},
    "SOL": {"cantidad": 2, "entrada": 140}
}

def get_precios():
    try:
        # API de Binance que sí funciona en Render
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5)
        data = {item['symbol']: float(item['price']) for item in r.json()}
        return {
            "BTC": data.get("BTCUSDT", 68432),
            "ETH": data.get("ETHUSDT", 3450),
            "SOL": data.get("SOLUSDT", 165)
        }
    except:
        # Si falla, precios demo
        return {"BTC": 68432, "ETH": 3450, "SOL": 165}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot Rub Activo!\nEscribe: precio")

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    precios = get_precios()
    mensaje = "💰 **TU PORTAFOLIO $1000 DEMO**\n\n"
    ganancia_total = 0
    valor_total = 0

    for moneda, info in PORTAFOLIO.items():
        precio_actual = precios[moneda]
        valor_actual = info["cantidad"] * precio_actual
        valor_entrada = info["cantidad"] * info["entrada"]
        ganancia = valor_actual - valor_entrada
        ganancia_total += ganancia
        valor_total += valor_actual

        signo = "🟢" if ganancia >= 0 else "🔴"
        mensaje += f"{signo} {moneda}: ${precio_actual:,.2f}\n"
        mensaje += f" Tienes: {info['cantidad']} = ${valor_actual:.2f} ({ganancia:+.2f})\n\n"

    mensaje += f"--------------------\n"
    mensaje += f"💵 Valor total: ${valor_total:.2f}\n"
    mensaje += f"📈 Ganancia total: ${ganancia_total:+.2f}"

    await update.message.reply_text(mensaje)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await precio(update, context)

print("BOT 3 CRYPTOS INICIADO")
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_polling()
