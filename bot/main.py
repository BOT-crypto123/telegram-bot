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
  # teclado partido para no cortar
  b1={"text":"GRAF","url":u}
  b2={"text":"DASH","url":D}
  b3={"text":"BUY","callback_data":"BUY_"+mon}
  b4={"text":"SELL","callback_data":"SELL_"+mon}
  row1=[b1,b2]
  row2=[b3,b4]
  if buy:
   kb={"inline_keyboard":[row1,row2]}
  else:
   kb={"inline_keyboard":[row1]}
  await c.post(B+"/sendMessage",json={"chat_id":cid,"text":t,"reply_markup":kb})

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L()
 b=s["bal"]
 h=s["holds"]
 hs=s["hist"]
 tot=b
 r=""
 for k,v in h.items():
  p=await P(k)
  a=v["a"]
  e=v["e"]
  vl=a*p
  tot+=vl
  gn=(p/e-1)*100 if e else 0
  co="green" if gn>=0 else "red"
  r+=f"<tr><td>{k}</td><td>{a:.4f}</td><td>{e:.0f}</td><td>{p:.0f}</td><td style='color:{co}'>{gn:.1f}%</td><td>{vl:.0f}</td></tr>"
 if r=="":
  r="<tr><td colspan=6>No pos</td></tr>"
 hr=""
 for x in hs[-10:][::-1]:
  hr+=f"<tr><td>{x['f']}</td><td>{x['t']}</td><td>{x['m']}</td><td>{x['p']:.0f}</td></tr>"
 if hr=="":
  hr="<tr><td colspan=4>No trades</td></tr>"
 h1="<html><head><meta name=viewport content='width=device-width'>"
 h2="<style>body{background:#0b0e11;color:#fff;font-family:monospace;padding:10px}"
 h
