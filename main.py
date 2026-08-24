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
    return json.load(f)
 except:
  pass
 return DEFAULT.copy()

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

@app.route('/api/prices')
def api_prices():
 return jsonify({"BTC":77355.93,"ETH":2439.75,"SOL":94.26})

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
  bot.send_message(chat_id=cid,text="DUAL V5 $1000\n\nPORTADA:\nhttps://telegram-bot-cijp.onrender.com/\n\nBINANCE $62.5:\nhttps://telegram-bot-cijp.onrender.com/dashboard\n\nMT5 $100:\nhttps://telegram-bot-cijp.onrender.com/dashboard_mt5.html")
 return 'ok'

@app.route('/set_webhook')
def sethook():
 if not bot:
  return 'Falta BOT_TOKEN en Render'
 bot.set_webhook(url='https://telegram-bot-cijp.onrender.com/telegram')
 return 'WEBHOOK PUESTO!'

if __name__=='__main__':
 app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
