import os, json, requests
from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
FILE="bot_data.json"
data={"capital_actual":450.0,"pos":[{"sym":"ETH","monto":50.0,"entry":2428.64,"ahora":2428.64,"gan_neta_pct":0}],"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"max_entradas":10,"tp_bruto":0.5,"sl_pct":-2.0,"rsi_venta":72.0,"filtro_ema":"OFF","rsi_compra":35.0,"rsi_por_moneda":{},"coins_activas":{"BTC":True,"ETH":True,"SOL":True,"XRP":True,"DOGE":True,"AVAX":True,"LINK":True,"ADA":True},"alert_users":[]}
def P(s):
 try:
  j=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT",timeout=4).json()
  return float(j['price'])
 except: return 0
def send(chat, text):
 if not TOKEN: return
 requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":chat,"text":text,"parse_mode":"HTML"},timeout=5)
@app.route('/', methods=['GET','POST'])
def root():
 if request.method=='POST':
  d=request.json or {}
  if "message" in d:
   chat=d["message"]["chat"]["id"]; txt=d["message"]["text"].upper()
   if "DASHBOARD" in txt or "/START" in txt or "START" in txt:
    send(chat,f"💰 <b>Máquina de Hacer Dinero</b>\nCapital: $450\nETH: $2428.64\n\n<a href='https://telegram-bot-cijp.onrender.com/dashboard'>VER DASHBOARD</a>")
  return jsonify({"ok":True})
 return "OK",200
@app.route('/api/prices')
def prices():
 out={}
 for s in data["coins"]:
  out[s]={"price":P(s),"rsi":30,"ok":False,"motivo":"Esperando","limite":35}
 return jsonify(out)
@app.route('/api/state')
def state():
 return jsonify({"capital":450.0,"bola":45.0,"pos":data["pos"],"max_entradas":10,"tp":0.5,"sl_pct":-2.0,"rsi_venta":72.0,"filtro_ema":"OFF","rsi_compra":35.0})
@app.route('/api/config', methods=['POST'])
def cfg(): return jsonify({"ok":True})
@app.route('/api/buy/<sym>', methods=['POST'])
def buy(sym): return jsonify({"ok":True})
@app.route('/api/sell/<sym>', methods=['POST'])
def sell(sym): return jsonify({"ok":True})
@app.route('/api/toggle', methods=['POST'])
def tog(): return jsonify({"ok":True})
@app.route('/dashboard')
def dash():
 return open("dashboard.html").read()
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
