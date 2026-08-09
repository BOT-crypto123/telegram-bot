import os,requests,io
from flask import Flask,request
from datetime import datetime,timedelta
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
def p(s):
 r=requests.get(
  "https://api.coinbase.com/v2/prices/"+s+"-USD/spot",
  timeout=8).json()
 return float(r["data"]["amount"])
def c(s):
 r=requests.get(
  "https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",
  headers={"User-Agent":"M"},timeout=10).json()
 return sorted(r)[-60:]
def rsi(a):
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 100-100/(1+g/l) if l else 88
@A.route("/")
def h():
 return "V237 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S
 d=request.get_json(force=True,silent=True)or{}
 m=d.get("message",{})
 cid=m["chat"]["id"]
 t=m.get("text","").upper()
 if "BTC" in t:
  S="BTC"
 if "ETH" in t:
  S="ETH"
 if "SOL" in t:
  S="SOL"
 if "XRP" in t:
  S="XRP"
 cl=c(S)
 cs=[]
 for q in cl:
  cs.append(q[4])
 pr=p(S)
 rr=rsi(cs)
 pc=(pr/cs[-2]-1)*100
 sg="ESPERA"
 if rr<30:
  sg="COMPRA FUERTE"
 elif rr>70:
  sg="VENTA FUERTE"
 elif rr<45:
  sg="COMPRA"
 elif rr>55:
  sg="VENTA"
 from PIL import Image,ImageDraw
 mn=min(cs)
 mx=max(cs)
 im=Image.new("RGB",(800,400),(10,14,21))
 dr=ImageDraw.Draw(im)
 i=0
 for x in cl:
  xx=10+i*12
  y1=380-(x[1]-mn)/(mx-mn)*350
  y2=380-(x[2]-mn)/(mx-mn)*350
  yt=380-(max(x[3],x[4])-mn)/(mx-mn)*350
  yb=380-(min(x[3],x[4])-mn)/(mx-mn)*350
  co=(0,230,118) if x[4]>=x[3] else (255,61,87)
  dr.line([xx,y1,xx,y2],fill=co)
  dr.rectangle([xx,yt,xx+4,yb],fill=co)
  i+=1
 hr=(datetime.utcnow()-timedelta(hours=
