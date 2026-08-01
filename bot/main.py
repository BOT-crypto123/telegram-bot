import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
# TUS DATOS REALES
XRP_CANT = 555.55
XRP_COMPRA = 0.60

def get_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd"
        r = requests.get(url, timeout=10).json()
        return {
            "BTC": r["bitcoin"]["usd"],
            "ETH": r["ethereum"]["usd"],
            "XRP": r["ripple"]["usd"]
        }
    except Exception as e:
        print(f"Error precios: {e}")
        return None

def texto_balance():
    prices = get_prices()
    if not prices:
        return "Error obteniendo precios, intenta de nuevo"
    btc_p = prices["BTC"]
    eth_p = prices["ETH"]
    xrp_p = prices["XRP"]
    
    xrp_valor = XRP_CANT * xrp_p
    compra_total = XRP_CANT * XRP_COMPRA
    ganancia = xrp_valor - compra_total
    porcentaje = ((xrp_p - XRP_COMPRA) / XRP_COMPRA * 100) if XRP_COMPRA>0 else 0
    
    txt = f"💰 BALANCE V22.3 LIVE\n\n"
    txt += f"📦 Tienes: {XRP_CANT} XRP\n"
    txt += f"💵 Valor: ${xrp_valor:.2f}\n"
    txt += f"🎯 Compra: ${XRP_COMPRA:.4f}\n"
    txt += f"📊 Ganancia: {porcentaje:+.2f}% (${ganancia:.2f})\n\n"
    txt += f"BTC: ${btc_p:,.2f}\nETH: ${eth_p:,.2f}\nXRP: ${xrp_p:.4f}"
    return txt

def get_menu():
    keyboard = [
        [InlineKeyboardButton("🟢 Comprar XRP", callback_data="comprar"), InlineKeyboardButton("🔴 Vender XRP", callback_data="vender")],
        [InlineKeyboardButton("💰 Ver Todo", callback_data="vertodo")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(texto_balance(), reply_markup=get_menu())

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(texto_balance(), reply_markup=get_menu())

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_prices()
    await update.message.reply_text(f"BTC: ${p['BTC']:,.2f}" if p else "Error")

async def eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_prices()
    await update.message.reply_text(f"ETH: ${p['ETH']:,.2f}" if p else "Error")

async def xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_prices()
    await update.message.reply_text(f"XRP: ${p['XRP']:.4f}" if p else "Error")

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "vertodo":
        await query.edit_message_text(texto_balance(), reply_markup=get_menu())
    elif query.data == "comprar":
        await query.edit_message_text("🟢 Para comprar más XRP, dime cuántos quieres agregar.\nEj: /comprar 100", reply_markup=get_menu())
    elif query.data == "vender":
        await query.edit_message_text("🔴 Para vender, dime cuántos.\nEj: /vender 100", reply_markup=get_menu())

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot V22.3 LIVE OK")
    def log_message(self, *a): pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Iniciando Bot V22.3...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("xrp", xrp))
    app.add_handler(CallbackQueryHandler(botones))
    print("Bot V22.3 listo - polling")
    app.run_polling()
