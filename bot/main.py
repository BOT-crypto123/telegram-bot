import os,requests,io,json,time
import threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
E={}
ON=False
CID=None
def p(s):
 try:
  r=requests.get(
   "https://api.coinbase.com/v2/prices/"+s+"-USD/spot",
   timeout=8).json()
  return float(r["data"]["amount"])
 except:
  return 0
def c(s):
 try:
  r=requests.get(
   "https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",
   headers={"User-Agent":"M"},timeout=10).json()
  return sorted(r)[-60:]
 except:
  return []
def rsi(a):
 if len(a)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 100-100/(1+g/l) if l else 88
def ema(a,n):
 if len(a)<n:
  return a[-1]
 k=2/(n+1)
 e=a[0]
 for x in a[1:]:
  e=x*k+e*(1-k)
 return e
def s2(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],
  ["COMPRAR","VENDER"],["AUTO"]],
  "resize_keyboard":True}
 try:
  requests.post(
   "https://api.telegram.org/bot"+T+"/sendMessage",
   json={"chat_id":x,"text":t,"reply_markup":kb},
   timeout=10)
 except:
  pass
def lp():
 while True:
  time.sleep(300)
  if not ON or not CID:
   continue
  try:
   for sy in ["BTC","ETH","SOL","XRP"]:
    cl=c(sy)
    if not cl:
     continue
    cs=[]
    for q in cl:
     cs.append(q[4])
    rr=rsi(cs)
    pr=p(sy)
    e9=ema(cs,9)
    e21=ema(cs,21)
    if rr<30 and e9>e21 and not E.get(sy):
     E[sy]=pr
     rr2=str(round(rr,1))
     m="AUTO COMPRO "+sy+" RSI "+rr2
     s2(CID,m)
    if rr>70 and e9<e21 and E.get(sy):
     pf=(pr/E[sy]-1)*100
     pf2=str(round(pf,2))
     m="AUTO VENDIO "+sy+" "+pf2+"%"
     del E[sy]
     s2(CID,m)
  except:
   time.sleep(60)
th.Thread(target=lp,daemon=True).start()
@A.route("/")
def h():
 return "V245 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,ON,CID
 j=request.get_json(force=True,silent=True)or{}
 m=j.get("message",{})
 cid=m.get("chat",{}).get("id",0)
 if not cid:
  return "ok",200
 t=m.get("text","").upper()
 if "BTC" in t:
  S="BTC"
 if "ETH" in t:
