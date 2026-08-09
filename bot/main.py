import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
TOKEN=os.getenv("TELEGRAM_TOKEN","")
BASE=f"https://api.telegram.org/bot{TOKEN}"
FILE="/tmp/b.json"
CAP=os.getenv("RENDER_EXTERNAL_HOSTNAME","")
DASH=f"https://{CAP}/dashboard"

def load():
 try:
  return json.load(open(FILE))
 except:
  return {"bal":1000.0,"holds":{},"hist":[]}

def save(s):
 json.dump(s,open(FILE,"w"))

async def price(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",headers={"User-Agent":"M"})
   return float(r.json()["data"]["amount"])
 except:
  return 65000.0

async def candles():
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600",headers={"User-Agent":"M"})
   d=sorted(r.json())[-40:]
   return [x[4] for x in d]
 except:
  return [65000,65100,65200,65153]

async def send(cid,txt,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=10) as c:
  u=f"https://www.tradingview.com/symbols/{mon}USDT/"
  if buy:
   kb={"inline_keyboard":[[{"text":"GRAFICA","url":u},{"text":"DASHBOARD","url":DASH}],[{"text":"COMPRAR","callback_data":"BUY_"+mon},{"text":"VENDER","callback_data":"SELL_"+mon}]]}
  else:
   kb={"inline_keyboard":[[{"text":"GRAFICA","url":u},{"text":"DASHBOARD","url":DASH}]]}
  km={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":"Menu","reply_markup":km})

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load()
 bal=s['bal']
 pr=await candles()
 rows=""
 tot=bal
 for k,v in s['holds'].items():
  p=await price(k)
  amt=v['a']
  ent=v['e']
  val=amt*p
  tot+=val
  gn=(p/ent-1)*100 if ent>0 else 0
  col="#00e676" if gn>=0 else "#ff5252"
  rows+=f"<tr><td>{k}</td><td>{amt:.5f}</td
