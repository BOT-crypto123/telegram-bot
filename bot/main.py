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
  async with httpx.Async
