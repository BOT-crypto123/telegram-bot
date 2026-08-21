from flask import Flask
import threading
import telebot
from telebot import types
import time

app = Flask(__name__)

BOT_TOKEN = "8602791768:AAEJB1QGlx4NWKXCka1nSFlKIurBZ1LwAmA"
DASHBOARD_URL = "https://telegram-bot-c...nder.com" # pon tu url real de render
bot = telebot.TeleBot(BOT_TOKEN)

CONFIG = {
    "dia_actual": 5,
    "dias_totales": 30,
    "BALANCE_INICIAL": 10000,
    "BALANCE": 10310.99,
    "profit_acumulado_neto": 310.99, # NETO = lo del centro
    "profit_bruto_acum": 350.50,
    "profit_fees_acum": 39.51,
    "COINS": ["SOL", "DOGE", "PEPE", "SHIB", "BONK", "FLOKI"],
    "COINS_ACTIVAS": {"SOL": True, "DOGE": True, "PEPE": True, "SHIB": True, "BONK": False, "FLOKI": False},
    "prices": {"SOL": 150.68, "DOGE": 0.1508, "PEPE": 0.000008, "SHIB": 0.000025, "BONK": 0.000030, "FLOKI": 0.00020},
    "bolas": [],
    "AUTO_TRADING": True,
    "CAIDA_MAX": 0.6,
    "MAX_BOLAS": 4,
    "CHAT_ID": None
}

# ESTA FUNCION ES LA CLAVE DE LO QUE PEDISTE EN AUDIO
def logica_entrada(coin, caida):
    if len(CONFIG["bolas"]) >= CONFIG["MAX_BOLAS"]: return
    if not CONFIG["COINS_ACTIVAS"].get(coin): return

    if CONFIG["AUTO_TRADING"]:
        CONFIG["bolas"].append({"coin": coin, "entry": CONFIG["prices"][coin]})
        texto = f"🟢 AUTO ON - COMPRE {coin}\nCaida: -{caida}%\nPrecio: {CONFIG['prices'][coin]}\nBola {len(CONFIG['bolas'])}/{CONFIG['MAX_BOLAS']}"
    else:
        texto = f"🔔 SEÑAL - HAY ENTRADA {coin}\nCaida: -{caida}%\nPrecio: {CONFIG['prices'][coin]}\nROBOT APAGADO - No compre, solo aviso."

    if CONFIG["CHAT_ID"]:
        try: bot.send_message(CONFIG["CHAT_ID"], texto)
        except: pass

def get_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    estado_txt = "🟢 ROBOT PRENDIDO" if CONFIG["AUTO_TRADING"] else "🔴 ROBOT APAGADO"
    btn_estado = "🔴 APAGAR ROBOT" if CONFIG["AUTO_TRADING"] else "🟢 PRENDER ROBOT"

    m.add(types.InlineKeyboardButton(estado_txt, callback_data="info"))
    m.add(
        types.InlineKeyboardButton(btn_estado, callback_data="toggle_auto"),
        types.InlineKeyboardButton("📊 DASHBOARD", url=DASHBOARD_URL)
    )
    m.add(
        types.InlineKeyboardButton(f"📉 CAIDA: 0.1% a {CONFIG['CAIDA_MAX']}%", callback_data="menu_caida"),
        types.InlineKeyboardButton(f"🔵 BOLAS: {CONFIG['MAX_BOLAS']}/8", callback_data="menu_bolas")
    )
    m.add(types.InlineKeyboardButton("💰 MONEDAS ON/OFF", callback_data="menu_coins"))
    return m

