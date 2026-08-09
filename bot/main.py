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
 try:
  return json.load(open(FILE))
 except:
  return {"bal":1000.0,"holds":{},"hist":[]}
def save(s):
 json.dump(s,open(FILE,"w"))

async def price(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",headers={"User-Agent":"M"})
   return float(r.json()["data"]["amount"])
 except:
  return 65000.0

async def candles():
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600",headers={"User-Agent":"M"})
   d=sorted(r.json())[-40:]
   return [x[4] for x in d]
 except:
  return [65000,65100,65200,65153]

async def send(cid,txt,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=10) as c:
  u="https://www.tradingview.com/symbols/"+mon+"USDT/"
  if buy:
   kb={"inline_keyboard":[[{"text":"GRAF","url":u},{"text":"DASH","url":DASH}],[{"text":"COMPRA","callback_data":"BUY_"+mon},{"text":"VENTA","callback_data":"SELL_"+mon}]]}
  else:
   kb={"inline_keyboard":[[{"text":"GRAF","url":u},{"text":"DASH","url":DASH}]]}
  km={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":"Menu","reply_markup":km})

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load()
 bal=s.get('bal',1000.0)
 holds=s.get('holds',{})
 hist=s.get('hist',[])
 pr=await candles()
 rows=""
 tot=bal
 for k,v in holds.items():
  p=await price(k)
  amt=v.get('a',0)
  ent=v.get('e',0)
  val=amt*p
  tot+=val
  gn=(p/ent-1)*100 if ent>0 else 0
  col="green" if gn>=0 else "red"
  rows+=f"<tr><td>{k}</td><td>{round(amt,5)}</td><td>{round(ent)}"
  rows+=f"</td><td>{round(p)}</td><td style='color:{col}'>{round(gn,1)}%"
  rows+=f"</td><td>{round(val)}</td></tr>"
 if rows=="":
  rows="<tr><td colspan=6>Sin pos</td></tr>"
 hrows=""
 for x in hist[-15:][::-1]:
  t=x.get('t','')
  co="green" if t=="VENTA" else "orange"
  hrows+=f"<tr><td>{x.get('f','')}</td><td style='color:{co}'>"
  hrows+=f"{t}</td><td>{x.get('m','')}</td><td>{x.get('p',0)}</td></tr>"
 if hrows=="":
  hrows="<tr><td colspan=4>Sin trades</td></tr>"
 a="<html><head><meta name='viewport' content='width=device-width'>"
 b="<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
 c="<style>"
 d="body{background:#000;color:#fff;font-family:monospace;padding:10px}"
 e=".card{background:#111;border:1px solid #333;border-radius:10px;"
 f="padding:10px;margin-bottom:10px}"
 g="th{color:#888;font-size:10px}td{font-size:12px;padding:5px}"
 h="</style></head><body>"
 i=f"<h3 style='color:#0af'>V874 WALL ST</h3>"
 j=f"<div style='display:flex;gap:6px'><div class='card'>SALDO<br><b>${round(bal,2)}</b></div>"
 k=f"<div class='card'>TOTAL<br><b style='color:#0f0'>${round(tot,2)}</b></div>"
 l=f"<div class='card'>PNL<br><b>${round(tot-1000,2)}</b></div></div>"
 m="<div class='card'><canvas id='c' height='100'></canvas></div>"
 n=f"<div class='card'><b>POS</b><table width=100%><tr><th>MON</th><th>CANT</th><th>ENT</th><th>ACT</th><th>%</th><th>VAL</th></tr>{rows}</table></div>"
 o=f"<div class='card'><b>HIST</b><table width=100%><tr><th>FECHA</th><th>TIPO</th><th>MON</th><th>PREC</th></tr>{hrows}</table></div>"
 p=f"<script>new Chart(document.getElementById('c'),{{type:'line',data:{{labels:{list(range(len(pr)))},datasets:[{{data:{pr},borderColor:'#0af',fill:true,pointRadius:0}}]}},options:{{plugins:{{legend:{{display:false}}}}}}}})</script></body></html>"
 html=a+b+c+d+e+f+g+h+i+j+k+l+m+n+o+p
 return HTMLResponse(html)

@app.post("/webhook")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  cq=d["callback_query"]
  cid=cq["message"]["chat"]["id"]
  act,mon=cq["data"].split("_")
  s=load()
  p=await price(mon)
  if act=="BUY":
   if s['bal']>=100:
    s['holds'][mon]={'a':100/p,'e':p}
    s['bal']-=100
    s['hist'].append({'f':datetime.now().strftime("%d/%m %H:%M"),'t':"COMPRA",'m':mon,'p':p})
    save(s)
    await send(cid,f"COMPRA {mon} {p:.1f} BAL {s['bal']:.1f}",mon,True)
   else:
    await send(cid,"Sin saldo",mon,True)
  else:
   if mon in s['holds']:
    amt=s['holds'][mon]['a']
    val=amt*p
    s['bal']+=val
    s['hist'].append({'f':datetime.now().strftime("%d/%m %H:%M"),'t':"VENTA",'m':mon,'p':p})
    del s['holds'][mon]
    save(s)
    await send(cid,f"VENTA {mon} {val:.1f} BAL {s['bal']:.1f}",mon,True)
   else:
    await send(cid,f"No tienes {mon}",mon,True)
  return {"ok":True}
 m=d.get("message",{})
 cid=m.get("chat",{}).get("id")
 txt=(m.get("text")or"").upper()
 if not cid:
  return {"ok":True}
 s=load()
 if txt in ["BTC","ETH","SOL","XRP"]:
  p=await price(txt)
  await send(cid,f"{txt} ${p:.1f} BAL ${s['bal']:.1f} {DASH}",txt,True)
 elif txt=="PORTAFOLIO":
  await send(cid,f"V874 BAL ${s['bal']:.1f} {DASH}","BTC",False)
 else:
  await send(cid,f"V874 LISTO {DASH}","BTC",False)
 return {"ok":True}

@app.get("/")
def home():
 return {"V874":DASH}
