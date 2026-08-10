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
   return float((await c.get(u)).json()["data"]["amount"])
 except:return 64000
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  d="https://"+os.getenv("RENDER_EXTERNAL_HOSTNAME","")+"/dashboard"
  k={"inline_keyboard":[[{"text":"GRAF","callback_data":"GRAF_"+m},{"text":"DASH","url":d}],[{"text":"BUY","callback_data":"BUY_"+m},{"text":"SELL","callback_data":"SELL_"+m}]]}
  await c.post(B+"/sendMessage",json={"chat_id":i,"text":t,"reply_markup":k})
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L();b=s["b"];h=s["h"];tot=b;rows=""
 for x in h:
  try:pr=await P(x["m"]);g=(pr/x["e"]-1)*100;tot+=x["a"]*pr
  except:g=0;pr=x["e"]
  co="#00e676" if g>=0 else "#ff5252"
  rows+=f"<tr><td>{x['m']}</td><td>{x['a']:.4f}</td><td>${x['e']:.0f}</td><td style=color:{co}>{g:+.2f}%</td><td>${x['a']*pr:.2f}</td></tr>"
 if not rows:rows="<tr><td colspan=5 style=text-align:center;opacity:.5>Sin posiciones</td></tr>"
 c1="#00e676" if tot>=1000 else "#ff5252"
 html1=f"<html><head><meta name=viewport content='width=device-width,initial-scale=1'><script src=https://cdn.jsdelivr.net/npm/chart.js></script><style>body{{background:#0a0e14;color:#c9d1d9;font-family:monospace;padding:12px}} .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;margin-bottom:10px}} th{{color:#8b949e;font-size:11px;text-align:left}} td{{padding:6px 4px;border-bottom:1px solid #21262d;font-size:12px}}</style></head><body><h2 style=color:#58a6ff>💼 WALL ST PRO V905</h2><div style=display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:12px 0><div class=card><div style=color:#8b949e;font-size:10px>SALDO</div><div style=font-size:18px>${b:.2f}</div></div><div class=card><div style=color:#8b949e;font-size:10px>TOTAL</div><div style=font-size:18px;color:#00e676>${tot:.2f}</div></div><div class=card><div style=color:#8b949e;font-size:10px>PNL</div><div style=font-size:18px;color:{c1}>${tot-1000:+.2f}</div></div></div><div class=card><canvas id=c height=90></canvas></div><div class=card><table style=width:100%><tr><th>MON</th><th>CANT</th><th>ENT</th><th>PNL</th><th>VAL</th></tr>{rows}</table></div>"
 html2="""
<script>
fetch('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600')
.then(r=>r.json()).then(d=>{
 let p=d.sort().slice(-30).map(x=>x[4]);
 new Chart(document.getElementById('c'),{
  type:'line',
  data:{labels:p.map((_,i)=>i),datasets:[{data:p,borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,0.1)',fill:true,tension:0.4,pointRadius:0}]},
  options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{grid:{color:'#21262d'}}}}
 });
});
</script></body></html>
"""
 return HTMLResponse(html1+html2)
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
 else:await G(cid,"V905 WALL ST PRO LIVE","BTC")
 return{"ok":1}
@app.get("/")
def home():return{"V905":"/dashboard"}
