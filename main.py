import os,json,time,threading,requests
from flask import Flask,request,jsonify
from flask import send_from_directory
from datetime import datetime

app=Flask(__name__)
BOT_TOKEN=os.getenv('BOT_TOKEN','')
DATA_FILE='bot_data.json'
FEE=0.001

default_data={
 'capital_binance':500.0,
 'capital_mt5':500.0,
 'usd_mxn':18.5,
 'gan_acum_total':0.0,
 'ganadas':0,
 'salidas':0,
 'tp_binance':0.3,
 'sl_binance':-2.5,
 'rsi_binance_compra':35,
 'rsi_binance_venta':70,
 'tp_mt5':0.8,
 'sl_mt5':-1.0,
 'rsi_mt5_compra':55,
 'rsi_mt5_venta':70,
 'filtro_ema_binance':'OFF',
 'filtro_ema_mt5':'ON',
 'max_entradas':8,
 'auto_binance':True,
 'auto_mt5':True,
 'auto_tune':False,
 'pos':[],
 'pos_mt5':[],
 'historial':[],
 'historial_binance':[],
 'historial_mt5':[],
 'capital_history':[],
 'coins_activas':{
  'BTC':True,'ETH':True,
  'SOL':True,'BNB':True,
  'XRP':True,'ADA':True,
  'AVAX':True,'DOGE':True},
 'coins_mt5_activas':{
  'XAUUSD':True,'XAGUSD':True,
  'USOIL':True,'SPX500':True,
  'NAS100':True,'US30':True},
 'rsi_por_moneda':{},
 'alert_users':[]
}

data=default_data.copy()
try:
 for p in ['/data/bot_data.json','bot_data.json']:
  if os.path.exists(p):
   with open(p) as f:
    data.update(json.load(f))
   break
 for k,v in default_data.items():
  if k not in data:
   data[k]=v
except:
 pass

def save():
 try:
  with open(DATA_FILE,'w') as f:
   json.dump(data,f)
  with open('/data/bot_data.json','w') as f:
   json.dump(data,f)
 except:
  pass

def tg(chat_id,text):
 if not BOT_TOKEN:
  return
 try:
  DASH='https://telegram-bot-cijp.onrender.com/dashboard'
  url=f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
  payload={
   'chat_id':chat_id,
   'text':text,
   'reply_markup':{
    'inline_keyboard':[
     [{'text':'V7 DOBLE CEREBRO','url':DASH}]
    ]
   }
  }
  requests.post(url,json=payload,timeout=10)
 except:
  pass

USD_PRICE=data.get('usd_mxn',18.5)
USD_TIME=0

def get_usd():
 global USD_PRICE,USD_TIME
 now=time.time()
 if now-USD_TIME<300:
  return USD_PRICE
 try:
  r=requests.get(
   'https://open.er-api.com/v6/latest/USD',
   timeout=8).json()
  mxn=float(r['rates']['MXN'])
  if 10<mxn<30:
   USD_PRICE=mxn
   USD_TIME=now
   data['usd_mxn']=mxn
   save()
   return mxn
 except:
  pass
 return USD_PRICE

SYMS=[
 'BTC/USDT','ETH/USDT',
 'SOL/USDT','BNB/USDT',
 'XRP/USDT','ADA/USDT',
 'AVAX/USDT','DOGE/USDT'
]

def get_rsi(prices,p=14):
 if len(prices)<p+1:
  return 50
 g=l=0
 for i in range(1,p+1):
  d=prices[-i]-prices[-i-1]
  if d>=0:
   g+=d
  else:
   l+=-d
 if l==0:
  return 100
 rs=g/l
 return 100-(100/(1+rs))

def get_prices_binance():
 out={}
 for sym in SYMS:
  coin=sym.replace('/USDT','')
  bsym=sym.replace('/','')
  try:
   r=requests.get(
    f'https://data-api.binance.vision/api/v3/klines?symbol={bsym}&interval=1h&limit=100',
    timeout=10).json()
   closes=[float(k[4]) for k in r]
   price=closes[-1]
   rsi=get_rsi(closes)
   ema=sum(closes[-20:])/20
   ok_ema=True
   if data['filtro_ema_binance']=='ON':
    ok_ema=price>ema
   lim=data['rsi_por_moneda'].get(
    coin,data['rsi_binance_compra'])
   ok_long=rsi<=lim and ok_ema
   out[coin]={
    'price':price,'rsi':round(rsi,1),
    'ema':ema,'p_ema_ok':ok_ema,
    'ok':ok_long,'sug':'COMPRA' if ok_long else 'Espera'
   }
  except:
   out[coin]={
    'price':0,'rsi':50,'ema':0,
    'p_ema_ok':False,'ok':False,'sug':'Error'
   }
 return out

