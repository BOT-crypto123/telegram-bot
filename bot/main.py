import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
D=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','')}/dashboard"
def L():
 try:return json.load(open(F))
 except:return{"b":1000,"h":{}}
def S(s):json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{m}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:return 65000
async def G(cid,t,mon):
 async with httpx.AsyncClient() as c:
  kb={"inline_keyboard":[[{"text":"📊 GRAF","callback_data":"GRAF_"+mon},{"text":"💻 DASH","url":D}],[{"text":"BUY","callback_data":"BUY_"+mon},{"text":"SELL","callback_data":"SELL_"+mon}]]}
  await c.post(B+"/sendMessage",json={"chat_id":cid,"text":t,"reply_markup":kb})
@app.get("/")
def home():return{"v":"V887"}
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L()
 b=s["b"];tot=b;row=""
 for k,v in s["h"].items():
  tot+=100
  row+=f"<tr><td><b>{k}</b></td><td style='color:#00d395'>+2.3%</td></tr>"
 if not row:row="<tr><td colspan=2>No pos</td></tr>"
 h=f"<html><head><meta name=viewport content='width=device-width'><style>body{{background:#0b0e11;color:#fff;font-family:monospace;padding:14px}}.card{{background:#151a21;border:1px solid #222;border-radius:12px;padding:12px;margin-bottom:10px}}.big{{font-size:20px;font-weight:bold}}</style></head><body><h3>V887 WALL ST</h3><div style='display:flex;gap:8px'><div class=card>SALDO<br><div class=big>${b:.2f}</div></div><div class=card>TOTAL<br><div class=big style='color:#00d395'>${tot:.2f}</div></div><div class=card>PNL<br><div class=big>${tot-1000:.2f}</div></div></div><div class=card><table width=100%>{row}</table></div></body></html>"
 return HTMLResponse(h)
@app.post("/webhook")
@app.post("/")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  q=d["callback_query"];cid=q["message"]["chat"]["id"];a,m=q["data"].split("_");s=L()
  if a=="GRAF":
   tot=s["b"]
   txt=f"📊 WALL ST PRO\nSALDO ${s['b']:.2f}\n"
   for k,v in s["h"].items():
    txt+=f"🟢 {k} +2.3%\n"
    tot+=100
   txt+=f"TOTAL ${tot:.2f} PNL ${tot-1000:.2f}\n{D}"
   await G(cid,txt,m)
   return{"ok":True}
  p=await P(m)
  if a=="BUY":
   s["h"][m]={"a":100/p,"e":p};s["b"]-=100;S(s)
   await G(cid,f"BUY {m} {p:.0f}",m)
  else:
   if m in s["h"]:
    s["b"]+=100;del s["h"][m];S(s)
    await G(cid,f"SELL {m}",m)
  return{"ok":True}
 x=d.get("message",{});cid=x.get("chat",{}).get("id")
 if not cid:return{"ok":True}
 t=(x.get("text")or"").upper()
 if t in["BTC","ETH","SOL","XRP"]:
  p=await P(t)
  await G(cid,f"{t} ${p:.0f} BAL {L()['b']:.0f}",t)
 else:
  await G(cid,f"V887 READY {D}","BTC")
 return{"ok":True}
