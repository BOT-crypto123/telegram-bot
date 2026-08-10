import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv('TELEGRAM_TOKEN','')
B='https://api.telegram.org/bot'+T
F='/tmp/b.json'
def L():
 try: return json.load(open(F))
 except: return {'b':1000,'h':{},'hs':[],'auto':False}
def S(s): json.dump(s,open(F,'w'))
async def P(m):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
   return float(r.json()['data']['amount'])
 except: return 0
async def C(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f'https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=3600',headers={'User-Agent':'Mozilla'})
   d=r.json()
   return sorted(d)[-80:] if isinstance(d,list) else []
 except: return []
def ema(pr,n):
 if len(pr)<n: return []
 k=2/(n+1)
 s=sum(pr[:n])/n
 o=[s]
 for x in pr[n:]: o.append(x*k+o[-1]*(1-k))
 return o
def rsi(pr):
 if len(pr)<15: return 50
 g=0
 ll=0
 for i in range(1,15):
  d=pr[i]-pr[i-1]
  if d>0: g+=d
  else: ll-=d
 if ll==0: return 80
 if g==0: return 20
 return 100-100/(1+g/ll)
async def AN(sym):
 cl=await C(sym)
 if not cl: return None
 cs=[x[4] for x in cl]
 e9=ema(cs,9)
 e21=ema(cs,21)
 if not e9: return None
 rr=rsi(cs)
 p=cs[-1]
 a=e9[-1]
 b=e21[-1]
 tend='LATERAL'
 if p>a and a>b: tend='SUBE'
 if p<a and a<b: tend='BAJA'
 senal='NADA'
 if rr<30: senal='COMPRA FUERTE'
 elif rr>70: senal='VENTA FUERTE'
 elif p>a and rr<42: senal='COMPRA'
 elif p<a and rr>62: senal='VENTA'
 return {'p':p,'rsi':rr,'tend':tend,'senal':senal}
async def G(cid,txt):
 async with httpx.AsyncClient(timeout=10) as c:
  h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
  link='https://'+h+'/dashboard' if h else 'https://example.com'
  kb={'inline_keyboard':[[{'text':'DASHBOARD V928','url':link}]]}
  try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':
