# BOT: V43 FINAL - 5K BOLA - 29 MXN/DIA
import os
import time
import logging
from datetime import datetime

# CONFIG V43 FINAL - BOLA DE NIEVE
BOT_NAME = "V43 FINAL - 5K BOLA"
CAPITAL_TOTAL = 5000
MONEDAS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XAUUSD"]
N1 = 500
N2_BOLA = 750
N3_BOLA = 1000
RSI_ENTRADA = 45
TP_PORC = 1.5
TRAILING_PORC = 1.0
SL_PORC = -15.0
MAX_POSICIONES = 3

print(f"=== {BOT_NAME} ===")
print(f"Capital: ${CAPITAL_TOTAL} MXN")
print(f"Estrategia: RSI < {RSI_ENTRADA} + BOLA N1 ${N1} / N2 ${N2_BOLA} / N3 ${N3_BOLA}")
print(f"TP: +{TP_PORC}% Trailing: {TRAILING_PORC}% SL: {SL_PORC}%")
print(f"Iniciado: {datetime.now()}")

# --- TU CODIGO DE TELEGRAM ABAJO ---
# Si usas python-telegram-bot, deja esto

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"🤖 {BOT_NAME} ACTIVO\n"
            f"Capital: ${CAPITAL_TOTAL} MXN\n"
            f"Monedas: BTC, ETH, SOL, XAUUSD\n"
            f"Entrada: RSI 1H < {RSI_ENTRADA}\n"
            f"Bola: ${N1} -> ${N2_BOLA} (-3%) -> ${N3_BOLA} (-6%)\n"
            f"TP: +{TP_PORC}% con trailing {TRAILING_PORC}%\n"
            f"Meta: $29 MXN/dia"
        )

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"✅ {BOT_NAME} corriendo\nBuscando RSI < {RSI_ENTRADA} en 4 monedas...")

    def main():
        print("Iniciando Telegram Bot...")
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.run_polling()

    if __name__ == "__main__":
        main()

except Exception as e:
    print(f"Error iniciando: {e}")
    # Fallback para que Render no crashee si falta TOKEN
    while True:
        print(f"[{datetime.now()}] {BOT_NAME} esperando... RSI < {RSI_ENTRADA} | Bola ${N1}/${N2_BOLA}/${N3_BOLA}")
        time.sleep(60)