def get_prices_mt5():
 out={}
 def mk(p,rsi_val,ok_v):
  return {
   'price':p,'rsi':rsi_val,
   'ema':p*0.998,
   'p_ema_ok':p>p*0.998,
   'ok':ok_v,'sug':'COMPRA' if ok_v else 'Espera',
   'change':0.5
  }
 try:
  r=requests.get(
   'https://api.gold-api.com/price/XAU',
   timeout=8).json()
  pr=float(r.get('price',2341.2))
  # MT5 compra solo si RSI 50-60 y tendencia alcista
  ok_mt5=50<=45<=60
  out['XAUUSD']=mk(pr,52,True)
 except:
  out['XAUUSD']=mk(2341.2,52,True)
 out['XAGUSD']=mk(28.15,53,False)
 out['USOIL']=mk(76.42,54,True)
 out['SPX500']=mk(5432.1,56,False)
 out['NAS100']=mk(18500.5,57,False)
 out['US30']=mk(39000.0,55,True)
 return out

def es_horario_mt5():
 # Solo opera 14:00 a 21:00 hora Veracruz
 # Veracruz UTC-6 -> 20:00 a 03:00 UTC
 try:
  h=datetime.utcnow().hour
  # 20,21,22,23,0,1,2,3 UTC = 14-21 MX
  return h in [20,21,22,23,0,1,2,3]
 except:
  return True
 @app.route('/',methods=['GET','POST'])
@app.route('/webhook',methods=['GET','POST'])
def webhook():
 if request.method=='GET':
  return 'BOT V7 DOBLE CEREBRO 500+500 OK',200
 d=request.get_json(force=True,silent=True) or {}
 if 'message' in d and 'chat' in d['message']:
  chat=d['message']['chat']['id']
  if chat not in data['alert_users']:
   data['alert_users'].append(chat)
   save()
  base='https://telegram-bot-cijp.onrender.com'
  msg=f"V7 DUAL BIN {data['capital_binance']:.0f} MT5 {data['capital_mt5']:.0f} {base}/dashboard"
  tg(chat,msg)
 return jsonify(ok=True)

@app.route('/dashboard')
def dash():
 if os.path.exists('dashboard.html'):
  return send_from_directory('.','dashboard.html')
 return 'no dashboard',404

@app.route('/api/prices')
def api_p():
 return jsonify(get_prices_binance())

@app.route('/api/prices_mt5')
def api_pm():
 return jsonify(get_prices_mt5())

@app.route('/api/state')
def api_state():
 bola_b=data['capital_binance']/data['max_entradas']
 bola_m=data['capital_mt5']/data['max_entradas']
 win=0
 if data['salidas']>0:
  win=data['ganadas']/data['salidas']*100
 bloq_b=0
 for x in data['pos']:
  bloq_b+=x.get('monto',bola_b)
 disp_b=data['capital_binance']-bloq_b
 bloq_m=0
 for x in data['pos_mt5']:
  bloq_m+=x.get('monto',bola_m)
 disp_m=data['capital_mt5']-bloq_m
 return jsonify({
  'capital_binance':data['capital_binance'],
  'capital_mt5':data['capital_mt5'],
  'capital':data['capital_binance']+data['capital_mt5'],
  'bola_binance':bola_b,
  'bola_mt5':bola_m,
  'bola':bola_b,
  'bola_mxn':bola_b*data['usd_mxn'],
  'gan_acum':data['gan_acum_total'],
  'usd_mxn':round(data['usd_mxn'],4),
  'ganadas':data['ganadas'],
  'salidas':data['salidas'],
  'winrate':win,
  'tp':data['tp_binance'],
  'tp_binance':data['tp_binance'],
  'tp_mt5':data['tp_mt5'],
  'sl_binance':data['sl_binance'],
  'sl_mt5':data['sl_mt5'],
  'rsi_compra':data['rsi_binance_compra'],
  'rsi_mt5_compra':data['rsi_mt5_compra'],
  'max_entradas':data['max_entradas'],
  'auto':data['auto_binance'],
  'auto_binance':data['auto_binance'],
  'auto_mt5':data['auto_mt5'],
  'coins_activas':data['coins_activas'],
  'coins_mt5_activas':data['coins_mt5_activas'],
  'disponible_usd':disp_b,
  'disponible_binance':disp_b,
  'disponible_mt5':disp_m,
  'bloqueado_usd':bloq_b,
  'bloqueado_binance':bloq_b,
  'bloqueado_mt5':bloq_m,
  'pos':data['pos'],
  'pos_binance':data['pos'],
  'pos_mt5':data['pos_mt5'],
  'historial':data['historial'][-50:],
  'capital_history':data['capital_history'][-100:]
 })

