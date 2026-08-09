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
 except:return{"bal":1000.0,"holds":{},"hist":[],"auto":False}
def save(s):json.dump(s,open(FILE,"w"))
async def price(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",headers={"User-Agent":"M"})
   return float(r.json()["data"]["amount"])
 except:return 65000.0
async def candles():
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600",headers={"User-Agent":"M"})
   d=sorted(r.json())[-40:]
   return [x[4] for x in d]
 except:return[65000,65100,65200,65153]
async def send(cid,txt,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=10) as c:
  u=f"https://www.tradingview.com/symbols/{mon}USDT/"
  if buy:kb={"inline_keyboard":[[{"text":"GRAFICA","url":u},{"text":"DASHBOARD","url":DASH}],[{"text":"COMPRAR","callback_data":"BUY_"+mon},{"text":"VENDER","callback_data":"SELL_"+mon}]]}
  else:kb={"inline_keyboard":[[{"text":"GRAFICA","url":u},{"text":"DASHBOARD","url":DASH}]]}
  km={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":"Menu:","reply_markup":km})
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load();bal=s["bal"];pr=await candles()
 rows="";tot=bal
 for k,v in s["holds"].items():
  p=await price(k);val=v["a"]*p;tot+=val;gn=(p/v["e"]-1)*100 if v["e"]>0 else 0;co="#00e676" if gn>=0 else "#ff5252"
  rows+=f"<tr><td>{k}</td><td>{v['a']:.5f}</td><td>${v['e']:.1f}</td><td>${p:.1f}</td><td style='color:{co}'>{gn:+.1f}%</td><td>${val:.1f}</td></tr>"
 if not rows:rows="<tr><td colspan=6>Sin posiciones</td></tr>"
 hrows=""
 for x in s["hist"][-20:][::-1]:
  co="#00e676" if x["t"]=="VENTA" else "#ffab40";hrows+=f"<tr><td>{x['f']}</td><td style='color:{co}'>{x['t']}</td><td>{x['m']}</td><td>${x['p']:.2f}</td></tr>"
 if not hrows:hrows="<tr><td colspan=4>Sin trades</td></tr>"
 html=f"<html><head><meta name='viewport' content='width=device-width'><script src='https://cdn.jsdelivr.net/npm/chart.js'></script><style>body{{background:#0a0e14;color:#fff;font-family:monospace;padding:12px}}.card{{background:#161b22;border:1px solid #333;border-radius:12px;padding:12px;margin-bottom:12px}}th{{color:#888;font-size:11px}}td{{font-size:13px;padding:6px}}</style></head><body><h2 style='color:#58a6ff'>V869 WALL ST</h2><div style='display:flex;gap:8px'><div class='card'>SALDO<br><b>${bal:.2f}</b></div><div class='card'>TOTAL<br><b style='color:#00e676'>${tot:.2f}</b></div><div class='card'>PNL<br><b>${tot-bal:+.2f}</b></div></div><div class='card'><b>GRAFICA BTC 40H</b><canvas id='c' height='110'></canvas></div><div class='card'><b>POSICIONES</b><table width=100%><tr><th>MON</th><th>CANT</th><th>ENT</th><th>ACT</th><th>PNL</th><th>VAL</th></tr>{rows}</table></div><div class='card'><b>HISTORIAL</b><table width=100%><tr><th>FECHA</th><th>TIPO</th><th>MON</th><th>PRECIO</th></tr>{hrows}</table></div><script>new Chart(document.getElementById('c'),{{type:'line',data:{{labels:{list(range(len(pr)))},datasets:[{{data:{pr},borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,0.1)',fill:true,tension:0.4,pointRadius:0}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{display:false}},y:{{grid:{{color:'#222'}}}}}}}}})</script></body></html>"
 return HTMLResponse(html)
@app.post("/webhook")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  cq=d["callback_query"];cid=cq["message"]["chat"]["id"];act,mon=cq["data"].split("_");s=load();p=await price(mon)
  if act=="BUY":
   if s["bal"]>=100:s["holds"][mon]={"a":100/p,"e":p};s["bal"]-=100;s["hist"].append({"f":datetime.now().strftime("%d/%m %H:%M"),"t":"COMPRA","m":mon,"p":p});save(s);await send(cid,f"COMPRADO {mon} 100 USD @ {p:.2f} BAL {s['bal']:.2f}",mon,True)
   else:await send(cid,"Sin saldo",mon,True)
  else:
   if mon in s["holds"]:val=s["holds"][mon]["a"]*p;s["bal"]+=val;s["hist"].append({"f":datetime.now().strftime("%d
