import os,requests,io,json,time,threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP";E={};O=False;C=0;LC={}
def p(s):
 try:
  j=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
  return float(j["data"]["amount"])
 except:return 0
def q(s):
 try:
  j=requests.get(f"https://api.exchange.coinbase.com/products/{s}-USD/candles?granularity=60",timeout=10).json()
  if not isinstance(j,list):return []
  o=[]
  for c in j:
   try:float(c[4]);o.append(c)
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
 k=2.0/(n+1.0)
 e=a[0]
 for x in a[1:]:e=x*k+e*(1-k)
 return e
def m(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try:requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
 except:pass
@A.route("/")
def h():return "V270 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,O,C
 d=request.json or {};g=d.get("message",{});i=g.get("chat",{}).get("id",0)
 if not i:return "ok",200
 t=g.get("text","").upper()
 if "BTC"in t:S="BTC"
 if "ETH"in t:S="ETH"
 if "SOL"in t:S="SOL"
 if "XRP"in t:S="XRP"
 if "AUTO"in t:O=not O;C=i;m(i,"AUTO ON"if O else"AUTO OFF");return "ok",200
 z=q(S)
 if not z:return "ok",200
 v=[]
 for c in z:
  try:v.append(float(c[4]))
  except:continue
 if not v:return "ok",200
 pr=p(S)or v[-1];uu=rsi(v);jj=em(v,9);kk=em(v,21);pc=(pr/v[-2]-1)*100 if len(v)>1 else 0
 sg="COMPRA"if uu<30 else"VENTA"if uu>70 else"ESPERA"
 pd="SUBIDA"if uu<30 or(30<=uu<50 and jj>kk)else"BAJADA"if uu>70 or(uu>50 and jj<kk)else"LATERAL"
 ms=""
 if"COMPRAR"in t:E[S]=pr;ms=f"COMPRADO {pr:.2f}"
 if"VENDER"in t:
  if E.get(S):buy=E[S];prof=(pr-buy)/buy*100;ms=f"VENDIDO {prof:+.2f}%";del E[S]
  else:ms="SIN COMPRA"
 from PIL import Image,ImageDraw
 mn=min(v);mx=max(v)
 if mn==mx:mx=mn+1
 im=Image.new("RGB",(800,400),(10,14,21));dr=ImageDraw.Draw(im);n=0
 for c in z:
  try:
   bf=float(c[4]);bh=float(c[2]);bl=float(c[1]);bo=float(c[3]);x=10+n*12
   y1=380-(bh-mn)/(mx-mn)*350;y2=380-(bl-mn)/(mx-mn)*350;yt=380-(max(bo,bf)-mn)/(mx-mn)*350;yb=380-(min(bo,bf)-mn)/(mx-mn)*350;co=(0,230,118)if bf>=bo else(255,61,87);dr.line([x,y1,x,y2],fill=co);dr.rectangle([x,yt,x+4,yb],fill=co);n+=1
  except:continue
 c1=f"{S} {round(pr,2)}";c2=f"{round(pc,2)}% RSI:{round(uu,1)}";c3=f"EMA9:{round(jj,2)} 21:{round(kk,2)}";c4=f"SENAL:{sg}";c5=f"PRED:{pd} V270"
 if ms:c4=f"{ms} | {c4}"
 cp=c1+"\n"+c2+"\n"+c3+"\n"+c4+"\n"+c5;b=io.BytesIO();b.name="g.png";im.save(b,"PNG");b.seek(0)
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 requests.post("https://api.telegram.org/bot"+T+"/sendPhoto",data={"chat_id":i,"caption":cp,"reply_markup":json.dumps(kb)},files={"photo":b},timeout=10)
 return "ok",200
A.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
