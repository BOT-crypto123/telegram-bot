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
def h():
 return{"v":"V889","dash":D}
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L()
 b=s["b"]
 tot=b
 rows=""
 for k,v in s["h"].items():
  tot=tot+100
  rows=rows+f"<tr><td>{k}</td><td>+2.3%</td></tr>"
 if rows=="":
  rows="<tr><td>No pos</td></tr>"
 html=f"<html><body style='background:#000;color:#fff;font-family:monospace;padding:12px'><h3>V889 CALLE MURALLA</h3><div style='display:flex;gap:8px'><div style='background:#151a21;padding:12px;border-radius:12px'>SALDO ${b:.2f}</div><div style='background:#151a21;padding:12px;border-radius:12px'>TOTAL ${tot:.2f}</div><div style='background:#151a21;padding:12px;border-radius:12px'>PNL ${tot-1000:.2f}</div></div><table>{rows}</table></body></html>"
 return HTMLResponse(html)
@app.post("/webhook")
@app.post("/")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  q=d["callback_query"]
  cid=q["message"]["chat"]["id"]
  a,m=q["data"].split("_")
  s=L()
  if a=="GRAF":
   tot=s["b"]
   txt="DASHBOARD CALLE MURALLA\n"
   txt=txt+f"SALDO ${s['b']:.2f}\n"
   if not s["h"]:
    txt=txt+"No pos\n"
   for k in s
