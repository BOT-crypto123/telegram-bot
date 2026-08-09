import os,requests,io,json,time,threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP";E={};O=False;C=0;LC={}
def p(s):
 try:
  u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
  j=requests.get(u,timeout=8).json()
  return float(j["data"]["amount"])
 except:return 0
def q(s):
 try:
  u="https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60"
  j=requests.get(u,timeout=10).json()
  if not isinstance(j,list):return []
  o=[]
  for c in j:
   try:
    if len(c)>=5:
     float(c[4]);o.append(c)
   except:continue
  return sorted(o)[-60:]
 except:return []
def rsi(a):
 if len(a)<15:return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0;l+=-d if d<0 else 0
 return 88 if l==0 else 100-100/(1+g/l)
def em(a,n):
 if len(a)<n:return a[-1]
 k=2/(n+1);e=a[0]
 for x in a[1:]:e=x*k+e*(1-k)
 return e
def m(x,t):
 k1=[["BTC","ETH"]];k1+=[["SOL","XRP"]];k2=[["COMPRAR","VENDER"]];k2+=[["AUTO"]];kb={"keyboard":k1+k2,"resize_keyboard":True}
 try:
  u="https://api.telegram.org/bot"+T+"/sendMessage"
  requests.post(u,json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
 except:pass
def chk():
 while True:
  time.sleep(180)
  if not O or not C:continue
  try:
   for y in ["BTC","ETH","SOL","XRP"]:
    z=q(y)
    if not z:continue
    v=[]
    for c in z:
     try:v.append(float(c[4]))
     except:continue
    if not v:continue
    u=rsi(v);j=em
