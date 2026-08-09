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
 return 65138.0,0.0
async def send_msg(chat_id,text,moneda="BTC",btns=False):
 kb={"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}],[{"text":f"COMPRAR {moneda}","callback_data":f"BUY_{moneda}"},{"text":f"VENDER {moneda}","callback_data":f"SELL_{moneda}"}]]} if btns else {"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}]]}
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown","reply_markup":kb})
async def send_menu(chat_id,text):
 kb={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"},{"text":"ESTADO"}],[{"text":"AUTO ON"},{"text":"AUTO OFF"}]],"resize_keyboard":True}
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown","reply_markup":kb})
async def cq_answer(id,txt):
 async with httpx.AsyncClient(timeout=10) as c:
  await c.post(f"{BASE}/answerCallbackQuery",json={"callback_query_id":id,"text":txt})
@app.get("/dashboard",response_class
