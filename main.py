import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter
print('V152 FINAL TODO', flush=True)
TOKEN=os.environ.get('TELEGRAM_TOKEN')
URL='https://telegram-bot-cijp.onrender.com'
CONFIG={'BASE_USD':500.0,'BASE_MXN':9750.0,'ACUMULADO_MXN':310.0,'ACUMULADO_USD':15.90,'TP_PCT':0.30,'AUTO':True,'BOLAS_MAX':6,'RATE_MXN':19.50}
MONEDAS={'ADA':True,'AVAX':True,'BNB':True,'BTC':False,'DOGE':True,'ETH':True,'SOL':True,'XRP':True}
bolas=[];historial=[];PRECIOS={}
def get_rate_mxn():
 try:
  r=requests.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN',timeout=4)
  p=float(r.json()['price'])
  if 10<p<30:
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
 if not historial: return {'total_entradas':0,'ganadas':0,'perdidas':0,'total_mxn':0,'mas_entradas':'-','mejor_moneda':'-','peor_moneda':'-'}
 total_mxn=sum(h['neta_mxn'] for h in historial);ganadas=len([h for h in historial if h['neta_mxn']>0]);perdidas=len([h for h in historial if h['neta_mxn']<=0])
 conteo=Counter(h['moneda'] for h in historial);mas=conteo.most_common(1)[0][0] if conteo else '-';por=defaultdict(float)
 for h in historial: por[h['moneda']]+=h['neta_mxn']
 mejor=max(por,key=por.get) if por else '-';peor=min(por,key=por.get) if por else '-'
 return {'total_entradas':len(historial),'ganadas':ganadas,'perdidas':perdidas,'total_mxn':total_mxn,'mas_entradas':mas,'mejor_moneda':mejor,'peor_moneda':peor}
def tabla_por_moneda():
 stats=defaultdict(lambda: {'entradas':0,'ganadas':0,'total_mxn':0.0})
 for h in historial:
  m=h['moneda'];stats[m]['entradas']+=1
  if h['neta_mxn']>0: stats[m]['ganadas']+=1
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
 c='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
 t={ch:i for i,ch in enumerate(c)};o=bytearray();i=0
 while i<len(s):
  a=t.get(s[i],0);b=t.get(s[i+1],0) if s[i+1]!='=' else 0;d=t.get(s[i+2],0) if i+2<len(s) and s[i+2]!='=' else 0;e=t.get(s[i+3],0) if i+3<len(s) and s[i+3]!='=' else 0
  n=(a<<18)|(b<<12)|(d<<6)|e;o.append((n>>16)&255)
  if s[i+2]!='=': o.append((n>>8)&255)
  if s[i+3]!='=': o.append(n&255)
  i+=4
 return bytes(o)
