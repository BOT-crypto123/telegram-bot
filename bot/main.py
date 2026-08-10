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
   return float((await c.get("https://api.coinbase.com/v2/prices/"+m+"-USD/spot").json())["data"]["amount"])
 except:return 65000
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  d="https://"+os.getenv("RENDER_EXTERNAL_HOSTNAME","")+"/dashboard"
  k={"inline_keyboard":[[{"text":"📊 DASHBOARD","url":d}],[{"text":"BUY $100","callback_data":"BUY_"+m},{"text":"SELL","callback_data":"SELL_"+m}]]}
  await c.post(B+"/sendMessage",json={"chat_id":i,"text":t,"reply_markup":k})
async def CHECK(s,cid):
 if not s.get("auto"):return
 for mon,hold in list(s["h"].items()):
  pr=await P(mon);ent=hold["e"];chg=(pr/ent-1)*100
  if chg<=-2 or chg>=2:
   val=hold["a"]*pr*0.998
   gan=chg
   s["b"]+=val
   s["hs"].append({"f
