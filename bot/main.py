import os,requests,io,json,time
import threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
E={}
O=False
C=0
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
 k=2/(n+1)
 e=a[0]
 for x in a[1:]:
  e=x*k+e*(1-k)
 return e
def m(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try:
  requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
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
    u=rsi(v)
    w=p(y)
    j=em(v,9)
    l=em(v,21)
    if u<30 and j>l:
     if not E.get(y):
      E[y]=w
      m(C,"COMPRO "+y)
    if u>70 and j<l:
     if E.get(y):
      del E[y]
      m(C,"VENDIO "+y)
  except: time.sleep(30)
th.Thread(target=lp,daemon=True).start()
@A.route("/")
def h(): return "V251",200
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
 if "AUTO" in t: O=not O
 if "AUTO" in t: C=i
 if "AUTO" in t: m(i,"AUTO ON" if O else "AUTO OFF")
 if "AUTO" in t: return "ok",200
 z=q(S)
 v=[b[4] for b in z]
 if not v: return "ok",200
 pr=p(S) or v[-1]
 u=rsi(v)
 j=em(v,9)
 l=em(v,21)
 pc=(pr/v[-2]-1)*100 if len(v)>1 else 0
 sg="ESPERA"
 if u<30: sg="COMPRA"
 if u>70: sg="VENTA"
 pd="LATERAL"
 pb=50
 if j>l: pd="SUBIDA"
 if j>l: pb=65
 if j<l: pd="BAJADA"
 if j<l: pb=65
 if j>l and u<50: pd="SUBIDA FUERTE"
 if j>l and u<50: pb=85
 if j<l and u>50: pd="BAJADA FUERTE"
 if j<l and u>50: pb=82
 if j>l and u<30: pd="SUBIDA FUERTE"
 if j>l and u<30: pb=92
 ms=""
 if "COMPRAR" in t: E[S]=pr
 if "COMPRAR" in t: ms="COMPRADO "+S
 if "VENDER" in t:
  if E.get(S):
   pf=(pr/E[S]-1)*100
   ms="VENDIDO "+str(round(pf,2))+"%"
   del E[S]
  else: ms="NO TIENES"
 from PIL import Image,ImageDraw
 mn=min(v)
 mx=max(v)
 if mn==mx: mx*=1.001
 im=Image.new("RGB",(800,400),(10,14,21))
 dr=ImageDraw.Draw(im)
 k=0
 for b in z:
  x=10+k*12
  y1=380-(b[1]-mn)/(mx-mn)*350
  y2=380-(b[2]-mn)/(mx-mn)*350
  yt=380-(max(b[3],b[4])-mn)/(mx-mn)*350
  yb=380-(min(b[3],b[4])-mn)/(mx-mn)*350
