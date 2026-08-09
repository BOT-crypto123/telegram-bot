import os,requests,io,json
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
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try: requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
 except: pass
@A.route("/")
def h(): return "V252 LIVE",200
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
 if "AUTO" in t: m(i,"AUTO ON EMA9/21" if O else "AUTO OFF")
 if "AUTO" in t: return "ok",200
 z=q(S)
 v=[b[4] for b in z]
 if not v: return "ok",200
 pr=p(S) or v[-1]
 u=rsi(v)
 j=em(v,9)
 k=em(v,21)
 pc=(pr/v[-2]-1)*100 if len(v)>1 else 0
 sg="ESPERA"
 if u<30: sg="COMPRA FUERTE"
 if u>70: sg="VENTA FUERTE"
 pd="LATERAL"
 pb=50
 if j>k: pd="SUBIDA"
 if j>k: pb=65
 if j<k: pd="BAJADA"
 if j<k: pb=65
 if j>k and u<50: pd="SUBIDA FUERTE"
 if j>k and u<50: pb=85
 if j<k and u>50: pd="BAJADA FUERTE"
 if j<k and u>50: pb=82
 if j>k and u<30: pd="SUBIDA FUERTE"
 if j>k and u<30: pb=92
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
 st="ON" if O else "OFF"
 c1=S+" "+str(round(pr,4))
 c2=str(round(pc,2))+"% RSI"+str(round(u,1))
 c3=" EMA9"+str(round(j,2))+" 21"+str(round(k,2))
 c4=sg+" AUTO"+st
 c5="PRED "+pd+" "+str(pb)+"% V252"
 if ms: c4=ms+"\n"+c4
 cp=c1+"\n"+c2+c3+"\n"+c4+"\n"+c5
 b=io.BytesIO()
 b.name="g.png"
 im.save(b,"PNG")
 b.seek(0)
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 requests.post("https://api.telegram.org/bot"+T+"/sendPhoto",data={"chat_id":i,"caption":cp,"reply_markup":json.dumps(kb)},files={"photo":b},timeout=10)
 return "ok",200
A.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
