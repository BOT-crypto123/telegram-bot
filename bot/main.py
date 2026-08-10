import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
T=os.getenv('TELEGRAM_TOKEN','')
B='https://api.telegram.org/bot'+T
F='/tmp/b.json'
def L():
 try:return json.load(open(F))
 except:return{'b':1000,'h':{},'hs':[],'auto':False}
def S(s):json.dump(s,open(F,'w'))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
   return float(r.json()['data']['amount'])
 except:return 0
async def candles(sym):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get('https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=3600',headers={'User-Agent':'M'})
   d=r.json()
   return sorted(d)[-60:] if isinstance(d,list) else []
 except:return []
def ema(pr,n):
 if len(pr)<n:return []
 k=2/(n+1)
 m=sum(pr[:n])/n
 o=[m]
 for x in pr[n:]:
  o.append(x*k+o[-1]*(1-k))
 return o
def rsi(pr):
 if len(pr)<15:return 50
 g=l=0
 for i in range(1,15):
  d=pr[i]-pr[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
async def ANALIZA(sym):
 cl=await candles(sym)
 if not cl:return None
 cs=[c[4] for c in cl]
 e9=ema(cs,9)
 e21=ema(cs,21
