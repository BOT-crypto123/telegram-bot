import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
E={}
ON=False
CID=None
F="/tmp/b.json"
G="/tmp/a.json"
def L():
 global E,ON,CID
 if os.path.exists(F):
  E=json.load(open(F)).get("ENTS",{})
 if os.path.exists(G):
  d=json.load(open(G))
  ON=d.get("ON",0)
  CID=d.get("CID")
L()
def p(s):
 r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
 return float(r.get("data",{}).get("amount","0")or 0)
def c(s):
 r=requests.get("https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json()
 return sorted(r)[-60:] if isinstance(r,list) else []
def ema(a,n):
 if len(a)<n:
  return []
 k=2/(n+1)
 m=sum(a[:n])/n
 o=[m]
 for x in a[n:]:
  o.append(x*k+o[-1]*(1-k))
 return o
def rsi(a):
 if len(a)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
def snd(x,t):
 k={"keyboard":[["BTC","ETH"],["SOL","XRP"],["GRAF","AUTO"]],"resize_keyboard":True}
 requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":k},timeout=10)
def lp():
 while True:
  time.sleep(600)
  if ON and CID:
   for s in ["BTC","ETH","SOL","XRP"]:
    cl=c(s)
    if cl and rsi([a[
