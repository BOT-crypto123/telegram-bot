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

async def G(cid,t,mon):
 async with httpx.AsyncClient(timeout=5) as c:
  b1={"text":"GRAF","callback_data":"GRAF_"+mon}
  b2={"text":"DASH","url":D}
  b3={"text":"BUY","callback_data":"BUY_"+mon}
  b4={"text":"SELL","callback_data":"SELL_"+mon}
  kb={"inline_keyboard":[[b1,b2],[b3,b4]]}
  await c.post(B+"/sendMessage",json={"chat_id":cid,"text":t,"reply_markup":kb})

@app.get("/")
def root():
 return{"ok":True,"dash":D,"v":"V881"}

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L()
 b=s["bal"]
 tot=b
 r=""
 for k,v in s["holds"].items():
  p=await P(k)
  vl=v["a"]*p
  tot+=vl
  r+=f"<tr><td>{k}</td><td>{v['a']:.4f}</td><td>{v['e']:.0f}</td><td>{p:.0f}</td><td>{vl:.0f}</td></tr>"
 if r=="":
  r="<tr><td colspan=5>No pos</td></tr>"
 h=f"<html><body style='background:#0b0e11;color:#fff;font-family:monospace;padding:10px'><h3 style='color:#58a6ff'>V881 WALL ST</h3><div>SALDO ${b:.2f} TOTAL ${tot:.2f} PNL ${tot-1000:.2f}</div><br><table border=1><tr><th>MON</th><th>QTY</th><th>ENT</th><th>NOW</th><th>VAL</th></tr>{r}</table><br><a href='/' style='color:#58a6ff'>Home</a></body></html>"
 return HTMLResponse(h)

async def handle(d):
 if "callback_query" in d:
  q=d["callback_query"]
  cid=q["message"]["chat"]["id"]
  act,mon=q["data"].split("_")
  s=L()
  if act=="GRAF":
   txt=f"📊 DASH V881\nSALDO ${s['bal']:.2f}\n"
   tot=s["bal"]
   for k,v in s["holds"].items():
    p=await P(k)
    tot+=v["a"]*p
    txt+=f"{k} {v['a']:.4f} {p:.0f}\n"
   txt+=f"TOTAL ${tot:.2f}\n{D}"
   await G(cid,txt,mon)
   return{"ok":True}
  p=await P(mon)
  if act=="BUY":
   if s["bal"]>=100:
    s["holds"][mon]={"a":100/p,"e":p}
    s["bal"]-=100
    s["hist"].append({"f":datetime.now().strftime("%H:%M"),"t":"BUY","m":mon,"p":p})
    S(s)
    await G(cid,f"BUY {mon} {p:.0f} BAL {s['bal']:.0f}",mon)
  if act=="SELL":
   if mon in s["holds"]:
    s["bal"]+=s["holds"][mon]["a"]*p
    del s["holds"][mon]
    S(s)
    await G(cid,f"SELL {mon} BAL {s['bal']:.0f}",mon)
  return{"ok":True}
 m=d.get("message",{})
 cid=m.get("chat",{}).get("id")
 if not cid:
  return{"ok":True}
 t=(m.get("text")or"").upper()
 s=L()
 if t in["BTC","ETH","SOL","XRP"]:
  p=await P(t)
  await G(cid,f"{t} ${p:.0f} BAL {s['bal']:.0f}",t)
 else:
  await G(cid,f"V881 LISTO BAL {s['bal']:.0f} {D}","BTC")
 return{"ok":True}

@app.post("/webhook")
async def wh1(r:Request):
 return await handle(await r.json())

@app.post("/")
async def wh2(r:Request):
 return await handle(await r.json())
