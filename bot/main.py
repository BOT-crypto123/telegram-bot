import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B="https://api.telegram.org/bot"+T
F="/tmp/b.json"
def L():
 try:return json.load(open(F))
 except:return{"b":1000,"h":{},"hs":[],"auto":False}
def S(s):json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   j=await c.get("https://api.coinbase.com/v2/prices/"+m+"-USD/spot").then
   d=(await c.get("https://api.coinbase.com/v2/prices/"+m+"-USD/spot").json())["data"]["amount"]
   return float(d)
 except:return 65000
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  d="https://"+os.getenv("RENDER_EXTERNAL_HOSTNAME","")+"/dashboard"
  k={"inline_keyboard":[[{"text":"DASHBOARD","url":d}],[{"text":"BUY","callback_data":"BUY_"+m},{"text":"SELL","callback_data":"SELL
