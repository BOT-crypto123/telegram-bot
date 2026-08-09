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
W=f"https://{C}/webhook"

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
  # GRAF ahora es callback, no URL
  b1={"text":"GRAF","callback_data":"GRAF_"+mon}
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

@app.on_event("startup")
async def setup():
 async with httpx.AsyncClient(timeout=10) as c:
  await c.get(B+f"/setWebhook?url={W}")

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
 h3=".c{background:#151a21;border:1px solid #222;border-radius:12px;padding:10px;margin-bottom:10px}"
 h4=".b{font-size:18px;font-weight:bold}th{color:#888;font-size:10px}td{font-size:12px;padding:5px}</style></head><body>"
 h5=f"<h3 style='color:#58a6ff'>V880 WALL ST</h3>"
 h6=f"<div style='display:flex;gap:6px'><div class=c>SALDO<br><div class=b>${b:.2f}</div></div>"
 h7=f"<div class=c>TOTAL<br><div class=b style='color:#0f0'>${tot:.2f}</div></div>"
 h8=f"<div class=c>PNL<br><div class=b>${tot-1000:.2f}</div></div></div>"
 h9=f"<div class=c><b>POS</b><table width=100%><tr><th>MON</th><th>QTY</th><th>ENT</th><th>NOW</th><th>%</th><th>VAL</th></tr>{r}</table></div>"
 hh=f"<div class=c><b>HIST</b><table width=100%><tr><th>DATE</th><th>TYPE</th><th>COIN</th><th>PRICE</th></tr>{hr}</table></div></body></html>"
 return HTMLResponse(h1+h2+h3+h4+h5+h6+h7+h8+h9+hh)

async def handle(r:Request):
 d=await r.json()
 if "callback_query" in d:
  q=d["callback_query"]
  cid=q["message"]["chat"]["id"]
  data=q["data"]
  act,mon=data.split("_")
  s=L()
  p=await P(mon)
  # NUEVO: GRAF muestra dashboard
  if act=="GRAF":
   b=s["bal"]
   holds=s["holds"]
   tot=b
   txt="📊 DASHBOARD V880\n"
   txt+=f"SALDO: ${b:.2f}\n"
   for k,v in holds.items():
    pr=await P(k)
    vl=v["a"]*pr
    tot+=vl
    gn=(pr/v["e"]-1)*100 if v["e"] else 0
    txt+=f"{k}: {v['a']:.4f} ENTRY {v['e']:.0f} NOW {pr:.0f} {gn:.1f}% VAL ${vl:.0f}\n"
   txt+=f"TOTAL: ${tot:.2f} PNL: ${tot-1000:.2f}\n{D}"
   await G(cid,txt,mon,True)
   return{"ok":True}
  if act=="BUY":
   if s["bal"]>=100:
    s["holds"][mon]={"a":100/p,"e":p}
    s["bal"]-=100
    s["hist"].append({"f":datetime.now().strftime("%d/%m %H:%M"),"t":"BUY","m":mon,"p":p})
    S
