import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter
print('V150 COPIAR TODO', flush=True)
TOKEN=os.environ.get('TELEGRAM_TOKEN')
URL='https://telegram-bot-cijp.onrender.com'
CONFIG={'BASE_USD':500.0,'BASE_MXN':9750.0,'ACUMULADO_MXN':310.0,'ACUMULADO_USD':15.90,'TP_PCT':0.30,'AUTO':True,'BOLAS_MAX':6,'RATE_MXN':19.50}
MONEDAS={'ADA':True,'AVAX':True,'BNB':True,'BTC':False,'DOGE':True,'ETH':True,'SOL':True,'XRP':True}
bolas=[];historial=[];PRECIOS={}
def get_rate_mxn():
 try:
  r=requests.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN',timeout=4)
  p=float(r.json()['price'])
  if 10 < p < 30:
   CONFIG['RATE_MXN']=p;CONFIG['BASE_MXN']=CONFIG['BASE_USD']*p;return p
 except: pass
 return CONFIG['RATE_MXN']
def get_precio(m):
 try:
  r=requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={m}USDT',timeout=4)
  p=float(r.json()['price']);PRECIOS[m]=p;return p
 except: return PRECIOS.get(m,0)
def get_total_mxn(): return CONFIG['BASE_MXN']+CONFIG['ACUMULADO_MXN']
def get_costo_mxn(): return get_total_mxn()/CONFIG['BOLAS_MAX']
def get_costo_usd(): return get_costo_mxn()/CONFIG['RATE_MXN']
def calc(e,s,c,r):
 if not e or s==0: return {}
 pct=((s-e)/e)*100;bruta=c*(pct/100);com=c*0.001+(c+bruta)*0.001;neta=bruta-com
 return {'pct_bruto':pct,'pct_neto':(neta/c)*100,'neta_usd':neta,'neta_mxn':neta*r}
def get_stats():
 rate=get_rate_mxn();CONFIG['ACUMULADO_MXN']=CONFIG['ACUMULADO_USD']*rate;CONFIG['BASE_MXN']=CONFIG['BASE_USD']*rate
 for b in bolas:
  p=get_precio(b['moneda'])
  if p>0: b['actual']=p
  d=calc(b['compra'],b['actual'],b['costo_usd'],rate);b.update(d)
 total_mxn=get_total_mxn();total_usd=total_mxn/rate;prog=(datetime.now().day/30)*100
 return total_usd,total_mxn,0,0,prog,rate,get_costo_usd(),get_costo_mxn()
def comprar_bola(m):
 if len(bolas)>=CONFIG['BOLAS_MAX']: return None
 for x in bolas:
  if x['moneda']==m: return None
 p=get_precio(m)
 if p==0: return None
 bolas.append({'id':int(time.time()*1000),'moneda':m,'compra':p,'costo_usd':get_costo_usd(),'costo_mxn':get_costo_mxn(),'actual':p})
 return True
def vender_bola(i):
 for b in bolas[:]:
  if str(b['id'])==str(i):
   CONFIG['ACUMULADO_USD']+=b.get('neta_usd',0);CONFIG['ACUMULADO_MXN']+=b.get('neta_mxn',0)
   historial.insert(0,{'fecha':datetime.now().strftime('%d/%m %H:%M'),'moneda':b['moneda'],'neta_mxn':round(b.get('neta_mxn',0),2),'pct_neto':round(b.get('pct_neto',0),3)})
   bolas.remove(b);return b
 return None
def resumen_total():
 if not historial: return {'total_entradas':0,'ganadas':0,'perdidas':0,'total_mxn':0,'total_usd':0,'mas_entradas':'-','mejor_moneda':'-','peor_moneda':'-'}
 total_mxn=sum(h['neta_mxn'] for h in historial);total_usd=sum(h.get('neta_usd',0) for h in historial);ganadas=len([h for h in historial if h['neta_mxn']>0]);perdidas=len([h for h in historial if h['neta_mxn']<=0])
 conteo=Counter(h['moneda'] for h in historial);mas=conteo.most_common(1)[0][0] if conteo else '-';por=defaultdict(float)
 for h in historial: por[h['moneda']]+=h['neta_mxn']
 mejor=max(por,key=por.get) if por else '-';peor=min(por,key=por.get) if por else '-'
 return {'total_entradas':len(historial),'ganadas':ganadas,'perdidas':perdidas,'total_mxn':total_mxn,'total_usd':total_usd,'mas_entradas':mas,'mejor_moneda':mejor,'peor_moneda':peor}
def tabla_por_moneda():
 stats=defaultdict(lambda: {'entradas':0,'ganadas':0,'perdidas':0,'total_mxn':0.0})
 for h in historial:
  m=h['moneda'];stats[m]['entradas']+=1
  if h['neta_mxn']>0: stats[m]['ganadas']+=1
  else: stats[m]['perdidas']+=1
  stats[m]['total_mxn']+=h['neta_mxn']
 for b in bolas: stats[b['moneda']]['entradas']+=1
 return stats
def loop_auto():
 while True:
  try:
   if CONFIG['AUTO']:
    get_stats()
    for b in bolas[:]:
     if b.get('pct_neto',0)>=CONFIG['TP_PCT']: vender_bola(b['id'])
    if len(bolas)<CONFIG['BOLAS_MAX']:
     disp=[m for m,on in MONEDAS.items() if on and all(x['moneda']!=m for x in bolas)]
     if disp: comprar_bola(random.choice(disp))
  except: print(traceback.format_exc(),flush=True)
  time.sleep(10)
threading.Thread(target=loop_auto,daemon=True).start()
app=Flask(__name__)
def b64d(s):
 chars='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
 tbl={c:i for i,c in enumerate(chars)}
 out=bytearray();i=0
 while i<len(s):
  c0=tbl.get(s[i],0);c1=tbl.get(s[i+1],0) if s[i+1]!='=' else 0;c2=tbl.get(s[i+2],0) if i+2<len(s) and s[i+2]!='=' else 0;c3=tbl.get(s[i+3],0) if i+3<len(s) and s[i+3]!='=' else 0
  n=(c0<<18)|(c1<<12)|(c2<<6)|c3
  out.append((n>>16)&255)
  if s[i+2]!='=': out.append((n>>8)&255)
  if s[i+3]!='=': out.append(n&255)
  i+=4
 return bytes(out)
B64=''
B64+='PCFET0NUWVBFIGh0bWw+PGh0bWw+PGhlYWQ+PG1ldGEgbmFtZT12aWV3cG9y'
B64+='dCBjb250ZW50PSd3aWR0aD1kZXZpY2Utd2lkdGgsIGluaXRpYWwtc2NhbGU9'
B64+='MSc+PHRpdGxlPk1BUVVJTkEgNTAwPC90aXRsZT48c3R5bGU+Ym9keXtiYWNr'
B64+='Z3JvdW5kOiMwNjExMjY7Y29sb3I6I2ZmZjtmb250
