import os, requests, threading, time, re, io, json
from flask import Flask, request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"; SL=2.0; TP2=2.2; DROP_AUTO=1.0
ENTS={}; FILE="/tmp/bot81.json"
CONFIG={"AUTO":False,"LAST_CID":0}
def load():
    try:
        if os.path.exists(FILE):
            with open(FILE,"r") as f:
                d=json.load(f)
                global ENTS
                ENTS=d.get("ENTS",{}); CONFIG.update(d.get("CONFIG",{}))
    except: pass
def save():
    try:
        with open(FILE,"w") as f: json.dump({"ENTS":ENTS,"CONFIG":CONFIG},f)
    except: pass
load()
def price(s):
    try:
        r=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
        return float(r["data"]["amount"])
    except: return 0
def get_candles(sym,gran=60,n=20):
    try:
        url=f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity={gran}"
