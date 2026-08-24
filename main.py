import os,json,time,threading,requests
from flask import Flask,request,jsonify,send_from_directory
from pathlib import Path

app=Flask(__name__)
BOT_TOKEN=os.getenv('BOT_TOKEN','')
DATA_FILE='bot_data.json'
FEE=0.001

default_data={
 'capital_actual':500.0,
 'capital_inicial':500.0,
 'capital_binance':500.0,
 'capital_mt5':500.0,
 'usd_mxn':18.5,
 'gan_acum_total':0.0,
 'gan_mes':0.0,
 'pct_mes':0.0,
 'ganadas':0,
 'salidas':0,
 'tp':0.3,
 'sl_pct':-1.5,
 'rsi_compra':35,
 'rsi_venta':70,
 'filtro_ema':'OFF',
 'max_entradas':8,
 'auto':True,
 'auto_tune':True,
 'modo':'AMBOS',
 'pos':[],
 'pos_short':[],
 'pos_mt5':[],
 'historial':[],
 'historial_binance':[],
 'historial_mt5':[],
 'capital_history':[],
 'coins_activas':{'BTC':True,'ETH':True,'SOL':True,'BNB':True,'XRP':True,'ADA':True,'AVAX':True,'DOGE':True},
 'coins_mt5_activas':{'XAUUSD':True,'XAGUSD':True,'USOIL':True,'SPX500':True},
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
  payload={'chat_id':chat_id,'text':text,'reply_markup':{'inline_keyboard':[[{'text':'VER DASHBOARD V5','url':DASH}]]}}
  requests.post(url,json=payload,timeout=10)
 except:
  pass

def keep_alive():
 while True:
  try:
   u=os.getenv('RENDER_EXTERNAL_URL') or 'https://telegram-bot-cijp.onrender.com/'
   requests.get(u,timeout=10)
  except:
   pass
  time.sleep(600)
threading.Thread(target=keep_alive,daemon=True).start()

USD_PRICE=data.get('usd_mxn',18.5)
USD_TIME=0

def get_usd():
 global USD_PRICE,USD_TIME
 now=time.time()
 if now-USD_TIME<300:
  return USD_PRICE
 try:
  r=requests.get('https://open.er-api.com/v6/latest/USD',timeout=8).json()
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

SYMS=['BTC/USDT','ETH/USDT','SOL/USDT','BNB/USDT','XRP/USDT','ADA/USDT','AVAX/USDT','DOGE/USDT']

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

def get_prices():
 out={}
 for sym in SYMS:
  coin=sym.replace('/USDT','')
  bsym=sym.replace('/','')
  try:
   r=requests.get(f'https://data-api.binance.vision/api/v3/klines?symbol={bsym}&interval=1h&limit=100',timeout=10).json()
   closes=[float(k[4]) for k in r]
   price=closes[-1]
   rsi=get_rsi(closes)
   ema=sum(closes[-20:])/20
   filt=data['filtro_ema']
   ok_ema=price>ema if filt=='ON' else True
   lim=data['rsi_por_moneda'].get(coin,data['rsi_compra'])
   ok_long=rsi<=lim and ok_ema
   ok_short=rsi>=data['rsi_venta'] and (price<ema)
   sug='COMPRA LONG' if ok_long else 'VENTA SHORT' if ok_short else 'Espera'
   out[coin]={'price':price,'rsi':round(rsi,1),'limite':lim,'p_ema_ok':ok_ema,'ok':ok_long,'ok_short':ok_short,'sug':sug,'motivo':f'RSI {rsi:.1f}','ema':ema}
  except Exception as e:
   out[coin]={'price':0,'rsi':50,'limite':35,'p_ema_ok':False,'ok':False,'ok_short':False,'sug':'Error','motivo':str(e)[:60],'ema':0}
 return out

def get_mt5():
 out={}
 try:
  r=requests.get('https://api.gold-api.com/price/XAU',timeout=8).json()
  out['XAUUSD']={'price':float(r.get('price',2341.2)),'rsi':45,'ok':True,'sug':'COMPRA LONG','change':0.64}
 except:
  out['XAUUSD']={'price':2341.2,'rsi':45,'ok':True,'sug':'COMPRA LONG','change':0.64}
 try:
  r=requests.get('https://api.gold-api.com/price/XAG',timeout=8).json()
  out['XAGUSD']={'price':float(r.get('price',28.15)),'rsi':52,'ok':False,'sug':'Espera','change':-0.31}
 except:
  out['XAGUSD']={'price':28.15,'rsi':52,'ok':False,'sug':'Espera','change':-0.31}
 out['USOIL']={'price':76.42,'rsi':48,'ok':True,'sug':'COMPRA LONG','change':1.08}
 out['SPX500']={'price':5432.1,'rsi':55,'ok':False,'sug':'Espera','change':0.42}
 return out
 def tune(prices):
 if not data.get('auto_tune',True):
  return
 debajo=sum(1 for v in prices.values() if v['price']>0 and v['price']<v['ema'])
 if debajo>=6:
  data['filtro_ema']='OFF'
  data['sl_pct']=-2.5
  data['tp']=0.3
  data['rsi_venta']=70
  data['rsi_compra']=40
 elif debajo<=2:
  data['filtro_ema']='ON'
  data['sl_pct']=-1.0
  data['tp']=0.5
  data['rsi_venta']=75
  data['rsi_compra']=30
 else:
  data['filtro_ema']='OFF'
  data['sl_pct']=-1.5
  data['tp']=0.3
  data['rsi_venta']=70
  data['rsi_compra']=35
 save()

@app.route('/',methods=['GET','POST'])
@app.route('/webhook',methods=['GET','POST'])
def webhook():
 if request.method=='GET':
  return 'BOT LIVE V5 - /dashboard OK',200
 d=request.get_json(force=True,silent=True) or {}
 if 'message' in d and 'chat' in d['message']:
  chat=d['message']['chat']['id']
  if chat not in data['alert_users']:
   data['alert_users'].append(chat)
   save()
  base='https://telegram-bot-cijp.onrender.com'
  msg=f"DUAL V5 OK Bin {data['capital_binance']:.0f} MT5 {data['capital_mt5']:.0f} {base}/dashboard"
  tg(chat,msg)
 return jsonify(ok=True)

@app.route('/dashboard')
def dash():
 if os.path.exists('dashboard.html'):
  return send_from_directory('.','dashboard.html')
 return 'no dashboard',404

@app.route('/api/prices')
def api_p():
 return jsonify(get_prices())

@app.route('/api/prices_mt5')
def api_pm():
 return jsonify(get_mt5())

@app.route('/api/state')
def api_state():
 bola=data['capital_binance']/data['max_entradas']
 bola_m=data['capital_mt5']/data['max_entradas']
 win=(data['ganadas']/data['salidas']*100) if data['salidas']>0 else 0
 prices=get_prices()
 for p in data['pos']:
  pr=prices.get(p['sym'],{}).get('price',p['entry'])
  p['ahora']=pr
  gb=(pr-p['entry'])/p['entry']*100
  gn=gb-(FEE*2*100)
  p['gan_neta_pct']=gn
  p['tipo']='LONG'
 for p in data.get('pos_short',[]):
  pr=prices.get(p['sym'],{}).get('price',p['entry'])
  p['ahora']=pr
  gb=(p['entry']-pr)/p['entry']*100
  gn=gb-(FEE*2*100)
  p['gan_neta_pct']=gn
  p['tipo']='SHORT'
 bloq=sum([x.get('monto',bola) for x in data['pos']])+sum([x.get('monto',bola) for x in data.get('pos_short',[])])
 disp=data['capital_binance']-bloq
 return jsonify({
  'capital_binance':data['capital_binance'],
  'capital_mt5':data['capital_mt5'],
  'capital':data['capital_binance']+data['capital_mt5'],
  'bola_binance':bola,
  'bola_mt5':bola_m,
  'gan_acum':data['gan_acum_total'],
  'usd_mxn':round(data['usd_mxn'],4),
  'pct_mes':data['pct_mes'],
  'gan_mes':data['gan_mes'],
  'ganadas':data['ganadas'],
  'salidas':data['salidas'],
  'winrate':win,
  'tp':data['tp'],
  'fee_total':FEE*2*100,
  'max_entradas':data['max_entradas'],
  'rsi_compra':data['rsi_compra'],
  'sl_pct':data['sl_pct'],
  'rsi_venta':data['rsi_venta'],
  'filtro_ema':data['filtro_ema'],
  'auto':data['auto'],
  'auto_tune':data.get('auto_tune',True),
  'modo':data.get('modo','AMBOS'),
  'coins_activas':data['coins_activas'],
  'coins_mt5_activas':data['coins_mt5_activas'],
  'bola':bola,
  'bola_mxn':bola*data['usd_mxn'],
  'disponible_usd':disp,
  'bloqueado_usd':bloq,
  'pos':data['pos']+data.get('pos_short',[]),
  'pos_long':data['pos'],
  'pos_short':data.get('pos_short',[]),
  'pos_binance':data['pos'],
  'pos_mt5':data.get('pos_mt5',[]),
  'historial':data['historial'][-50:],
  'capital_history':data['capital_history'][-100:]
 })

@app.route('/api/config',methods=['POST'])
def cfg():
 j=request.json
 if 'toggle_coin' in j:
  data['coins_activas'][j['toggle_coin']]=not data['coins_activas'].get(j['toggle_coin'],True)
 if 'max' in j:
  data['max_entradas']=int(j['max'])
 if 'modo' in j:
  data['modo']=j['modo']
 if 'auto_tune' in j:
  data['auto_tune']=(j['auto_tune']=='ON' or j['auto_tune']==True)
 if not data.get('auto_tune',True):
  if 'rsi_compra' in j:
   data['rsi_compra']=float(j['rsi_compra'])
  if 'tp' in j:
   data['tp']=float(j['tp'])
  if 'sl_pct' in j:
   data['sl_pct']=float(j['sl_pct'])
  if 'rsi_venta' in j:
   data['rsi_venta']=float(j['rsi_venta'])
  if 'filtro_ema' in j:
   data['filtro_ema']=j['filtro_ema']
 if 'rsi_coin' in j:
  data['rsi_por_moneda'][j['rsi_coin']['sym']]=float(j['rsi_coin']['val'])
 if 'rsi_coin_reset' in j:
  data['rsi_por_moneda'].pop(j['rsi_coin_reset'],None)
 save()
 return jsonify(ok=True)

@app.route('/api/sell/<sym>',methods=['POST'])
def sell(sym):
 prices=get_prices()
 for p in list(data['pos']):
  if p['sym']==sym:
   pr=prices.get(sym,{}).get('price',p['entry'])
   gb=(pr-p['entry'])/p['entry']*100
   gn=gb-FEE*2*100
   gm=p['monto']*gn/100*data['usd_mxn']
   data['capital_binance']+=p['monto']*gn/100
   data['gan_acum_total']+=p['monto']*gn/100
   data['salidas']+=1
   if gn>0:
    data['ganadas']+=1
   h={'fecha':time.strftime('%m-%d %H:%M'),'sym':sym+' LONG','monto':p['monto'],'entry':p['entry'],'exit':pr,'gan_neta_pct':gn,'gan_neta_mxn':gm,'capital_despues':data['capital_binance']}
   data['historial'].append(h)
   data['historial_binance'].append(h)
   data['capital_history'].append({'t':int(time.time()*1000),'cap':data['capital_binance']})
   data['pos'].remove(p)
   save()
   return jsonify(ok=True)
 return jsonify(ok=True)

@app.route('/api/toggle',methods=['POST'])
def tog():
 data['auto']=not data['auto']
 save()
 return jsonify(ok=True)

@app.route('/api/backup/binance')
def bak_b():
 return jsonify({'tipo':'binance','capital_binance':data['capital_binance'],'pos_binance':data['pos'],'historial_binance':data.get('historial_binance',[]),'coins_activas':data['coins_activas']})

@app.route('/api/backup/mt5')
def bak_m():
 return jsonify({'tipo':'mt5','capital_mt5':data['capital_mt5'],'pos_mt5':data.get('pos_mt5',[]),'historial_mt5':data.get('historial_mt5',[])})

@app.route('/api/restore',methods=['POST'])
def rest():
 global data
 try:
  nuevo=request.get_json(force=True)
  tipo=nuevo.get('tipo','all')
  if tipo=='binance':
   if 'capital_binance' in nuevo:
    data['capital_binance']=nuevo['capital_binance']
   if 'pos_binance' in nuevo:
    data['pos']=nuevo['pos_binance']
   save()
   return jsonify(ok=True)
  if tipo=='mt5':
   if 'capital_mt5' in nuevo:
    data['capital_mt5']=nuevo['capital_mt5']
   if 'pos_mt5' in nuevo:
    data['pos_mt5']=nuevo['pos_mt5']
   save()
   return jsonify(ok=True)
  data=nuevo
  for k,v in default_data.items():
   if k not in data:
    data[k]=v
  save()
  return jsonify(ok=True)
 except Exception as e:
  return jsonify(ok=False,error=str(e))

def loop():
 lt=0
 lu=0
 while True:
  try:
   if time.time()-lu>300:
    try:
     get_usd()
    except:
     pass
    lu=time.time()
   if data['auto']:
    prices=get_prices()
    if time.time()-lt>900:
     try:
      tune(prices)
     except:
      pass
     lt=time.time()
    tm=data['max_entradas']
    if len(data['pos']) < (tm+1)//2:
     for sym,info in prices.items():
      if info['price']>0 and info['ok'] and data['coins_activas'].get(sym,True) and not any(x['sym']==sym for x in data['pos']):
       monto=data['capital_binance']/tm
       data['pos'].append({'sym':sym,'entry':info['price'],'monto':monto})
       save()
       break
  except Exception as e:
   print('ERR',e)
  time.sleep(60)

threading.Thread(target=loop,daemon=True).start()
if __name__=='__main__':
 app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