@bot.message_handler(commands=['start','menu'])
def start_cmd(message):
    CONFIG["CHAT_ID"] = message.chat.id
    modo = "PRENDIDO: Compra/Vende solo" if CONFIG["AUTO_TRADING"] else "APAGADO: Solo señales"
    bot.send_message(message.chat.id, f"MAQUINA V58\nBase $10k | Neto Acum +${CONFIG['profit_acumulado_neto']}\nModo: {modo}", reply_markup=get_menu())

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "toggle_auto":
        CONFIG["AUTO_TRADING"] = not CONFIG["AUTO_TRADING"]
        txt = "PRENDIDO" if CONFIG["AUTO_TRADING"] else "APAGADO"
        bot.answer_callback_query(call.id, f"Robot {txt}")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_menu())
        bot.send_message(call.message.chat.id, f"Robot ahora {txt}:\n{'Compra y vende solo' if CONFIG['AUTO_TRADING'] else 'Solo manda señales, no compra'}", reply_markup=get_menu())

    elif call.data == "menu_caida":
        k = types.InlineKeyboardMarkup(row_width=3)
        for v in [0.1,0.2,0.3,0.4,0.5,0.6]: k.add(types.InlineKeyboardButton(f"0.1 a {v}%", callback_data=f"set_caida_{v}"))
        bot.send_message(call.message.chat.id, "Elige rango:", reply_markup=k)

    elif call.data.startswith("set_caida_"):
        CONFIG["CAIDA_MAX"] = float(call.data.split("_")[-1])
        bot.send_message(call.message.chat.id, f"✅ Caida 0.1% a {CONFIG['CAIDA_MAX']}%", reply_markup=get_menu())

    elif call.data == "menu_bolas":
        k = types.InlineKeyboardMarkup(row_width=4)
        for i in range(2,9): k.add(types.InlineKeyboardButton(f"{i}", callback_data=f"set_bolas_{i}"))
        bot.send_message(call.message.chat.id, "Max bolas:", reply_markup=k)

    elif call.data.startswith("set_bolas_"):
        CONFIG["MAX_BOLAS"] = int(call.data.split("_")[-1])
        bot.send_message(call.message.chat.id, f"✅ Max {CONFIG['MAX_BOLAS']}", reply_markup=get_menu())

    elif call.data == "menu_coins":
        k = types.InlineKeyboardMarkup(row_width=2)
        for c in CONFIG["COINS"]:
            on = CONFIG["COINS_ACTIVAS"][c]
            k.add(types.InlineKeyboardButton(f"{'✅' if on else '❌'} {c}", callback_data=f"tog_{c}"))
        k.add(types.InlineKeyboardButton("⬅️ Volver", callback_data="back"))
        bot.send_message(call.message.chat.id, "Prende/apaga monedas:", reply_markup=k)

    elif call.data.startswith("tog_"):
        coin = call.data.split("_")[1]
        CONFIG["COINS_ACTIVAS"][coin] = not CONFIG["COINS_ACTIVAS"][coin]
        bot.answer_callback_query(call.id, f"{coin} {'ON' if CONFIG['COINS_ACTIVAS'][coin] else 'OFF'}")

    elif call.data == "back":
        bot.send_message(call.message.chat.id, "Menu:", reply_markup=get_menu())

@app.route("/")
def dash():
    dia = CONFIG["dia_actual"]
    tot = CONFIG["dias_totales"]
    prog = (dia/tot)*100
    circ = 565.48
    off = circ - (prog/100*circ)
    return f"""
    <html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='10'></head>
    <body style='background:#0a0a0a;color:#e0e0e0;font-family:monospace;padding:10px'>
    <h1 style='color:#FFD700;text-align:center'>MAQUINA DE HACER DINERO</h1>
    <div style='text-align:center;font-size:11px'>{'🟢 PRENDIDO - Auto' if CONFIG['AUTO_TRADING'] else '🔴 APAGADO - Solo señales'} | Caida 0.1% a {CONFIG['CAIDA_MAX']}% | Bolas {CONFIG['MAX_BOLAS']}/8</div>
    <div style='display:flex;justify-content:center;margin:15px 0'>
      <div style='position:relative;width:280px;height:280px'>
        <svg width='280' height='280' style='transform:rotate(-90deg)'><circle cx='140' cy='140' r='90' stroke='#fff' stroke-opacity='0.1' stroke-width='18' fill='none'/><circle cx='140' cy='140' r='90' stroke='#FFD700' stroke-width='18' fill='none' stroke-dasharray='{circ}' stroke-dashoffset='{off}' stroke-linecap='round'/></svg>
        <div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center'>
          <div style='color:#888;font-size:11px'>BASE ${CONFIG['BALANCE_INICIAL']}</div>
          <div style='color:#0f0;font-size:32px;font-weight:bold'>+${CONFIG['profit_acumulado_neto']:.2f}</div>
          <div style='color:#0f0;font-size:11px'>NETA ACUMULADA</div>
          <div style='font-size:9px;color:#666'>BRUTA ${CONFIG['profit_bruto_acum']:.2f} - FEES ${CONFIG['profit_fees_acum']:.2f}<br>DIA {dia}/{tot} {prog:.0f}%</div>
        </div>
      </div>
    </div>
    </body></html>
    """

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
