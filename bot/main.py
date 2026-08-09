import os,requests,io,json,time,threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or"";A=Flask(__name__)
S="XRP";E={};O=False;C=0;LC={}
def p(s):
 try: return float(requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()["data"]["amount"])
 except: return 0
def q(s):
 try: return sorted(requests.get("https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json())[-60:]
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
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try: requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
 except: pass
def chk():
 while True:
  time.sleep(180)
  if not O or not C: continue
  try:
   for y in ["BTC","ETH","SOL","XRP"]:
    z=q(y)
    if not z: continue
    v=[b[4] for b in z]
    u=rsi(v); w=p(y); j=em(v,9); k=em(v,21)
    if u<30 and j>k and LC.get(y)!="C":
     LC[y]="C"; m(C,f"{y} {round(w,2)} COMPRA 92%")
    if u>70 and j<k and LC.get(y)!="V":
     LC[y]="V"; m(C,f"{y} {round(w,2)} VENTA {round(u,1)}")
    if u>=30 and u<=70: LC[y]="E"
  except: time.sleep(30)
th.Thread(target=chk,daemon=True).start()
@A.route("/")
def h(): return "V257 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,O,C
 d=request.get_json(force
