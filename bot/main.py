from flask import Flask, jsonify, request
import os, json, requests
from datetime import datetime
app = Flask(__name__)
TOKEN = os.getenv('TELEGRAM_TOKEN','')
FILE='trades.json'
def load():
 try:
  import json as js
  return js.load(open(FILE))
 except:
  return {'coin':'BTC','auto_on':False,'balance':1000,'signal':'ESPERA','trades':[],'chat_id':None}
def save(d):
 json.dump(d, open(FILE,'w'))
def send(cid,t):
 if not TOKEN or not cid: return
 kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['AUTO']],'resize_keyboard':True}
 requests.post('https://api.telegram.org/bot'+TOKEN+'/sendMessage',json={'chat_id':cid,'text':t,'reply_markup':json.dumps(kb)},timeout=10)
@app.route('/')
def home(): return '<h1>BOT V511 LIVE</h1>'
@app.route('/api/status')
def st(): return jsonify(load())
@app.route('/api/set',methods=['POST'])
def setc():
 d=load(); j=request.get_json() or {}
 for k in ['coin','auto_on','signal']:
  if k in j: d[k]=j[k]
 save(d); return jsonify({'ok':True})
@app.route('/webhook',methods=['POST'])
def wh():
 data=request.get_json(silent=True) or {}
 cid=data.get('message',{}).get('chat',{}).get('id')
 txt=(data.get('message',{}).get('text','') or '').upper().strip()
 d=load()
 if cid: d['chat_id']=cid
 if txt in ['BTC','ETH','SOL','XRP']: d['coin']=txt; send(cid,'Coin '+txt)
 elif txt=='AUTO': d['auto_on']=not d.get('auto_on',False); send(cid,'AUTO '+str(d['auto_on']))
 elif txt in ['/START','START','/BALANCE','BALANCE']: send(cid,'RESUMEN '+d['coin']+' '+str(d['balance']))
 save(d); return 'ok'
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT',10000)))
