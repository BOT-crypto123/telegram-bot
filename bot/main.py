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
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except:
  return 0
def c(s):
 try:
  r=requests.get("https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json()
  return sorted(r)[-60:]
 except:
  return []
def rsi(a):
 if len(a)<15: return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  if d>0: g+=d
  else: l+=-d
 return 100-100/(1+g/l) if l else 88
def ema(a,n):
 if len(a)<n: return a[-1]
 k=2/(n+1); e=a[0]
 for x in a[1:]: e=x*k+e*(1-k)
 return e
def s2(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try: requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":kb},timeout=10)
 except: pass
def lp():
 while True:
  time.sleep(300)
  if not ON or not CID: continue
  try:
   for sy in ["BTC","ETH","SOL","XRP"]:
    cl=c(sy)
    if not cl: continue
    cs=[q[4] for q in cl]
    rr=rsi(cs); pr=p(sy)
    e9=ema(cs,9); e21=ema(cs,21)
    if rr<30 and e9>e21 and not E.get(sy):
     E[sy]=pr; s2(CID,"AUTO COMPRO "+sy+" RSI "+str(round(rr,1)))
    if rr>70 and e9<e21 and E.get(sy):
     pf=(pr/E[sy]-1)*100; del E[sy]; s2(CID,"AUTO VENDIO "+sy+" "+str(round(pf,2))+"%")
  except: time.sleep(60)
th.Thread(target=lp,daemon=True).start()
@A.route("/")
def h(): return "V246 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,ON,CID
 j=request.get_json(force=True,silent=True)or{}
 m=j.get("message",{})
 cid=m.get("chat",{}).get("id",0)
 if not cid: return "ok",200
 t=m.get("text","").upper()
 if "BTC" in t: S="BTC"
 if "ETH" in t: S="ETH"
 if "SOL" in t: S="SOL"
 if "XRP" in t: S="XRP"
 if "AUTO" in t:
  ON=not ON; CID=cid
  s2(cid,"AUTO ON EMA" if ON else "AUTO OFF")
  return "ok",200
 cl=c(S); cs=[q[4] for q in cl]
 if not cs: return "ok",200
 pr=p(S) or cs[-1]; rr=rsi(cs)
 pc=(pr/cs[-2]-1)*100 if len(cs)>1 else 0
 e9=ema(cs,9); e21=ema(cs,21)
 sg="ESPERA"
 if rr<30: sg="COMPRA FUERTE"
 elif rr>70: sg="VENTA FUERTE"
 pred="LATERAL"; prob=50
 if e9>e21 and rr<50:
