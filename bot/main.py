import os, json, requests, threading, time
from flask import Flask, request
print("=== V39.6.8 VICENTE FINAL ===")

# DETECTA TU TOKEN AUNQUE SE LLAME TELEG... BOT_TOKEN TELEGRAM_BOT_TOKEN
BOT=""
for k,v in os.environ.items():
    if not v: continue
    v=str(v).strip()
    if v.startswith("8805451290:"): BOT=v; print(f"TOKEN FOUND IN {k}")
    if "BOT" in k.upper() and "TOKEN" in k.upper() and len(v)>20: BOT=v
    if "TELE" in k.upper() and len(v)>20: BOT=v
BOT=BOT.strip()
print(f"BOT FINAL: {BOT[:15]}... LEN:{len(BOT)}")

URL=os.environ.get("UPSTASH_REDIS_REST_URL","")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
for k,v in os.environ.items():
    if "UPSTASH" in k and "URL" in k and "https" in str(v): URL=str(v).strip()
    if "UPSTASH" in k and "TOKEN" in k and "REDIS" in k and "8805" not in str(v): TOK=str(v).strip()
print(f"UPSTASH URL:{bool(URL)} TOK:{bool(TOK)}")

KEY="btc-vicente-v36-1-final"
app=Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return f"V39.6.8 LIVE BOT:{BOT[:6]}... LEN:{len(BOT)} - 1:30AM"

def load():
    try:
        if not URL or not TOK: return {"users":{}}
        r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
        j=r.json().get("result")
        if j: return json.loads(j)
    except Exception as e: print(f"LOAD ERR {e}")
    return {"users":{}}

def save(d):
    try: requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(d)],timeout=10)
    except: pass

def send(cid,txt,btn=None):
    try:
        if not BOT: print("NO BOT TOKEN!"); return
        p={"chat_id":cid,"text":txt,"parse_mode":"Markdown"}
        if btn: p["reply_markup"]=json.dumps({"inline_keyboard":btn})
        r=requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",json=p,timeout=10)
        print(f"SEND TO {cid} : {r.text[:100]}")
    except Exception as e: print(f"SEND ERR {e}")

def gp(s):
    try: return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}",timeout=5).json()["price"])
    except: return 0
def get_prices(): 
    return gp("BTCUSDT") or 64293,gp("ETHUSDT") or 1903,gp("XRPUSDT") or 1.03

def get_user(cid):
    db=load();
