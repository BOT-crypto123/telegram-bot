import os, time, requests, threading, yfinance as yf
from flask import Flask, jsonify
from datetime import datetime
import pytz
NPOINT_ID="455c95667066c8b158d0"
NPOINT_URL=f"https://api.npoint.io/{NPOINT_ID}"
app=Flask(__name__)
B1=600; B2=850; RSI_BUY=42; TP=1.3; SL=18; MAX=6; RES=1500
MAP={"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
data={"b":5000,"pos":[],"alert_users":[],"auto":True,"gan_total":0,"com_total":0}
prices={}; rsis={"BTC":38,"ETH":42,"SOL":43,"XAUUSD":40,"NVDA":50,"TSLA":50}

def ny_open():
    try:
        ny=datetime.now(pytz.timezone('America/New_York'))
        if ny.weekday()>=5: return False
        return 7.5 <= ny.hour+ny.minute/60 <= 14.0
    except: return False

def puede(s):
    return True if s in ["BTC","ETH","SOL","XAUUSD"] else ny_open()

def get_price(sym):
    try:
        if sym=="XAUUSD":
            try:
                p=yf.Ticker("GC=F").fast_info.last_price
                if p and p>4000: return float(p)
            except: pass
            return 4369.0
        p=yf.Ticker(MAP.get(sym,sym)).fast_info.last_price
        return float(p) if p else 0
    except: return 0

def load():
    global data
    try:
        r=requests.get(NPOINT_URL,timeout=8).json()
        if r.get("b",5000)<3000 and len(r.get("pos",[]))>=4:
            data={"b":5000,"pos":[],"alert_users":r.get("alert_users",[]),"auto":True,"gan_total":0,"com_total":0}; save(); return
        data["b"]=r.get("b",5000); data["pos"]=r.get("pos",[]); data["auto"]=r.get("auto",True)
    except: pass

def save():
    try: requests.post(NPOINT_URL,json=data,timeout=8)
    except: pass

def trading_loop():
    while True:
        try:
            for s in ["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]:
                pr=get_price(s);
                if pr!=0: prices[s]=pr
                else: continue
                for p in data["pos"][:]:
                    if p["sym"]!=s: continue
                    pct=(pr-p["entry"])/p["entry"]*100
