import os,json,requests,threading,time,traceback
from flask import Flask,request
print("V39.6.5 FINAL FIX /start + XRP ALERT")

BOT=os.environ.get("BOT_TOKEN")
if not BOT:
 for k,v in os.environ.items():
  if "TELE" in k and "TOKEN" in k: BOT=v

URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k and "URL" in k: URL=v
 if "UPSTASH" in k and "TOKEN" in k:
  if "REDIS" in k and v!=BOT: TOK=v

KEY="btc-vicente-v36-1-final"
app=Flask(__name__)

@app.route("/")
def home(): return "V39.6.5 FINAL LIVE"

def load():
