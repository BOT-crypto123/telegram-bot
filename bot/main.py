import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
def L():
 try:return json.load(open(F))
 except:return{"b":1000,"h":{}}
def S(s):json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{m}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:return 0
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  k={"inline_keyboard":[[{"text":"GRAF","callback_data":"GRAF_"+m}],[{"text":"BUY","callback_data":"BUY_"+m},{"text":"SELL","callback_data":"SELL_"+m}]]}
  await c.post(B+"/sendMessage",json={"chat_id":i,"text":t,"reply_markup":k})
@app.get("/dashboard",response_class=HTMLResponse)
async def d():
 s=L()
 b=s["b"]
 return HTMLResponse("<body style='background:#000;color:#fff;font-family:monospace;padding:20px'><h3>V896 WALL ST</h3>SALDO "+str(b)+"</body></html>")
@app.post("/webhook")
@app.post("/")
async def w(r:Request):
 q=await r.json()
 if "callback_query" in q:
  c=q["callback_query"];i=c["message"]["chat"]["id"];a,m=c["data"].split("_");s=L()
  if a=="GRAF":
   b=s["b"];hh=s["h"];tot=b
   for k in hh:
    v=hh[k]
    try:
     pr=await P(k)
     tot=tot+v["a"]*pr
    except:tot=tot+100
   pnl=tot-1000
   try:pr=await P(m)
   except:pr=0
   txt="WALL ST PRO - "+m+"\n\n"
   txt=txt+"SALDO $"+str(round(b,2))+"\n"
   txt=txt+"TOTAL $"+str(round(tot,2))+"\n"
   txt=txt+"PNL $"+str(round(pnl,2))+"\n\n"
   txt=txt+m+" $"+str(round(pr,0))+"\n\n"
   txt=txt+"POSICIONES:\
