import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
D=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','')}/dashboard"
def L():
 try:
  return json.load(open(F))
 except:
  return{"b":1000,"h":{}}
def S(s):
 json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{m}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:
  return 65000
async def G(cid,t,mon):
 async with httpx.AsyncClient() as c:
  kb={"inline_keyboard":[[{"text":"GRAF","callback_data":"GRAF_"+mon},{"text":"DASH","url":D}],[{"text":"BUY","callback_data":"BUY_"+mon},{"text":"SELL","callback_data":"SELL_"+mon}]]}
  await c.post(B+"/sendMessage",json={"chat_id":cid,"text":t,"reply_markup":kb})
@app.get("/")
def home():
 return{"v":"V890"}
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L()
 b=s["b"]
 h=s["h"]
 html="<html><body style='background:#000;color:#fff;font-family:monospace;padding:12px'><h3>V890 CALLE MURALLA</h3>"
 html=html+f"<div>SALDO {b:.2f}</div><div>TOTAL {b:.2f}</div>"
 if len(h)==0:
  html=html+"<div>No pos</div>"
 else:
  for k in h:
   html=html+f"<div>{k}</div>"
 html=html+"</body></html>"
 return HTMLResponse(html)
@app.post("/webhook")
@app.post("/")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  q=d["callback_query"]
  cid=q["message"]["chat"]["id"]
  dat=q["data"]
  parts=dat.split("_")
  a=parts[0]
  m=parts[1]
  s=L()
  if a=="GRAF":
   b=s["b"]
   txt="DASHBOARD\n"
   txt=txt+f"SALDO {b:.2f}\n"
   h=s["h"]
   if len(h)==0:
    txt=txt+"No pos\n"
   else:
    for k in h:
     txt=txt+f"{k}\n"
   txt=txt+D
   await G(cid,txt,m)
   return{"ok":True}
  p=await P(m)
  if a=="BUY":
   s["h"][m]={"a":100/p,"e":p}
   s["b"]=s["b"]-100
   S(s)
   await G(cid,f"BUY {m}",m)
  else:
   hh=s["h"]
   if m in hh:
    s["b"]=s["b"]+100
    del s["h"][m]
    S(s)
    await G(cid,f"SELL {m}",m)
  return{"ok":True}
 x=d.get("message",{})
 cid=x.get("chat",{}).get("id")
 if not cid:
  return{"ok":True}
 t=(x.get("text")or"").upper()
 if t in["BTC","ETH","SOL","XRP"]:
  p=await P(t)
  await G(cid,f"{t} {p:.0f}",t)
 else:
  await G(cid,"V890 LIVE", "BTC")
 return{"ok":True}
