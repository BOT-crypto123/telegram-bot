import os,requests,threading,time,io,random,re
from flask import Flask,request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=2.0;TP=2.2;ENTS={};LAST={};HIGHS={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def get_candles(sym):
 try:
  mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT"}
  pair=mp.get(sym,"BTCUSDT")
  url="https://api.binance.com/api/v3/klines?symbol="+pair+"&interval=15m&limit=30"
  r=requests.get(url,timeout=6).json()
  if isinstance(r,list) and len(r)>5:
   out=[]
   for x in r: out.append([float(x[1]),float(x[2]),float(x[3]),float(x[4])])
   return out
  return []
 except: return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except: return
def send_graf(cid,sym,p):
 try
