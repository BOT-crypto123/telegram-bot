import os,requests,threading,time,io,random,re
from flask import Flask,request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=2.0;TP=2.2;ENTS={};LAST={};HIGHS={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except:
  return 0
def get_candles(sym):
 try:
  mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT"}
  pair=mp.get(sym,"BTCUSDT")
  url="https://api.binance.com/api/v3/klines?symbol="+pair+"&interval=15m&limit=30"
  r=requests.get(url,timeout=6).json()
  if isinstance(r,list) and len(r)>5:
   out=[]
   for x in r:
    out.append([float(x[1]),float(x[2]),float(x[3]),float(x[4])])
   return out
  return []
 except:
  return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except:
  return
def send_graf(cid,sym,p):
 try:
  from PIL import Image, ImageDraw
  candles=get_candles(sym)
  if len(candles)<5:
   candles=[]
   base=p if p>0 else 65000
   for i in range(30):
    o=base*(1+random.uniform(-0.005,0.005))
    c=o*(1+random.uniform(-0.008,0.008))
    h=max(o,c)*(1+random.uniform(0,0.003))
    l=min(o,c)*(1-random.uniform(0,0.003))
    candles.append([o,h,l,c])
    base=c
  W,H=900,480
  img=Image.new("RGB",(W,H),"#0a0a0a")
  d=ImageDraw.Draw(img)
  mn=min([c[2] for c in candles])
  mx=max([c[1] for c in candles])
  entry=ENTS[sym]["entry"] if sym in ENTS else None
  if entry:
   mn=min(mn,entry*0.995)
   mx=max(mx,entry*1.005)
  if mx==mn:
   mx=mn*1.01
  pad=50
  def yf(v):
   return H-pad - (v-mn)/(mx-mn)*(H-pad*2-20)
  step=W//len(candles)
  bw=max(4,step-6)
  for i,c in enumerate(candles):
   o,h,l,cl=c
   x=i*step+bw//2+15
   col="#00ff88" if cl>=o else "#ff3b3b"
   d
