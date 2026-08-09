import os,requests,io,json,time
import threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP";E={};O=False;C=0
def p(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def q(s):
 try:
  r=requests.get("https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json()
  return sorted(r)[-60:]
 except: return []
def rsi(a):
 if len(a)<15: return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  if d>0: g+=d
  else: l+=-d
 return 100-100/(1+g/l) if l else 88
def em(a,n):
 if len(a)<n: return a[-1]
 k=2/(n+1); e=a[0]
 for x in a[1:]: e=x*k+e*(1-k)
 return e
def m(x,t):
 k={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try: requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":k},timeout=8)
 except: pass
def lp():
 while True:
  time.sleep(300)
  if not O or not C: continue
  try:
   for y in ["BTC","ETH","SOL","XRP"]:
    z=q(y)
    if not z: continue
    v=[b[4] for b in z]
    u=rsi(v); w=p(y)
    j=em(v,9); l=em(v,21)
    if u<30 and j>l and not E.get(y): E[y]=w; m(C,"COMPRO "+y)
    if u>70 and j<l and E.get(y): del E[y]; m(C,"VENDIO "+y)
  except: time.sleep(30)
th.Thread(target=lp,daemon=True).start()
@A.route("/")
def h(): return "V250",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,O,C
 d=request.get_json(force=True,silent=True)or{}
 g=d.get("message",{})
 i=g.get("chat",{}).get("id",0)
 if not i: return "ok",200
 t=g.get("text","").upper()
 if "BTC" in t: S="BTC"
 if "ETH" in t: S="ETH"
 if "SOL" in t: S="SOL"
 if "XRP" in t: S="XRP"
 if "AUTO" in t:
