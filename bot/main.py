import os,requests,re,io,json,sys
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
print("V115 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b115.json"

def load():
    if os.path.exists(FILE):
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))

load()
print("V115 LOADED",flush=True)

def price(s):
    u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
    r=requests.get(u,timeout=8).json()
    return float(r.get("data",{}).get("amount","0") or 0)

def candles(sym):
    u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
    r=requests.get(u,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
    if isinstance(r,list):
        return sorted(r)[-60:]
    return []

def ema_calc(prices,period):
    if len
