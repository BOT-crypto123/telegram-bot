import os, requests, threading, time
from flask import Flask, request
TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app = Flask(__name__)
SEL="BTC"; SL=5.0; TP=10.0
ENTS={} # { "BTC": {"entry":64966, "chat":123} }
LAST={} # ultimos precios
CHATS=set()
ALERT_BUY={} # para no spamear

def price(s):
 try:
  r=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0

def send(cid,txt):
 try:
  u=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except: pass

def checker():
 while True:
  time.sleep(180) # cada 3 min
  try:
   for sym in ["BTC","ETH","SOL","XRP"]:
    p=price(sym)
    if p==0: continue
    # ALERTA VENTA si hay partida
    for s,info in list(ENTS.items()):
     if s!=sym: continue
     ent=info["entry"]; cid=info["chat"]
     pnl=(p/ent-1)*100
     if pnl <= -SL:
      send(cid,f"🔴 VENDER {s} {round(p,2)} PnL {round(pnl,2)}% TOCO SL -{SL}%")
      del ENTS[s]
     elif pnl >= TP:
      send(cid,f"🟢 VENDER {s} {round(p,2)} PnL {round(pnl,2)}% TOCO TP +{TP}%")
      del ENTS[s]
    # ALERTA COMPRA si cae >3% en 1h
    if sym in LAST:
     ch=(p/LAST[sym]-1)*100
     if ch <= -3.0:
      if sym not in ALERT_BUY or time.time()-ALERT_BUY[sym]>
