import os, json, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
TOKEN=os.getenv("TELEGRAM_TOKEN","")
BASE=f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE="/tmp/bot_state.json"
MONEDAS=["BTC","ETH","SOL","XRP"]
CAPITAL=1000.0
HOST=os.getenv("RENDER_EXTERNAL_HOSTNAME","")
DASH_URL=f"https://{HOST}/dashboard"
def load_state():
 try:
  with open(STATE_FILE,"r") as f:
   return json.load(f)
 except:
  return {"auto":False,"chat_id":None,"virtual_balance":CAPITAL,"holdings":{},"trade_history":[]}
def save_state(s):
 with open(STATE_FILE,"w") as f:
  json.dump(s,f)
async def get_data(sym):
 try:
  async with httpx.AsyncClient(timeout=15) as c:
   try:
    r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot",headers={"User-Agent":"Mozilla/5.0"})
    return float(r.json()["data"]["amount"]),0.0
   except:
    pass
   try:
    m={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
    url=f"https://api.coingecko.com/api/v3/simple/price?ids={m.get(sym,'bitcoin')}&vs_currencies=usd"
    r2=await c.get(url,headers={"User-Agent":"Mozilla/5.0"})
    return float(r2.json()[m.get(sym,"bitcoin")]["usd"]),0.0
   except:
    pass
 except:
  pass
 return 65138.0,0.0
async def send_msg(chat_id,text,moneda="BTC",btns=False):
 if btns:
  kb={"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}],[{"text":f"COMPRAR {moneda}","callback_data":f"BUY_{moneda}"},{"text":f"VENDER {moneda}","callback_data":f"SELL_{moneda}"}]]}
 else:
  kb={"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}]]}
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown","reply_markup":kb})
async def send_menu(chat_id,text):
 kb={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"},{"text":"ESTADO"}],[{"text":"AUTO ON"},{"text":"AUTO OFF"}]],"resize_keyboard":True}
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown","reply_markup":kb})
async def cq_answer(id,txt):
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/answerCallbackQuery",json={"callback_query_id":id,"text":txt})
@app.get("/dashboard",response_class=HTMLResponse)
async def dashboard():
 s=load_state()
 bal=s.get("virtual_balance",0)
 html=f"<h1>V866-B OK</h1><p>Saldo {bal}</p><p>Auto {s.get('auto')}</p><p>{s.get('holdings')}</p>"
 return HTMLResponse(content=html)
@app.post("/webhook")
async def webhook(req: Request):
 data=await req.json()
 if "callback_query" in data:
  cq=data["callback_query"]
  chat_id=cq["message"]["chat"]["id"]
  accion,moneda=cq["data"].split("_")
  s=load_state()
  price,_=await get_data(moneda)
  await cq_answer(cq["id"],f"{accion} {moneda}")
  if accion=="BUY":
   monto=min(200,s["virtual_balance"])
   if monto<5:
    await send_msg(chat_id,f"Sin saldo Bal {s['virtual_balance']:.2f}",moneda)
    return {"ok":True}
   amount=(monto*0.998)/price if price>0 else 0
   s["virtual_balance"]-=monto
   if moneda not in s["holdings"]:
    s["holdings"][moneda]={"amount":0,"entry":price}
   old=s["holdings"][moneda]
   tot=old["amount"]+amount
   avg=(old["amount"]*old["entry"]+amount*price)/tot if tot>0 else price
   s["holdings"][moneda]={"amount":tot,"entry":avg}
   s["trade_history"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":moneda,"tipo":"COMPRA","precio":price,"monto":monto,"ganancia":0})
   save_state(s)
   await send_msg(chat_id,f"COMPRA {moneda} {monto:.2f} @ {price:.2f} Bal {s['virtual_balance']:.2f}",moneda,True)
  else:
   hold=s.get("holdings",{}).get(moneda)
   if not hold:
    await send_msg(chat_id,f"No tienes {moneda}",moneda)
    return {"ok":True}
   val=hold["amount"]*price*0.998
   gan=((price-hold["entry"])/hold["entry"]*100) if hold["entry"]>0 else 0
   s["virtual_balance"]+=val
   s["trade_history"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":moneda,"tipo":"VENTA","precio":price,"monto":val,"ganancia":gan})
   del s["holdings"][moneda]
   save_state(s)
   await send_msg(chat_id,f"VENTA {moneda} {val:.2f} Gan {gan:.2f}% Bal {s['virtual_balance']:.2f}",moneda)
  return {"ok":True}
 msg=data.get("message",{})
 chat_id=msg.get("chat",{}).get("id")
 text=(msg.get("text") or "").strip().upper()
 if not chat_id:
  return {"ok":True}
 s=load_state()
 s["chat_id"]=chat_id
 if text=="AUTO ON":
  s["auto"]=True
  save_state(s)
  await send_menu(chat_id,f"AUTO ACTIVADO {DASH_URL}")
  return {"ok":True}
 if text=="AUTO OFF":
  s["auto"]=False
  save_state(s)
  await send_menu(chat_id,f"AUTO DESACTIVADO {DASH_URL}")
  return {"ok":True}
 if text in ["ESTADO","PORTAFOLIO","BALANCE"]:
  bal=s["virtual_balance"]
  holds=s.get("holdings",{})
  txt=f"PORTAFOLIO V866-B\nSaldo: ${bal:.2f}\nAuto: {s.get('auto',False)}\n\n"
  tot=bal
  for k,v in holds.items():
   p,_=await get_data(k)
   val=v["amount"]*p
   gan=((p-v["entry"])/v["entry"]*100) if v["entry"]>0 else 0
   txt+=f"{k}: {v['amount']:.5f} = ${val:.2f} ({gan:+.1f}%)\n"
   tot+=val
  txt+=f"\nTotal: ${tot:.2f}\n{DASH_URL}"
  save_state(s)
  await send_menu(chat_id,txt)
  return {"ok":True}
 save_state(s)
 if text in MONEDAS:
  p,c=await get_data(text)
  await send_msg(chat_id,f"{text}: ${p:,.2f} ({c:+.2f}%) Bal ${s['virtual_balance']:.2f}",text,True)
 else:
  await send_menu(chat_id,f"V866-B Bal ${s['virtual_balance']:.2f} {DASH_URL}")
 return {"ok":True}
@app.get("/")
def home():
 return {"V866B":DASH_URL}
