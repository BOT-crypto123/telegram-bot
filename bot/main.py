import os,requests,re,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
print("V111 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b111.json"

def load():
    try:
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))
    except:
        pass

def save():
    try:
        open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
    except:
        pass

load()

def price(s):
    try:
        u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
        return float(requests.get(u,timeout=8).json()["data"]["amount"])
    except:
        return 0.0

def candles(sym):
    try:
        u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
        return sorted(requests.get(u,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json())[-60:]
    except:
        return []
