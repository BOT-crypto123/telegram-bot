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
 try:return json.load(open(FILE))
 except:return{"bal":1000.0,"holds":{},"hist":[]}
def save(s):json.dump(s,open(FILE,"w"))
async def price(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",headers={"User-Agent":"M"})
   return float(r.json()["data"]["amount"])
 except:return 65000.0
async def send(cid,txt):
 async with httpx.AsyncClient(timeout=10) as c:
  kb={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load()
 bal=s["bal"]
 rows=""
 for k,v in s["holds"].items():
  p=await price(k)
  rows+=f"<tr><td>{k}</td><td>{v['a']:.4f}</td><td>${p:.2f}</td></tr>"
 if not rows:rows="<tr><td colspan=3>Sin posiciones</td></tr>"
 h=""
 for x in s["hist"][-10:][::-1]:h+=f"<tr><td>{x['m']}</td><td>{x['t']}</td></tr>"
 html=f"<html><body style='background:#0a0e14;color:#fff;font-family:monospace;padding:15px'><h2 style='color:#58a6ff'>V866-B DASHBOARD</h2><h3>Saldo ${bal:.2f}</h3><table border=1 width=100%><tr><th>MON</th><th>CANT</th><th>PRECIO</th></tr>{rows}</table><br><table border=1 width=100%><tr><th>MON</th><th>TIPO</th></tr>{h}</table><p>{DASH}</p></body></html>"
 return HTMLResponse(html)
@app.post("/webhook")
async def wh(r:Request):
 d=await r.json()
 m=d.get("message",{})
 cid=m.get("chat",{}).get("id")
 txt=(m.get("text")or"").upper()
 if not cid:return{"ok":True}
 s=load()
 if txt in ["BTC","ETH","SOL","XRP"]:
  p=await price(txt)
  await send(cid,f"{txt} ${p:.2f} BAL ${s['bal']:.2f} {DASH}")
 else:
  await send(cid,f"V866-B OK BAL ${s['bal']:.2f} {DASH}")
 return{"ok":True}
@app.get("/")
def home():return{"ok":DASH}