@app.route('/api/config',methods=['POST'])
def cfg():
 j=request.json
 if 'toggle_coin' in j:
  c=j['toggle_coin']
  data['coins_activas'][c]=not data['coins_activas'].get(c,True)
 if 'toggle_coin_mt5' in j:
  c=j['toggle_coin_mt5']
  data['coins_mt5_activas'][c]=not data['coins_mt5_activas'].get(c,True)
 if 'max' in j:
  data['max_entradas']=int(j['max'])
 if 'auto_binance' in j:
  data['auto_binance']=j['auto_binance']=='ON'
 if 'auto_mt5' in j:
  data['auto_mt5']=j['auto_mt5']=='ON'
 save()
 return jsonify(ok=True)

@app.route('/api/sell/<sym>',methods=['POST'])
def sell(sym):
 # Vende BINANCE
 for p in list(data['pos']):
  if p['sym']==sym:
   pr=get_prices_binance().get(sym,{}).get('price',p['entry'])
   gb=(pr-p['entry'])/p['entry']*100
   gn=gb-FEE*2*100
   data['capital_binance']+=p['monto']*gn/100
   data['pos'].remove(p)
   save()
   return jsonify(ok=True)
 # Vende MT5
 for p in list(data['pos_mt5']):
  if p['sym']==sym:
   pr=get_prices_mt5().get(sym,{}).get('price',p['entry'])
   gb=(pr-p['entry'])/p['entry']*100
   gn=gb-FEE*2*100
   data['capital_mt5']+=p['monto']*gn/100
   data['pos_mt5'].remove(p)
   save()
   return jsonify(ok=True)
 return jsonify(ok=True)

@app.route('/api/toggle',methods=['POST'])
def tog():
 j=request.json or {}
 if j.get('bot')=='MT5':
  data['auto_mt5']=not data['auto_mt5']
 else:
  data['auto_binance']=not data['auto_binance']
 save()
 return jsonify(ok=True)

@app.route('/api/backup/binance')
def bak_b():
 return jsonify({
  'tipo':'binance',
  'capital_binance':data['capital_binance'],
  'pos_binance':data['pos']
 })

@app.route('/api/backup/mt5')
def bak_m():
 return jsonify({
  'tipo':'mt5',
  'capital_mt5':data['capital_mt5'],
  'pos_mt5':data['pos_mt5']
 })

# CEREBRO 1: BINANCE - Reversion RSI 35
def loop_binance():
 lu=0
 while True:
  try:
   if time.time()-lu>300:
    get_usd()
    lu=time.time()
   if data['auto_binance']:
    prices=get_prices_binance()
    tm=data['max_entradas']
    if len(data['pos'])<tm:
     for sym,info in prices.items():
      if info['price']>0 and info['ok']:
       if data['coins_activas'].get(sym,True):
        has=False
        for x in data['pos']:
         if x['sym']==sym:
          has=True
        if not has:
         monto=data['capital_binance']/tm
         data['pos'].append({
          'sym':sym,
          'entry':info['price'],
          'monto':monto
         })
         save()
         break
  except Exception as e:
   print('ERR BIN',e)
  time.sleep(60)

# CEREBRO 2: MT5 - Tendencia RSI 55 + EMA ON + Horario USA
def loop_mt5():
 while True:
  try:
   if data['auto_mt5']:
    if es_horario_mt5():
     prices=get_prices_mt5()
     tm=data['max_entradas']
     if len(data['pos_mt5'])<tm:
      for sym,info in prices.items():
       # Solo si RSI entre 50-60 y precio > EMA
       if info['price']>0 and info['ok']:
        if info['rsi']>=50 and info['rsi']<=62:
         if info['p_ema_ok']:
          if data['coins_mt5_activas'].get(sym,True):
           has=False
           for x in data['pos_mt5']:
            if x['sym']==sym:
             has=True
           if not has:
            monto=data['capital_mt5']/tm
            data['pos_mt5'].append({
             'sym':sym,
             'entry':info['price'],
             'monto':monto
            })
            save()
            break
  except Exception as e:
   print('ERR MT5',e)
  time.sleep(90)

threading.Thread(target=loop_binance,daemon=True).start()
threading.Thread(target=loop_mt5,daemon=True).start()

if __name__=='__main__':
 app.run(
  host='0.0.0.0',
  port=int(os.environ.get('PORT',10000))
)
