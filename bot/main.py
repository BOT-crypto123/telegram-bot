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
 except:return 0
async def C():
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600")
   d=sorted(r.json())[-5:]
   return d[0][4],d[-1][4]
 except:return 0,0
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  k={"inline_keyboard":[[{"text":"GRAF","callback_data":"GRAF_"+m}],[{"text":"BUY","callback_data":"BUY_"+m},{"text":"SELL","callback_data":"SELL_"+m}]]}
  await c.post(B+"/sendMessage",json={"chat_id":i,"text":t,"reply_markup":k})
@app.get("/dashboard",response_class=HTMLResponse)
async def d():
 s=L();b=s["b"];h=s["h"];tot=b;rows=""
 if len(h)==0:rows="<tr><td>No pos</td></tr>"
 else:
  for k in h:
   v=h[k];pr=await P(k);tot+=v["a"]*pr
   rows+=f"<tr><td>{k}</td><td>{(pr/v['e']-1)*100:.1f}%</td></tr>"
 return HTMLResponse(f"<body style='background:#0b0e11;color:#fff;font-family:monospace;padding:12px'><h3>WALL ST PRO</h3>SALDO ${b:.2f} TOTAL ${tot:.2f} PNL ${tot-1000:.2f}<table>{rows}</table></body></html>")
@app.post("/webhook")
@app.post("/")
async def w(r:Request):
 q=await r.json()
 if "callback_query" in q:
  c=q["callback_query"];i=c["message"]["chat"]["id"];a,m=c["data"].split("_");s=L()
  if a=="GRAF":
   b=s["b"];hh=s["h"];tot=b;txt="";o,n=await C();ch=(n/o-1)*100 if o else 0
   for k in hh:
    v=hh[k];pr=await P(k);tot+=v["a"]*pr
   pnl=tot-1000;pr=await P(m)
   txt=f"WALL ST PRO - {m}\n\n"
   txt+=f"SALDO ${b:.2f}\nTOTAL ${tot:.2f}\nPNL ${pnl:.2f}\n\n"
   txt+=f"{m}: ${pr:.2f}\n40H: {ch:+.2f}%\n\n"
   txt+="--- POSICIONES ---\n"
   if len(hh)==0:txt+="Sin posiciones\n"
   else:
    for k in hh:
     v=hh[k];pc=await P(k);gn=(pc/v["e"]-1)*100;e="🟢" if gn>=0 else "🔴"
     txt+=f"{e} {k} {gn:+.1f}% | ${v['a']*pc:.0f} | Ent ${v['e']:.0f}\n"
   txt+="\n--- HISTORIAL ---\nUltimos trades listos en web"
   await G(i,txt,m)
   return{"ok":1}
  p=await P(m)
  if a=="BUY":s["h"][m]={"a":100/p,"e":p};s["b"]-=100;S(s);await G(i,f"BUY {m} ${p:.0f}",m)
else:
