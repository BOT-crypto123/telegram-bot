import os, json
from flask import Flask, request, send_from_directory, jsonify
import telegram
from telegram import Update
from datetime import datetime

app = Flask(__name__)
FILE='state.json'

DEFAULT={
 # BINANCE $500
 "disponible_usd":500,"bloqueado_usd":0,"gan_acum":0.59,"gan_mes":0,"ganadas":1,"winrate":100,"tp":0.7,"sl_pct":-1.5,"rsi_venta":70,"filtro_ema":"ON","rsi_compra":35,"modo":"AMBOS","max_entradas":8,"usd_mxn":16.96,"pct_mes":0,"auto":True,"auto_tune":False,"fee_total":0.2,
 "coins_activas":{"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"DOGE":True,"ADA":True,"AVAX":True},
 "pos":[],"pos_long":[],"pos_short":[],"historial":[],"capital_history":[{"t":datetime.now().isoformat(),"cap":500}],
 # MT5 $500
 "disponible_m":500,"bloqueado_m":0,"gan_mt5":0,"gan_mes_m":0,"ganadas_m":0,"winrate_m":0,"tp_m":0.8,"sl_m":-1.2,"rsi_venta_m":70,"filtro_ema_m":"ON","rsi_compra_m":30,"modo_m":"AMBOS","max_m":4,"auto_m":True,"auto_tune_m":False,
 "coins_mt5_activas":{"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True},
 "pos_m":[],"pos_m_short":[],"historial_m":[],"capital_history_m":[{"t":datetime.now().isoformat(),"cap":500}]
}

def load_state():
 try:
  if os.path.exists(FILE):
   with open(FILE) as f:
    data=json.load(f)
    m=DEFAULT.copy()
    m.update(data)
    return m
 except: pass
 return DEFAULT.copy()

def save_state(s):
 with open(FILE,'w') as f: json.dump(s,f)

@app.route('/')
def index(): return send_from_directory('.','index.html')
@app.route('/dashboard')
def dash(): return send_from_directory('.','dashboard.html')
@app.route('/dashboard_mt5.html')
def dashm(): return send_from_directory('.','dashboard_mt5.html')

@app.route('/api/state')
def api_state(): return jsonify(load_state())

@app.route('/api/prices')
def api_prices():
 coins=["BTC","ETH","SOL","BNB","XRP","DOGE","ADA","AVAX"]
 out={}
 for c in coins:
  out[c]={"price":100,"rsi":40,"limite":35,"ema":99,"sug":"ESPERAR","motivo":"Esperando RSI"}
 out["BTC"]["price"]=77355; out["ETH"]["price"]=2439; out["SOL"]["price"]=94.26
 return jsonify(out)

@app.route('/api/prices_mt5')
def api_prices_mt5():
 out={}
 for k,v in {"XAUUSD":2630,"XAGUSD":31.2,"USOIL":76.5,"SPX500":5950}.items():
  out[k]={"price":v,"rsi":58,"limite":30,"change":1.2,"ema":v*0.99,"sug":"ESPERAR MT5","motivo":"MT5 estrategia propia"}
 return jsonify(out)

@app.route('/api/config', methods=['POST'])
def api_config():
 st=load_state(); d=request.get_json(force=True)
 for k,v in d.items():
  if k=='toggle_coin': st['coins_activas'][v]=not st['coins_activas'].get(v,True)
  elif k=='toggle_coin_mt5': st['coins_mt5_activas'][v]=not st['coins_mt5_activas'].get(v,True)
  elif k=='max': st['max_entradas']=int(v)
  elif k=='max_m': st['max_m']=int(v)
  else: st[k]=v
 save_state(st); return jsonify({"ok":True})

@app.route('/api/toggle', methods=['POST'])
def api_toggle():
 st=load_state()
 data=request.get_json(force=True,silent=True) or {}
 side=data.get('side','')
 if side=='mt5': st['auto_m']=not st.get('auto_m',True)
 else: st['auto']=not st.get('auto',True)
 save_state(st); return jsonify({"ok":True})

@app.route('/api/sell/<sym>', methods=['POST'])
def api_sell(sym):
 st=load_state(); st['pos']=[p for p in st['pos'] if sym not in p.get('sym','')]; save_state(st); return jsonify({"ok":True})
@app.route('/api/sell_mt5/<sym>', methods=['POST'])
def api_sell_mt5(sym):
 st=load_state(); st['pos_m']=[p for p in st['pos_m'] if sym!=p.get('sym')]; st['pos_m_short']=[p for p in st['pos_m_short'] if sym!=p.get('sym')]; save_state(st); return jsonify({"ok":True})

@app.route('/api/backup')
def api_backup(): return jsonify(load_state())
@app.route('/api/restore', methods=['POST'])
def api_restore():
 try: save_state(request.get_json(force=True)); return jsonify({"ok":True})
 except Exception as e: return jsonify({"ok":False,"error":str(e)}),400

BOT_TOKEN=os.environ.get("BOT_TOKEN","")
bot=telegram.Bot(token=BOT_TOKEN) if BOT_TOKEN else None
@app.route('/telegram',methods=['POST'])
def tg():
 if not bot: return 'no bot'
 data=request.get_json(force=True); up=Update.de_json(data,bot)
 if not up.message: return 'ok'
 txt=(up.message.text or '').upper(); cid=up.message.chat.id
 if any(x in txt for x in ['DASHBOARD','/START','DUAL','HOLA']):
  bot.send_message(chat_id=cid,text="DUAL V5 AMBAS $1000\n\nDASHBOARD AMBAS (BINANCE $500 + MT5 $500):\nhttps://telegram-bot-cijp.onrender.com/dashboard\n\nMT5 Detalle:\nhttps://telegram-bot-cijp.onrender.com/dashboard_mt5.html")
 return 'ok'
@app.route('/set_webhook')
def sethook():
 bot.set_webhook(url='https://telegram-bot-cijp.onrender.com/telegram'); return 'WEBHOOK PUESTO!'

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