B=''
B+='PCFET0NUWVBFIGh0bWw+'
B+='PGh0bWw+PGhlYWQ+PG1l'
B+='dGEgbmFtZT12aWV3cG9y'
B+='dCBjb250ZW50PSd3aWR0'
B+='aD1kZXZpY2Utd2lkdGgs'
B+='IGluaXRpYWwtc2NhbGU9'
B+='MSc+PHRpdGxlPk08L3Rp'
B+='dGxlPjxzdHlsZT5ib2R5'
B+='e2JhY2tncm91bmQ6IzA2'
B+='MTEyNjtjb2xvcjojZmZm'
B+='O2ZvbnQtZmFtaWx5OkFy'
B+='aWFsO3BhZGRpbmc6MTBw'
B+='eH0udGl0dWxve2ZvbnQt'
B+='c2l6ZToyNnB4O3RleHQt'
B+='YWxpZ246Y2VudGVyO2Nv'
B+='bG9yOiNGRkQ3MDA7Zm9u'
B+='dC13ZWlnaHQ6OTAwfS5j'
B+='YXJke2JhY2tncm91bmQ6'
B+='IzBjMWUzYTtib3JkZXIt'
B+='cmFkaXVzOjEycHg7cGFk'
B+='ZGluZzoxMnB4O21hcmdp'
B+='bjoxMHB4IDB9LmJ0bntw'
B+='YWRkaW5nOjhweCAxMnB4'
B+='O2JvcmRlci1yYWRpdXM6'
B+='OHB4O2JvcmRlcjpub25l'
B+='O21hcmdpbjozcHg7Zm9u'
B+='dC13ZWlnaHQ6Ym9sZH0u'
B+='b257YmFja2dyb3VuZDoj'
B+='MGVhNWU5O2NvbG9yOiNm'
B+='ZmZ9Lm9mZntiYWNrZ3Jv'
B+='dW5kOiMwZjI4NGE7Y29s'
B+='b3I6IzVhN2FhNX0udHB7'
B+='YmFja2dyb3VuZDojMDBl'
B+='NWZmO2NvbG9yOiMwMDB9'
B+='LmJ1eXtiYWNrZ3JvdW5k'
B+='OiMwMGZmODg7Y29sb3I6'
B+='IzAwMH0uc2VsbHtiYWNr'
B+='Z3JvdW5kOiNmZjNiMzA7'
B+='Y29sb3I6I2ZmZn0uY29t'
B+='cHtiYWNrZ3JvdW5kOiMw'
B+='MGZmODg7Y29sb3I6IzAw'
B+='MDtwYWRkaW5nOjEwcHg7'
B+='Ym9yZGVyLXJhZGl1czox'
B+='MHB4O2ZvbnQtd2VpZ2h0'
B+='OjkwMDt0ZXh0LWFsaWdu'
B+='OmNlbnRlcn0ucmVzdW1l'
B+='bntiYWNrZ3JvdW5kOiMx'
B+='MDJhNGE7Ym9yZGVyOjJw'
B+='eCBzb2xpZCAjRkZENzAw'
B+='O2JvcmRlci1yYWRpdXM6'
B+='MTJweDtwYWRkaW5nOjEy'
B+='cHh9LmNpcmNsZS13cmFw'
B+='e3Bvc2l0aW9uOnJlbGF0'
B+='aXZlO3dpZHRoOjI3MHB4'
B+='O2hlaWdodDoyNzBweDtt'
B+='YXJnaW46MTVweCBhdXRv'
B+='fS5iZ3tmaWxsOm5vbmU7'
B+='c3Ryb2tlOiMwZjI4NGE7'
B+='c3Ryb2tlLXdpZHRoOjE0'
B+='fS5wcm9ne2ZpbGw6bm9u'
B+='ZTtzdHJva2U6I0ZGRDcw'
B+='MDtzdHJva2Utd2lkdGg6'
B+='MTQ7c3Ryb2tlLWxpbmVj'
B+='YXA6cm91bmQ7dHJhbnNm'
B+='b3JtOnJvdGF0ZSgtOTBk'
B+='ZWcpO3RyYW5zZm9ybS1v'
B+='cmlnaW46NTAlIDUwJX0u'
B+='Y2VudGVye3Bvc2l0aW9u'
B+='OmFic29sdXRlO3RvcDo1'
B+='MCU7bGVmdDo1MCU7dHJh'
B+='bnNmb3JtOnRyYW5zbGF0'
B+='ZSgtNTAlLC01MCUpO3Rl'
B+='eHQtYWxpZ246Y2VudGVy'
B+='fS5teG4tYmlne2ZvbnQt'
B+='c2l6ZTo0MHB4O2NvbG9y'
B+='OiMwMGZmODg7Zm9udC13'
B+='ZWlnaHQ6OTAwfTwvc3R5'
B+='bGU+PC9oZWFkPjxib2R5'
B+='Pgo8ZGl2IGNsYXNzPXRp'
B+='dHVsbz5NQVFVSU5BIERF'
B+='IEhBQ0VSIERJTkVSTzwv'
B+='ZGl2PjxkaXYgc3R5bGU9'
B+='dGV4dC1hbGlnbjpjZW50'
B+='ZXI7Y29sb3I6IzhhYT5C'
B+='QVNFIDUwMCBVU0QgLSBC'
B+='T0xBIE5JRVZFPC9kaXY+'
B+='CjxkaXYgY2xhc3M9Y2ly'
B+='Y2xlLXdyYXA+PHN2ZyB3'
B+='aWR0aD0yNzAgaGVpZ2h0'
B+='PTI3MD48Y2lyY2xlIGNs'
B+='YXNzPWJnIGN4PTEzNSBj'
B+='eT0xMzUgcj0xMTA+PC9j'
B+='aXJjbGU+PGNpcmNsZSBp'
B+='ZD1wYyBjbGFzcz1wcm9n'
B+='IGN4PTEzNSBjeT0xMzUg'
B+='cj0xMTAgc3Ryb2tlLWRh'
B+='c2hhcnJheT02OTEgc3Ry'
B+='b2tlLWRhc2hvZmZzZXQ9'
B+='NjkxPjwvY2lyY2xlPjwv'
B+='c3ZnPjxkaXYgY2xhc3M9'
B+='Y2VudGVyPjxkaXYgaWQ9'
B+='YmFzZU14biBjbGFzcz1t'
B+='eG4tYmlnPiQwPC9kaXY+'
B+='PGRpdiBpZD1iYXNlVXNk'
B+='IHN0eWxlPWNvbG9yOiM1'
B+='YTdhYTU+JDA8L2Rpdj48'
B+='ZGl2IGlkPXJhdGVUeHQg'
B+='c3R5bGU9Y29sb3I6I0ZG'
B+='RDcwMDtmb250LXNpemU6'
B+='OXB4PjwvZGl2PjxkaXYg'
B+='aWQ9ZGlhVHh0IHN0eWxl'
B+='PWNvbG9yOiM1YTdhYTU+'
B+='PC9kaXY+PC9kaXY+PC9k'
B+='aXY+CjxkaXYgY2xhc3M9'
B+='Y2FyZCBzdHlsZT1ib3Jk'
B+='ZXI6MnB4IHNvbGlkICMw'
B+='MGZmODg+PGRpdiBpZD1h'
B+='Y3VtTXhuIHN0eWxlPWZv'
B+='bnQtc2l6ZTo0MHB4O2Nv'
B+='bG9yOiMwMGZmODg7dGV4'
B+='dC1hbGlnbjpjZW50ZXI+'
B+='JDA8L2Rpdj48ZGl2IGlk'
B+='PWFjdW1Vc2Qgc3R5bGU9'
B+='dGV4dC1hbGlnbjpjZW50'
B+='ZXI7Y29sb3I6IzVhN2Fh'
B+='NT4kMDwvZGl2PjxkaXYg'
B+='aWQ9dG90YWxMaW5lIHN0'
B+='eWxlPXRleHQtYWxpZ246'
B+='Y2VudGVyO2NvbG9yOiM1'
B+='YTdhYTU7Zm9udC1zaXpl'
B+='OjEwcHg+PC9kaXY+PGRp'
B+='diBpZD1jb3N0b0xpbmUg'
B+='Y2xhc3M9Y29tcD48L2Rp'
B+='dj48L2Rpdj4KPGRpdiBj'
B+='bGFzcz1jYXJkPjxiIHN0'
B+='eWxlPWNvbG9yOiMwMGZm'
B+='ODg+VFAgMC4zJSBCQVNF'
B+='PC9iPiA8YnV0dG9uIGN
