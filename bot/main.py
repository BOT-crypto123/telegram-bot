import os,requests,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv("TELE_TOKEN") or ""
print("V202 TOKEN",len(TOKEN),flush=True)

app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b202.json"

def load():
    if os.path.exists(FILE):
        d=json.load(open(FILE))
        ENTS.update(d.get("ENTS",{}))

load()
print("V202 LOADED",flush=True)

def price(s):
    u="https://api.coinbase.com/v2/prices/"
    u=u+s+"-USD/spot"
    r=requests.get(u,timeout=8).json()
    a=r.get("data",{}).get("amount","0")
    return float(a)

def candles(sym):
    u="https://api.exchange.coinbase.com/"
    u=u+"products/"+sym+"-USD/candles"
    u=u+"?granularity=60"
    h={"User-Agent":"M"}
    r=requests.get(u,headers=h,timeout=10).json()
    if isinstance(r,list):
        r=sorted(r)
        return r[-60:]
    return []

def ema(prices,n):
    if len(prices)<n:
        return []
    k=2/(n+1)
    m=sum(prices[:n])/n
    out=[m]
    for p in prices[n:]:
        out.append(p*k+out[-1]*(1-k))
    return out

def rsi(prices):
    if len(prices)<15:
        return 50
    g=0
    l=0
    for i in range(1,15):
        d=prices[i]-prices[i-1]
        if
