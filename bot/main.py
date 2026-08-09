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
    r2=await c.get(f"https://api.coingecko.com/api/v3/simple/price?ids={m.get(sym,'bitcoin')}&vs_currencies=usd",headers={"User-Agent":"Mozilla/5.0"})
    return float(r2.json()[m.get(sym,"bitcoin")]["usd"]),0.0
   except:
    pass
 except:
  pass
 return 110000.0,1.0
async def send_msg(chat_id,text,moneda="BTC",btns=False):
 kb={"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}],[{"text":f"COMPRAR {moneda}","callback_data":f"BUY_{moneda}"},{"text":f"VENDER {moneda}","callback_data":f"SELL_{moneda}"}]]} if btns else {"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}]]}
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown","reply_markup":kb})
async def send_menu(chat_id,text):
 kb={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"AUTO ON"},{"text":"AUTO OFF"}],[{"text":"ESTADO"},{"text":"PORTAFOLIO"}]],"resize_keyboard":True}
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown","reply_markup":kb})
async def cq_answer(id,txt):
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/answerCallbackQuery",json={"callback_query_id":id,"text":txt})
@app.get("/dashboard",response_class=HTMLResponse)
async def dashboard():
 s=load_state()
 rows="".join([f"<tr><td>{h['fecha']}</td><td>{h['tipo']} {h['moneda']}</td><td>{h['precio']}</td><td>{h['monto']:.2f}</td></tr>" for h in reversed(s.get("trade_history",[])[-20:])])
 return f"<html><body style='background:#111;color:#fff;padding:20px'><h1>V865 COINBASE FIX</h1><p>Saldo {s.get('virtual_balance',0):.2f}</p><table border=1>{rows}</table></body></html>"
@app.post("/webhook")
async def webhook(req: Request):
 data=await req.json()
 if "callback_query" in data:
  cq=data["callback_query"];chat_id=cq["message"]["chat"]["id"];accion,moneda=cq["data"].split("_");s=load_state();price,_=await get_data(moneda);await cq_answer(cq["id"],f"{accion} {moneda}")
  if accion=="BUY":
   monto=min(200,s["virtual_balance"]);amount=(monto*0.998)/price if price>0 else 0;s["virtual_balance"]-=monto
   if moneda not in s["holdings"]:
    s["holdings"][moneda]={"amount":0,"entry":price}
   old=s["holdings"][moneda];tot=old["amount"]+amount;avg=(old["amount"]*old["entry"]+amount*price)/tot if tot>0 else price;s["holdings"][moneda]={"amount":tot,"entry":avg};s["trade_history"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":moneda,"tipo":"COMPRA","precio":price,"monto":monto,"ganancia":0});save_state(s);await send_msg(chat_id,f"COMPRA {moneda} {monto:.2f} @ {price:.2f}",moneda,True)
  else:
   hold=s.get("holdings",{}).get(moneda)
   if hold:
    val=hold["amount"]*price*0.998;gan=((price-hold["entry"])/hold["entry"]*100) if hold["entry"]>0 else 0;s["virtual_balance"]+=val;s["trade_history"].append({"fecha":datetime.now().strftime("%d/%m %H:%M"),"moneda":moneda,"tipo":"VENTA","precio":price,"monto":val,"ganancia":gan});del s["holdings"][moneda];save_state(s);await send_msg(chat_id,f"VENTA {moneda} {val:.2f} Gan {gan:.2f}%",moneda)
  return {"ok":True}
 msg=data.get("message",{});chat_id=msg.get("chat",{}).get("id");text=(msg.get("text") or "").upper()
 if not chat_id:
  return {"ok":True}
 s=load_state();s["chat_id"]=chat_id;save_state(s)
 if text in MONEDAS:
  p,c=await get_data(text);await send_msg(chat_id,f"{text}: ${p:,.2f} ({c:+.2f}%) Bal ${s['virtual_balance']:.2f}",text,True)
 else:
  await send_menu(chat_id,f"V865 Bal ${s['virtual_balance']:.2f} {DASH_URL}")
 return {"ok":True}
@app.get("/")
def home():
 return {"V865":DASH_URL}
