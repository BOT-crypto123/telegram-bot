import os,requests,io,json,time,threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP";E={};O=False;C=0;LC={}
def p(s):
 try:
  a="https://api.coinbase.com/"
  b="v2/prices/"
  c="-USD/spot"
  u=a+b+s+c
  j=requests.get(u,timeout=8).json()
  return float(j["data"]["amount"])
 except:
  return 0
def q(s):
 try:
  a="https://api.exchange.coinbase.com/"
  b="products/"+s
  c="-USD/candles"
  d="?granularity=60"
  u=a+b+c+d
  j=requests.get(u,timeout=10).json()
  return sorted(j)[-60:]
 except:
  return []
def rsi(a):
 if len(a)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  if d>0:
   g+=d
  else:
   l+=-d
 if l==0:
  return 88
 return 100-100/(1+g/l)
def em(a,n):
 if len(a)<n:
  return a[-1]
 k=2/(n+1)
 e=a[0]
 for x in a[1:]:
  e=x*k+e*(1-k)
 return e
def m(x,t):
 k1=[["BTC","ETH"]]
 k1+=[["SOL","XRP"]]
 k2=[["COMPRAR","VENDER"]]
 k2+=[["AUTO"]]
 kb={"keyboard":k1+k2}
 kb["resize_keyboard"]=True
 try:
  a="https://api.telegram.org/bot"
  b=a+T+"/sendMessage"
  requests.post(b,json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
 except:
  pass
   def chk():
 while True:
  time.sleep(180)
  if not O or not C:
   continue
  try:
   for y in ["BTC","ETH","SOL","XRP"]:
    z=q(y)
    if not z:
     continue
    v=[c[4] for c in z]
    u=rsi(v)
    w=p(y)
    j=em(v,9)
    k=em(v,21)
    if u<30 and j>k:
     if LC.get(y)!="C":
      LC[y]="C"
      m(C,y+" COMPRA")
    if u>70 and j<k:
     if LC.get(y)!="V":
      LC[y]="V"
      m(C,y+" VENTA")
    if u>=30 and u<=70:
     LC[y]="E"
  except:
   time.sleep(30)
th.Thread(target=chk,daemon=True).start()
@A.route("/")
def h():
 return "V266 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,O,C
 d=request.json or {}
 g=d.get("message",{})
 i=g.get("chat",{}).get("id",0)
 if not i:
  return "ok",200
 t=g.get("text","").upper()
 if "BTC"in t:
  S="BTC"
 if "ETH"in t:
  S="ETH"
 if "SOL"in t:
  S="SOL"
 if "XRP"in t:
  S="XRP"
 if "AUTO"in t:
  O=not O
  C=i
  m(i,"ON" if O else "OFF")
  return "ok",200
 z=q(S)
 v=[c[4] for c in z]
 if not v:
  return "ok",200
 pr=p(S) or v[-1]
 u=rsi(v)
 j=em(v,9)
 k=em(v,21)
 pc=(pr/v[-2]-1)*100 if len(v)>1 else 0
 sg="ESPERA"
 if u<30:
  sg="COMPRA"
 if u>70:
  sg="VENTA"
 pd="LATERAL"
 pb=50
 if u<30:
  pd="SUBIDA"
  pb=92
 if u>70:
  pd="BAJADA"
  pb=85
    if u>=30 and u<50 and j>k:
  pd="SUBIDA"
  pb=85
 if u>50 and j<k:
  pd="BAJADA"
  pb=82
 ms=""
 if "COMPRAR"in t:
  E[S]=pr
  ms="COMPRADO"
 if "VENDER"in t:
  if E.get(S):
   ms="VENDIDO"
   del E[S]
  else:
   ms="NO"
 from PIL import Image,ImageDraw
 mn=min(v)
 mx=max(v)
 if mn==mx:
  mx*=1.001
 im=Image.new("RGB",(800,400),(10,14,21))
 dr=ImageDraw.Draw(im)
 n=0
 for b in z:
  x=10+n*12
  y1=380-(b[1]-mn)/(mx-mn)*350
  y2=380-(b[2]-mn)/(mx-mn)*350
  yt=380-(max(b[3],b[4])-mn)/(mx-mn)*350
  yb=380-(min(b[3],b[4])-mn)/(mx-mn)*350
  co=(0,230,118) if b[4]>=b[3] else (255,61,87)
  dr.line([x,y1,x,y2],fill=co)
  dr.rectangle([x,yt,x+4,yb],fill=co)
  n+=1
 c1=S+" "+str(round(pr,2))
 c2=str(round(pc,2))+" RSI:"+str(round(u,1))
 c3="EMA9:"+str(round(j,2))
 c3=c3+" 21:"+str(round(k,2))
 c4="SENAL:"+sg
 c5="PRED:"+pd
 c4=c4+" ON" if O else c4+" OFF"
 if ms:
  c4=ms+" "+c4
 cp=c1+"\n"+c2+"\n"+c3+"\n"+c4+"\n"+c5
 b=io.BytesIO()
 b.name="g.png"
 im.save(b,"PNG")
 b.seek(0)
 a="https://api.telegram.org/bot"
 b1=a+T+"/sendPhoto"
 k1=[["BTC","ETH"]]
 k1+=[["SOL","XRP"]]
 k2=[["COMPRAR","VENDER"]]
 k2+=[["AUTO"]]
 kb={"keyboard":k1+k2}
 kb["resize_keyboard"]=True
 requests.post(b1,data={"chat_id":i,"caption":cp,"reply_markup":json.dumps(kb)},files={"photo":b},timeout=10)
 return "ok",200
A.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
