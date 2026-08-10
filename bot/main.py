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
async def C(s):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f'https://api.exchange.coinbase.com/products/{s}-USD/candles?granularity=3600',headers={'User-Agent':'Mozilla'})
   d=r.json()
   return sorted(d)[-80:] if isinstance(d,list) else []
 except: return []
def rsi(p):
 if len(p)<15: return 50
 g=ll=0
 for i in range(1,15):
  d=p[i]-p[i-1]
  g+=d if d>0
