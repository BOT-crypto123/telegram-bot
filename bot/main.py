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
  return {"bal":1000.0,"holds":{},"hist":[],"auto":False}
def save(s):
 json.dump(s,open(FILE,"w"))
async def price(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",headers={"User-Agent":"M"})
   return float(r.json()["data"]["amount"])
 except:
  return 65153.0
async def candles():
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600",headers={"User-Agent":"M"})
   d=sorted(r.json())[-40:]
   return [x[4] for x in d]
 except:
  return [65000,65100,65200,65153]
async def tsend(cid
