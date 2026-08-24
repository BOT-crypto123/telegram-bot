import os, json
from flask import Flask, request, send_from_directory, jsonify
import telegram
from telegram import Update

app = Flask(__name__)

FILE='state.json'
DEFAULT={
 "disponible":500,"bloqueado":0,"gan_mes":0,
 "modo":"CONSERVADOR","rsi_compra_m":35,
 "disponible_m":500,"bloqueado_m":0,
 "gan_mes_m":0,"modo_m":"MEDIO","max_m":5
}

def load_state():
 try:
  if os.path.exists(FILE):
   with open(FILE) as f:
    data = json.load(f)
    # junta default con lo guardado para que no falte nada
    merged = DEFAULT.copy()
    merged.update(data)
    return merged
 except Exception as e:
  print("Error load_state", e)
 return DEFAULT.copy()

def save_state(state):
 with open(FILE, 'w') as f:
  json.dump(state, f)

@app.route('/')
def index():
 return send_from_directory('.','index.html')

@app.route('/dashboard')
def dash():
 return send_from_directory('.','dashboard.html')

@app.route('/dashboard_mt5.html')
def dashm():
 return send_from_directory('.','dashboard_mt5.html')

@app.route('/api/state')
def api_state():
 return jsonify(load_state())

@app.route('/api/state', methods=['POST'])
def api_state_save():
 data = request.get_json(force=True)
 save_state(data)
 return jsonify({"ok": True})

@app.route('/api/upload', methods=['POST'])
def api_upload():
 # para restaurar respaldo
 try:
  data = request.get_json(force=True)
  # si viene con formato de respaldo viejo, lo normalizamos
  if isinstance(data, dict):
   save_state(data)
   return jsonify({"ok": True})
  return jsonify({"ok": False, "error": "formato invalido"})
 except Exception as e:
  return jsonify({"ok": False, "error": str(e)}), 400

@app.route('/api/prices')
def api_prices():
 # Agregué RSI para que no salga undefined en los 3 circulos
 return jsonify({
  "BTC": 77355.93, "BTC_RSI": 62,
  "ETH": 2439.75, "ETH_RSI": 58,
  "SOL": 94.26, "SOL_RSI": 55
 })

BOT_TOKEN=os.environ.get("BOT_TOKEN","")
bot=telegram.Bot(token=BOT_TOKEN) if BOT_TOKEN else None

@app.route('/telegram',methods=['POST'])
def tg():
 if not bot:
  return 'no bot'
 data=request.get_json(force=True)
 up=Update.de_json(data,bot)
 if not up.message:
  return 'ok'
 txt=(up.message.text or '').upper()
 cid=up.message.chat.id
 if 'DASHBOARD' in txt or '/START' in txt or 'DUAL' in txt or 'HOLA' in txt:
  # AQUI ESTA EL CAMBIO: Solo AMBAS, ya no MT5
  bot.send_message(chat_id=cid,text="DUAL V5 AMBAS $1000\n\nPORTADA:\nhttps://telegram-bot-cijp.onrender.com/\n\nDASHBOARD AMBAS (BINANCE + MT5):\nhttps://telegram-bot-cijp.onrender.com/dashboard")
 return 'ok'

@app.route('/set_webhook')
def sethook():
 if not bot:
  return 'Falta BOT_TOKEN en Render'
 bot.set_webhook(url='https://telegram-bot-cijp.onrender.com/telegram')
 return 'WEBHOOK PUESTO!'

if __name__=='__main__':
 app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
