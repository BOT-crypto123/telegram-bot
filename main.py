import os, json, time, threading, requests
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
app=Flask(__name__)
DATA_FILE='bot_data.json';FEE=0.001
POSIBLES=['/data/bot_data.json','bot_data.json']
default_data={'capital_binance':500.0,'capital_mt5':500.0,'usd_mxn':18.5,'gan_acum_total':0.0,'ganadas':0,'salidas':0,'tp':0.3,'sl_pct':-1.5,'rsi_compra':35,'rsi_venta':70,'filtro_ema':'OFF','max_entradas':8,'auto':True,'auto_tune':True,'pos':[],'pos_short':[],'historial':[],'coins_activas':{'BTC':True,'ETH':True,'SOL':True,'BNB':True,'XRP':True,'ADA':True,'AVAX':True,'DOGE':True},'alert_users':[]}
try:
 for p in POSIBLES:
  if os.path.exists(p):
   with open(p) as f: data=json.load(f);break
 else: raise FileNotFoundError
 for k,v in default_data.items():
  if k not in data: data[k]=v
except: data=default_data.copy()
def save():
 for p in [DATA_FILE,'/data/bot_data.json']:
  try: Path(p).parent.mkdir(parents=True,exist_ok=True);json.dump(data,open(p,'w'))
  except: pass
USD_CACHE={'price':18.5,'t':0,'last_ok':18.5}
def get_usd_mxn_live(force=False):
 now=time.time()
 if not force and now-USD_CACHE['t']<60: return USD_CACHE['price']
 try:
  r=requests.get('https://open.er-api.com/v6/latest/USD',timeout=8).json()
  mxn=float(r['rates']['MXN'])
  if 10<mxn<30: USD_CACHE['price']=mxn;USD_CACHE['t']=now;USD_CACHE['last_ok']=mxn;data['usd_mxn']=mxn;save();return mxn
 except: pass
 return USD_CACHE.get('last_ok',18.5)
SYMS=['BTC/USDT','ETH/USDT','SOL/USDT','BNB/USDT','XRP/USDT','ADA/USDT','AVAX/USDT','DOGE/USDT']
def get_rsi(prices,p=14):
 if len(prices)<p+1: return 50
 gains=losses=0
 for i in range(1,p+1):
  d=prices[-i]-prices[-i-1]
  if d>=0: gains+=d
  else: losses+=-d
 if losses==0: return 100
 rs=gains/losses;return 100-(100/(1+rs))
def get_prices_data():
 out={}
 for sym in SYMS:
  coin=sym.replace('/USDT','');bin_sym=sym.replace('/','')
  try:
   r=requests.get(f'https://data-api.binance.vision/api/v3/klines?symbol={bin_sym}&interval=1h&limit=100',timeout=10).json()
   closes=[float(k[4]) for k in r];price=closes[-1];rsi=get_rsi(closes);ema=sum(closes[-20:])/20
   out[coin]={'price':price,'rsi':round(rsi,1),'ema':ema,'ok':rsi<=data['rsi_compra'],'ok_short':rsi>=data['rsi_venta']}
  except: out[coin]={'price':0,'rsi':50,'ema':0,'ok':False,'ok_short':False}
 return out
@app.route('/')
def home(): return 'BOT LIVE V5 CEL FIX - OK',200
@app.route('/dashboard')
def dashboard():
 if os.path.exists('dashboard.html'): return send_from_directory('.','dashboard.html')
 return 'No dashboard.html',404
@app.route('/api/prices')
def api_prices(): return jsonify(get_prices_data())
@app.route('/api/state')
def api_state():
 usd_live=get_usd_mxn_live();max_ent=data.get('max_entradas',8);bola_base=data.get('capital_binance',500.0)/max(1,max_ent);prices=get_prices_data()
 for p in data.get('pos',[]): pr=prices.get(p['sym'],{}).get('price',p['entry']);p['ahora']=pr;p['gan_neta_pct']=(pr-p['entry'])/p['entry']*100
 for p in data.get('pos_short',[]): pr=prices.get(p['sym'],{}).get('price',p['entry']);p['ahora']=pr;p['gan_neta_pct']=(p['entry']-pr)/p['entry']*100
 bloqueado=sum([x.get('monto',bola_base) for x in data.get('pos',[])])+sum([x.get('monto',bola_base) for x in data.get('pos_short',[])])
 gan_total=data.get('gan_acum_total',0.0);capital_bin=data.get('capital_binance',500.0)
 if bloqueado==0: disponible=capital_bin;total_real=capital_bin+gan_total
 else: disponible=capital_bin-bloqueado;total_real=disponible+bloqueado+gan_total
 bola_real=total_real/max(1,max_ent)
 return jsonify({'capital_binance':capital_bin,'capital':total_real+data.get('capital_mt5',500.0),'total_real_usd':total_real,'bola':bola_real,'bola_mxn':bola_real*usd_live,'usd_mxn':round(usd_live,4),'gan_acum':gan_total,'disponible_usd':disponible,'bloqueado_usd':bloqueado,'pos':data.get('pos',[])+data.get('pos_short',[]),'historial':data.get('historial',[])[-20:]})
@app.route('/api/config',methods=['POST'])
def api_config():
 j=request.json
 if 'max' in j: data['max_entradas']=int(j['max'])
 save();return jsonify(ok=True)
@app.route('/api/toggle',methods=['POST'])
def toggle(): data['auto']=not data['auto'];save();return jsonify(ok=True)
def auto_loop():
 while True:
  try:
   if data['auto']:
    prices=get_prices_data()
    if len(data['pos'])<data['max_entradas']:
     for sym,info in prices.items():
      if info['price']>0 and info['ok'] and not any(x['sym']==sym for x in data['pos']):
       data['pos'].append({'sym':sym,'entry':info['price'],'monto':data['capital_binance']/data['max_entradas']});save();break
  except: pass
  time.sleep(60)
threading.Thread(target=auto_loop,daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
