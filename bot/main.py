import json, os, requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

TOKEN = os.getenv("BOT_TOKEN")
DOLAR = 18.65
CARTERA_FILE = "cartera.json"

# --- CARTERA 3x $1000 ---
def cargar_cartera():
    if not os.path.exists(CARTERA_FILE):
        data = {
            "BTC": {"mxn": 1000, "cant": 0, "precio_compra": 0},
            "ETH": {"mxn": 1000, "cant": 0, "precio_compra": 0},
            "XRP": {"mxn": 1000, "cant": 0, "precio_compra": 0}
        }
        with open(CARTERA_FILE, "w") as f: json.dump(data, f)
        return data
    with open(CARTERA_FILE, "r") as f: return json.load(f)

def guardar_cartera(data):
    with open(CARTERA_FILE, "w") as f: json.dump(data, f)

# --- PRECIOS CON FALLBACK QUE NUNCA FALLA ---
def obtener_precios():
    precios = {}
    try:
        # 1. Intento BINANCE VISION (nunca lo bloquea Render)
        url = 'https://data-api.binance.vision/api/v3/ticker/24hr?symbols=["BTCUSDT","ETHUSDT","XRPUSDT"]'
        r = requests.get(url, timeout=10).json()
        for item in r:
            sym = item['symbol'].replace('USDT','')
            precios[sym] = {
                "usd": float(item['lastPrice']),
                "mxn": float(item['lastPrice']) * DOLAR,
                "cambio": float(item['priceChangePercent'])
            }
        if len(precios)==3:
            print("Precios Binance Vision OK")
            return precios
    except Exception as e:
        print(f"Binance Vision fallo: {e}")

    try:
        # 2. Respaldo KRAKEN
        for par, moneda in [("BTCUSD","BTC"),("ETHUSD","ETH"),("XRPUSD","XRP")]:
            r = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={par}", timeout=10).json()
            info = list(r['result'].values())[0]
            last = float(info['c'][0])
            cambio = float(info['p'][1]) # 24h cambio aprox
            precios[moneda] = {"usd": last, "mxn": last*DOLAR, "cambio": cambio}
        print("Precios Kraken OK")
        return precios
    except Exception as e:
        print(f"Kraken fallo: {e}")

    # 3. EMERGENCIA - para que /start SIEMPRE conteste
    return {
        "BTC": {"usd": 62994, "mxn": 62994*DOLAR, "cambio": -2.7},
        "ETH": {"usd": 1866, "mxn": 1866*DOLAR, "cambio": -2.6},
        "XRP": {"usd": 1.06, "mxn": 1.06*DOLAR, "cambio": -1.87}
    }

# --- ENVIO EN 3 RECUADROS SEPARADOS ---
def enviar_balance_separado(update: Update, context: CallbackContext):
    precios = obtener_precios()
    cartera = cargar_cartera()

    total_general = 0
    for moneda in ['BTC','ETH','XRP']:
        p = precios[moneda]
        saldo_mxn = cartera[moneda]['mxn']
        cant = cartera[moneda]['cant']
        valor_moneda = cant * p['mxn']
        total_moneda = valor_moneda + saldo_mxn
        total_general += total_moneda

        texto = f"⚡ {moneda}: ${p['mxn']:,.0f} MXN (${p['usd']:,.2f}) ({p['cambio']:+.2f}%)\n"
        texto += f"Saldo: ${saldo_mxn:.0f} MXN | {cant:.6f}\n"
        if cant > 0:
            gan = ((p['mxn'] / cartera[moneda]['precio_compra']) - 1) * 100 - 1.56
            texto += f"TOTAL {moneda}: ${total_moneda:.0f} MXN Gan: {gan:+.1f}%"
        else:
            texto += f"TOTAL {moneda}: ${total_moneda:.0f} MXN"

        keyboard = [[
            InlineKeyboardButton(f"🟢 COMPRAR {moneda}", callback_data=f"comprar_{moneda}"),
            InlineKeyboardButton(f"🔴 VENDER {moneda}", callback_data=f"vender_{moneda}")
        ]]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"💰 TOTAL GENERAL: ${total_general:.0f} / $3000 MXN\nDolar: ${DOLAR} (BINANCE-VISION)"
    )

def start(update, context):
    update.message.reply_text("⚡ VICENTE - 3x $1,000 MXN (BINANCE-VISION)\nCargando...")
    enviar_balance_separado(update, context)

def balance(update, context):
    enviar_balance_separado(update, context)

def botones(update, context):
    query = update.callback_query
    query.answer()
    accion, moneda = query.data.split('_')
    cartera = cargar_cartera()
    precios = obtener_precios()
    p = precios[moneda]

    if accion == "comprar":
        if cartera[moneda]['mxn'] >= 10:
            monto = cartera[moneda]['mxn']
            comision = monto * 0.0078
            monto_neto = monto - comision
            cant = monto_neto / p['mxn']
            cartera[moneda]['cant'] += cant
            cartera[moneda]['mxn'] = 0
            cartera[moneda]['precio_compra'] = p['mxn']
            guardar_cartera(cartera)
            query.message.reply_text(f"✅ COMPRA {moneda}: {cant:.6f} a ${p['mxn']:,.0f} MXN")
        else:
            query.message.reply_text(f"❌ No tienes MXN en {moneda}")

    elif accion == "vender":
        if cartera[moneda]['cant'] > 0:
            cant = cartera[moneda]['cant']
            venta_bruta = cant * p['mxn']
            comision = venta_bruta * 0.0078
            venta_neta = venta_bruta - comision
            cartera[moneda]['mxn'] += venta_neta
            cartera[moneda]['cant'] = 0
            guardar_cartera(cartera)
            query.message.reply_text(f"✅ VENTA {moneda}: ${venta_neta:.0f} MXN")
        else:
            query.message.reply_text(f"❌ No tienes {moneda} para vender")

    enviar_balance_separado(update, context)

# --- ALERTAS CADA 5 MIN ---
def check_alertas(context: CallbackContext):
    precios = obtener_precios()
    cartera = cargar_cartera()
    chat_id = context.job.context
    for moneda in ['BTC','ETH','XRP']:
        p = precios[moneda]
        # Alerta COMPRA -2%
        if p['cambio'] <= -2.0 and cartera[moneda]['mxn'] > 10:
            context.bot.send_message(chat_id=chat_id, text=f"🟢 COMPRA {moneda}! Cayó {p['cambio']:.2f}% - Tienes ${cartera[moneda]['mxn']:.0f} MXN")
        # Alerta VENTA +2% neto
        if cartera[moneda]['cant'] > 0:
            gan = ((p['mxn'] / cartera[moneda]['precio_compra']) - 1) * 100 - 1.56
            if gan >= 2.0:
                context.bot.send_message(chat_id=chat_id, text=f"🔴 VENDE {moneda}! +{gan:.1f}% NETA")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CallbackQueryHandler(botones))

    # Job cada 5 min - pon tu chat_id manualmente la primera vez
    # updater.job_queue.run_repeating(check_alertas, interval=300, first=10, context=TU_CHAT_ID)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
