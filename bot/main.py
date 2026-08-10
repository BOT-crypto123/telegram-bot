import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B="https://api.telegram.org/bot"+T
F="/tmp/b.json"
N=chr(10)
def L():
 try:return json.load(open(F))
 except:return{"b":1000,"h":[]}
def S(s):json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   u="https://api.coinbase.com/v2/prices/"+m+"-USD/spot"
   j=(await c.get(u)).json()
   return float(j["data"]["amount"])
 except:return 65000
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  d="https://"+os.getenv("RENDER_EXTERNAL_HOSTNAME","")+"/dashboard"
  k={"inline_keyboard":[[{"text":"GRAF","callback_data":"GRAF_"+m},{"text":"DASH","url":d}],[{"text":"BUY","callback_data":"BUY_"+m},{"text":"SELL","callback_data":"SELL_"+m}]]}
  await c.post(B+"/sendMessage",json={"chat_id":i,"text":t,"reply_markup":k})
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L();b=s["b"];h=s["h"];tot=b;r=""
 for x in h:
  try:
   pr=await P(x["m"]);g=(pr/x["e"]-1)*100;tot+=x["a"]*pr
  except:g=0
  co="#0f6" if g>=0 else "#f44"
  r+=f"<tr><td>{x['m']}</td><td style=color:{co}>{g:+.1f}%</td></tr>"
 if not r:r="<tr><td>No pos</td></tr>"
 return HTMLResponse(f"<body style=background:#000;color:#fff;font-family:monospace;padding:12px><h3>V903 WALL ST</h3><div>Saldo ${b:.0f} | Total ${tot:.2f} | PNL ${tot-1000:+.2f}</div><table>{r}</table><canvas id=c></canvas><script src=https://cdn.jsdelivr.net/npm/chart.js></script><script>fetch('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600').then(r=>r.json()).then(d=>{{let p=d.sort().slice(-30).map(x=>x[4]);new Chart(c,{{type:'line',data:{{labels:p.map((_,i)=>i),datasets:[{{data:p,borderColor:'#58a6ff',pointRadius:0}}]}}}})}})</script>")
@app.post("/webhook")
@app.post("/")
async def w(req:Request):
 q=await req.json()
 if "callback_query" in q:
  o=q["callback_query"];i=o["message"]["chat"]["id"];a1,m=o["data"].split("_");s=L()
  if a1=="GRAF":
   tot=s["b"]
   for x in s["h"]:
    try:tot+=x["a"]*await P(x["m"])
    except:tot+=100
   t="WALL ST "+m+N+f"SALDO ${s['b']:.0f}"+N+f"TOTAL ${tot:.2f}"+N+f"PNL ${tot-1000:.2f}"+N
   for x in s["h"]:
    try:g=(await P(x["m"])/x["e"]-1)*100
    except:g=0
    t+=x["m"]+f" {g:+.1f}%"+N
   await G(i,t,m);return{"ok":1}
  pr=await P(m)
  if a1=="BUY":s["h"].append({"m":m,"a":100/pr,"e":pr});s["b"]-=100;S(s)
  else:s["h"]=[x for x in s["h"] if x["m"]!=m];s["b"]+=100;S(s)
  await G(i,f"{a1} {m} {pr:.0f}",m);return{"ok":1}
 msg=q.get("message",{});cid=msg.get("chat",{}).get("id")
 if not cid:return{"ok":1}
 t=(msg.get("text")or"").upper()
 if t in["BTC","ETH","SOL","XRP"]:await G(cid,f"{t} {await P(t):.0f}",t)
 else:await G(cid,"V903 LIVE","BTC")
 return{"ok":1}
@app.get("/")
def home():return{"ok":"V903"}
