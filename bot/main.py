from flask import Flask, jsonify, request
import os, json, requests
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CHAT_FILE = 'trades.json'
app = Flask(__name__)

def load():
    try:
        with open(CHAT_FILE,'r') as f:
            return json.load(f)
    except:
        return {'trades':[],'balance':1000.0,'hoy':0.0,'ganados':0,'perdidos':0,'chat_id':None,'auto_on':False,'coin':'BTC','signal':'ESPERA'}

def save(d):
    with open(CHAT_FILE,'w') as f:
        json.dump(d,f)

def send_msg(cid, txt):
    if not TOKEN or not cid:
        return
    kb = {'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR','VENDER'],['AUTO']],'resize_keyboard':True}
    payload = {'chat_id':cid,'text':txt,'reply_markup':json.dumps(kb)}
    try:
        requests.post('https://api.telegram.org/bot' + TOKEN + '/sendMessage', json=payload, timeout=10)
    except:
        pass

def resumen_text():
    d = load()
    now = datetime.now().strftime('%d/%m %H:%M')
    auto = 'AUTO ON' if d.get('auto_on') else 'AUTO OFF'
    bal = str(d.get('balance',0))
    coin = d.get('coin','BTC')
    sig = d.get('signal','ESPERA')
    return 'RESUMEN ' + now + ' PRACTICA\nBalance: $' + bal + '\nCoin: ' + coin + ' | ' + sig + '\n' + auto

@app.route('/')
def home():
    if os.path.exists('bot/templates/index.html'):
        with open('bot/templates/index.html',
