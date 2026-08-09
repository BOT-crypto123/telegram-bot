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
  return [65000,65200,65100,65300,65250,65400,65500,65450,65600,65153]

async def send(cid,txt,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=10) as c:
  u="https://www.tradingview.com/symbols/"+mon+"USDT/"
  if buy:
   kb={"inline_keyboard":[[{"text":"📈 GRAFICA","url":u},{"text":"💻 DASHBOARD","url":DASH}],[{"text":"✅ COMPRAR","callback_data":"BUY_"+mon},{"text":"❌ VENDER","callback_data":"SELL_"+mon}]]}
  else:
   kb={"inline_keyboard":[[{"text":"📈 GRAFICA","url":u},{"text":"💻 DASHBOARD","url":DASH}]]}
  km={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":"Menu","reply_markup":km})

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load()
 bal=s.get('bal',1000.0)
 holds=s.get('holds',{})
 hist=s.get('hist',[])
 pr=await candles()
 rows=""
 tot=bal
 for k,v in holds.items():
  p=await price(k)
  amt=v.get('a',0)
  ent=v.get('e',0)
  val=amt*p
  tot=tot+val
  if ent>0:
   gn=(p/ent-1)*100
  else:
   gn=0
  if gn>=0:
   col="#00d395"
   sign="+"
  else:
   col="#ff4d4d"
   sign=""
  rows=rows+"<tr><td><b>"+k+"</b></td><td>"+str(round(amt,5))+"</td><td>$"+str(round(ent,2))+"</td><td>$"+str(round(p,2))+"</td><td style='color:"+col+";font-weight:bold'>"+sign+str(round(gn,2))+"%</td><td>$"+str(round(val,2))+"</td></tr>"
 if rows=="":
  rows="<tr><td colspan=6 style='text-align:center;color:#666'>Sin posiciones - Compra BTC en Telegram</td></tr>"
 hrows=""
 for x in hist[-15:][::-1]:
  t=x.get('t','')
  m=x.get('m','')
  prc=x.get('p',0)
  f=x.get('f','')
  if t=="VENTA":
   co="#00d395"
  else:
   co="#ffb020"
  hrows=hrows+"<tr><td>"+f+"</td><td style='color:"+co+"'>"+t+"</td><td>"+m+"</td><td>$"+str(round(prc,2))+"</td></tr>"
 if hrows=="":
  hrows="<tr><td colspan=4 style='text-align:center;color:#666'>Sin trades</td></tr>"
 bal_s=str(round(bal,2))
 tot_s=str(round(tot,2))
 pnl=tot-1000.0
 pnl_s=str(round(pnl,2))
 if pnl>=0:
  pnl_col="#00d395"
 else:
  pnl_col="#ff4d4d"
 labels=""
 data=""
 for i in range(len(pr)):
  labels=labels+str(i)+","
  data=data+str(pr[i])+","
 html="<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
 html=html+"<style>body{background:#0b0e11;color:#e6
