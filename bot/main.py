import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
C=os.getenv("RENDER_EXTERNAL_HOSTNAME","")
D=f"https://{C}/dashboard"

def L():
 try:
  return json.load(open(F))
 except:
  return{"bal":1000,"holds":{},"hist":[]}
def S(s):
 json.dump(s,open(F,"w"))

async def P(m):
 try:
  async with httpx.AsyncClient(timeout=5) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{m}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:
  return 65000

async def G(cid,t,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=5) as c:
  u=f"https://www.tradingview.com/symbols/{mon}USDT/"
  if buy:
   k={"inline_keyboard":[[{"text":"GRAF","url":u},{"text":"DASH","url":D}],[{"text":"BUY","callback_data":"BUY_"+mon},{"text":"SELL","callback_data":"SELL_"+mon}]]}
  else:
   k={"inline_keyboard":[[{"text":"GRAF","url":u},{"text":"DASH","url":D}
