import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
NL=chr(10)
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
 return HTMLResponse("<body style=background:#000;color:#fff;font-family:monospace;padding:20px>V897 SALDO "+str(b)+"</body></html>")
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
   txt="WALL ST PRO - "+m+NL+NL
   txt=txt+"SALDO $"+str(round(b,2))+NL
   txt=txt+"TOTAL $"+str(round(tot,2))+NL
   txt=txt+"PNL $"+str(round(pnl,2))+NL+NL
   txt=txt+m+" $"+str(round(pr,0))+NL+NL
   txt=txt+"POSICIONES:"+NL
   if len(hh)==0:txt=txt+"No pos"+NL
   else:
    for k in hh:
     v=hh[k]
     try:pc=await P(k);gn=(pc/v["e"]-1)*100
     except:gn=0
     txt=txt+k+" "+str(round(gn,1))+"%"+NL
   await G(i,txt,m)
   return{"ok":1}
  try:p=await P(m)
  except:p=0
  if a=="BUY":
   s["h"][m]={"a":100/p if p else 0,"e":p};s["b"]=s["b"]-100;S(s);await G(i,"BUY "+m,m)
  else:
   if m in s["h"]:s["b"]=s["b"]+100;del s["h"][m];S(s);await G(i,"SELL "+m,m)
  return{"ok":1}
 x=q.get("message",{});i=x.get("chat",{}).get("id")
 if not i:return{"ok":1}
 t=(x.get("text")or"").upper()
 if t in["BTC","ETH","SOL","XRP"]:
  try:p=await P(t)
  except:p=0
  await G(i,t+" $"+str(round(p,0)),t)
 else:await G(i,"V897 LIVE", "BTC")
 return{"ok":1}
