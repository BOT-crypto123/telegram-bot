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

async def send(cid,txt,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=10) as c:
  u="https://www.tradingview.com/symbols/"+mon+"USDT/"
  if buy:
   kb={"inline_keyboard":[[{"text":"GRAFICA","url":u},{"text":"DASHBOARD","url":DASH}],[{"text":"COMPRAR","callback_data":"BUY_"+mon},{"text":"VENDER","callback_data":"SELL_"+mon}]]}
  else:
   kb={"inline_keyboard":[[{"text":"GRAFICA","url":u},{"text":"DASHBOARD","url":DASH}]]}
  km={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":"Menu","reply_markup":km})

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load()
 bal=s.get('bal',1000.0)
 holds=s.get('holds',{})
 hist=s.get('hist',[])
 rows=""
 tot=bal
 for k,v in holds.items():
  p=await price(k)
  amt=v.get('a',0)
  ent=v.get('e',0)
  val=amt*p
  tot=tot+val
  if ent>0:
   gn=(p/ent-1)*100
  else:
   gn=0
  if gn>=0:
   col="#00e676"
  else:
   col="#ff5252"
  rows=rows+"<tr><td>"+k+"</td><td>"+str(round(amt,5))+"</td><td>$"+str(round(ent,1))+"</td><td>$"+str(round(p,1))+"</td><td style='color:"+col+"'>"+str(round(gn,1))+"%</td><td>$"+str(round(val,1))+"</td></tr>"
 if rows=="":
  rows="<tr><td colspan=6>Sin posiciones</td></tr>"
 hrows=""
 for x in hist[-20:]:
  t=x.get('t','')
  m=x.get('m','')
  pr=x.get('p',0)
  f=x.get('f','')
  if t=="VENTA":
   co="#00e676"
  else:
   co="#ffab40"
  hrows=hrows+"<tr><td>"+f+"</td><td style='color:"+co+"'>"+t+"</td><td>"+m+"</td><td>$"+str(pr)+"</td></tr>"
 if hrows=="":
  hrows="<tr><td colspan=4>Sin trades</td></tr>"
 bal_s=str(round(bal,2))
 tot_s=str(round(tot,2))
 pnl_s=str(round(tot-bal,2))
 html="<html><head><meta name='viewport' content='width=device-width'><style>body{background:#0a0e14;color:#fff;font-family:monospace;padding:12px}.card{background:#161b22;border:1px solid #333;border-radius:12px;padding:12px;margin-bottom:12px}</style></head><body>"
 html=html+"<h2 style='color:#58a6ff'>V871 WALL ST</h2>"
 html=html+"<div style='display:flex;gap:8px'><div class='card'>SALDO<br><b>$"+bal_s+"</b></div><div class='card'>TOTAL<br><b style='color:#00e676'>$"+tot_s+"</b></div><div class='card'>PNL<br><b>$"+pnl_s+"</b></div></div>"
 html=html+"<div class='card'><b>POSICIONES</b><table width=100%><tr><th>MON</th><th>CANT</th><th>ENT</th><th>ACT</th><th>PNL</th><th>VAL</th></tr>"+rows+"</table></div>"
 html=html+"<div class='card'><b>HISTORIAL</b><table width=100%><tr><th>FECHA</th><th>TIPO</th><th>MON</th><th>PRECIO</th></tr>"+hrows+"</table></div>"
 html=html+"<p><a href='"+DASH+"' style='color:#58a6ff'>"+DASH+"</a></p></body></html>"
 return HTMLResponse(html)

@app.post("/webhook")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  cq=d["callback_query"]
  cid=cq["message"]["chat"]["id"]
  data=cq["data"]
  parts=data.split("_")
  act=parts[0]
  mon=parts[1]
  s=load()
  p=await price(mon)
  if act=="BUY":
   if s['bal']>=100:
    s['holds'][mon]={'a':100/p,'e':p}
    s['bal']=s['bal']-100
    s['hist'].append({'f':datetime.now().strftime("%d/%m %H:%M"),'t':"COMPRA",'m':mon,'p':p})
    save(s)
    await send(cid,"COMPRADO "+mon+" @ "+str(round(p,2))+" BAL "+str(round(s['bal'],2)),mon,True)
   else:
    await send(cid,"Sin saldo",mon,True)
  else:
   if mon in s['holds']:
    amt=s['holds'][mon]['a']
    val=amt*p
    s['bal']=s['bal']+val
    s['hist'].append({'f':datetime.now().strftime("%d/%m %H:%M"),'t':"VENTA",'m':mon,'p':p})
    del s['holds'][mon]
    save(s)
    await send(cid,"VENDIDO "+mon+" $"+str(round(val,2))+" BAL "+str(round(s['bal'],2)),mon,True)
   else:
    await send(cid,"No tienes "+mon,mon,True)
  return {"ok":True}
 m=d.get("message",{})
 cid=m.get("chat",{}).get("id")
 txt=(m.get("text")or"").upper()
 if not cid:
  return {"ok":True}
 s=load()
 if txt in ["BTC","ETH","SOL","XRP"]:
  p=await price(txt)
  await send(cid,txt+": $"+str(p)+" BAL $"+str(s['bal'])+" "+DASH,txt,True)
 elif txt=="PORTAFOLIO":
  await send(cid,"V871 WALL ST BAL $"+str(s['bal'])+" "+DASH,"BTC",False)
 else:
  await send(cid,"V871 WALL ST LISTO "+DASH,"BTC",False)
 return {"ok":True}

@app.get("/")
def home():
 return {"V871":DASH}
