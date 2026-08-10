import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
T=os.getenv('TELEGRAM_TOKEN','')
B='https://api.telegram.org/bot'+T
F='/tmp/b.json'
def L():
 try:
  return json.load(open(F))
 except:
  return {'b':1000,'h':{},'hs':[],'auto':False}
def S(s):
 json.dump(s,open(F,'w'))
async def P(m):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
   return float(r.json()['data']['amount'])
 except:
  return 0
async def candles(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get('https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=3600',headers={'User-Agent':'Mozilla'})
   d=r.json()
   if isinstance(d,list):
    d.sort()
    return d[-80:]
   return []
 except:
  return []
def ema(pr,n):
 if len(pr)<n:
  return []
 k=2/(n+1)
 s=sum(pr[:n])/n
 o=[s]
 for x in pr[n:]:
  o.append(x*k+o[-1]*(1-k))
 return o
def rsi(pr):
 if len(pr)<15:
  return 50
 g=0
 l=0
 for i in range(1,15):
  d=pr[i]-pr[i-1]
  if d>0:
   g+=d
  else:
   l-=d
 if l==0:
  return 80
 if g==0:
  return 20
 return 100-100/(1+g/l)
async def ANALIZA(sym):
 cl=await candles(sym)
 if not cl:
  return None
 cs=[x[4] for x in cl]
 e9=ema(cs,9)
 e21=ema(cs,21)
 if not e9 or not e21:
  return None
 rr=rsi(cs)
 p=cs[-1]
 a=e9[-1]
 b=e21[-1]
 tend='LATERAL'
 if p>a and a>b:
  tend='SUBE'
 elif p<a and a<b:
  tend='BAJA'
 senal='NADA'
 if rr<30:
  senal='COMPRA FUERTE'
 elif rr>70:
  senal='VENTA FUERTE'
 elif p>a and rr<42:
  senal='COMPRA'
 elif p<a and rr>62:
  senal='VENTA'
 drop=0
 if len(cs)>=10:
  drop=(cs[-1]/cs[-10]-1)*100
 return {'p':p,'rsi':rr,'tend':tend,'senal':senal,'drop':drop}
async def G(cid,txt,sym):
 async with httpx.AsyncClient(timeout=10) as c:
  host=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
  link='https://'+host+'/dashboard' if host else 'https://example.com'
  kb={'inline_keyboard':[[{'text':'DASHBOARD','url':link}],[{'text':'BUY $100','callback_data':'BUY_'+sym},{'text':'SELL','callback_data':'SELL_'+sym}],[{'text':'AUTO ON','callback_data':'AUTO_ON'},{'text':'AUTO OFF','callback_data':'AUTO_OFF'}]]}
  try:
   await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb})
  except:
   pass

@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L()
 prices={}
 for k in ['BTC','ETH','SOL','XRP']:
  an=
