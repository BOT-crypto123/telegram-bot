import os,requests,threading,time
from flask import Flask,request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=5.0;TP=10.0
ENTS={};LAST={};CHATS=set();ABUY={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except:
  return 0
def get_hist(sym):
 try:
  mp={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
  coin=mp.get(sym,"bitcoin")
  url="https://api.coingecko.com/api/v3/coins/"+coin+"/market_chart?vs_currency=usd&days=1"
  r=requests.get(url,timeout=10).json()
  arr=r.get("prices",[])
  out=[]
  for x in arr[-50:]:
   out.append(x[1])
  return out
 except:
  return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except:
  pass
def send_graf(cid,sym,p):
 try:
  hist=get_hist(sym)
  if len(hist)<5:
   hist=[p*0.99,p,p*1.01]
  plt.clf()
  plt.figure(figsize=(4,2))
  plt.plot(hist)
  plt.title(sym+" "+str(round(p,2)))
  plt.tight_layout()
  path="/tmp/g.png"
  plt.savefig(path)
  plt.close()
  u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
  cap=sym+" "+str(round(p,2))+" SL -"+str(SL)+"% TP +"+str(TP)+"%"
  with open(path,"rb") as f:
   requests.post(u,data={"chat_id":cid,"caption":cap},files={"photo":f},timeout=15)
 except:
  send_text(cid,sym+" "+str(round(p,2)))
def checker():
 while True:
  time.sleep(180)
  try:
   for sym in ["BTC","ETH","SOL","XRP"]:
    p=price(sym)
    if p==0:
     continue
    for k in list(ENTS.keys()):
     if k!=
