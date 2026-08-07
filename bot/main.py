import os,json,requests,threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.4 FIX")
BOT=None
for k,v in os.environ.items():
 if "TELE" in k.upper() and "TOKEN" in k.upper():
  BOT=v
if not BOT:
 BOT=os.environ.get("BOT_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k.upper() and "URL" in k.upper():
  URL=v
 if "UPSTASH" in k.upper() and "TOKEN" in k.upper():
  if "REDIS" in k.upper() and v!=BOT:
   TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home():
 return "V39.4 LIVE"
def load():
 try:
  if not URL or not TOK:
   return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  res=r.json().get("result")
  if res:
   return json.loads(res)
 except:
  pass
 return {"users":{}}
def save(d):
 try:
  requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(d)],timeout=10)
 except:
  pass
def market():
 try:
  b=requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=8).json()
  b=float(b["data"]["amount"])
  e=requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot",timeout=8).json()
  e=float(e["data"]["amount"])
  x=requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot",timeout=8).json()
  x=float(x["data"]["amount"])
  fx=17.22
  try:
   fx=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=
