import os,requests,threading,time,re,io,json
from flask import Flask,request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP";SL=2.0;TP2=2.2;DROP_AUTO=1.0
ENTS={};FILE="/tmp/bot89.json"
CONFIG={"AUTO":False,"LAST_CID":0}
def load():
 try:
  if os.path.exists(FILE):
   with open(FILE,"r") as f:
    d=json.load(f)
    ENTS.update(d.get("ENTS",{}))
    CONFIG.update(d.get("CONFIG",{}))
 except: pass
def save():
 try:
  with open(FILE,"w") as f: json.dump({"ENTS":ENTS,"CONFIG":CONFIG},f)
 except: pass
load()
def price(s):
 try:
  url="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
  r=requests.get(url,timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def get_candles(sym,gran=60,n=20):
 try:
  url="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity="+str(gran)
  r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
  return sorted(r)[-n:]
 except: return []
def send_text(cid,txt):
 try:
  url="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["\U0001f7e2 COMPRAR 100","\U0001f534 VENDER"],["GRAF","PRO"],["\U0001f7e9 AUTO ON","\U0001f7e5 AUTO OFF"]],"resize_keyboard":True}
  requests.post(url,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=15)
 except: pass
def checker():
 last={}
 while True:
  try:
   time.sleep(60)
   for sym in list(ENTS.keys()):
    p=price(sym)
    if p.__lt__(1): continue
    v=ENTS[sym]
    pnl=(p/v["entry"]-1)*100
    if CONFIG.get("AUTO"):
     if pnl.__le__(-SL):
      send_text(v["chat"],"V89 AUTO VENTA SL "+sym)
      del ENTS[sym];save()
     elif pnl.__ge__(TP2):
      send_text(v["chat"],"V89 AUTO VENTA TP "+sym)
      del ENTS[sym];save()
    else:
     if pnl.__le__(-1.5) and last.get(sym)!=p:
      send_text(v["chat
