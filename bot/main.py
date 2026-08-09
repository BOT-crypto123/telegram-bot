import os,requests,re,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
print("V101 TOKEN", len(TOKEN))

app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot_101.json'
CONFIG={'AUTO':False,'LAST_CID':0,'LAST_ALERT':''}

def load():
    try:
        if os.path.exists(FILE):
            d=json.load(open(FILE))
            ENTS.update(d.get('ENTS',{}))
            CONFIG.update(d.get('CONFIG',{}))
    except Exception as e:
        print("LOAD",e)

def save():
    try:
        open(FILE,'w').write(json.dumps({'ENTS':ENTS,'CONFIG':CONFIG}))
    except Exception as e:
        print("SAVE",e)

load()

def price(s):
    try:
        u='https://api.coinbase.com/v2/prices/'+s+'-USD/spot'
        r=requests.get(u,timeout=8).json()
        return float(r['data']['amount'])
    except:
        return 0.0

def get_candles(sym):
    try:
        u='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
        r=requests.get(u,headers={'User-Agent':'Mozilla/5.0'},timeout=12).json()
        return sorted(r)[-80:]
    except:
        return []

def ema_calc(prices,period):
    if len(prices) < period:
        return []
    k=2/(period+1)
    ema=[sum(prices[:period])/period]
    for p in prices[period:]:
        ema.append(p*k+ema[-1]*(1-k))
    return ema

def rsi_calc(prices):
    if len(prices) < 15:
        return 50.0
    gains=0.0
    losses=0.0
    for i in range(1,15):
        d=prices[i]-prices[i-1]
        if d >= 0:
            gains+=d
        else:
            losses-=d
    if losses == 0:
        return 88.0
    if gains == 0:
        return 12.0
    rs=gains/losses
    return 100-100/(1+rs)

def send_text(cid,txt):
    try:
        url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
        kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO'],['AUTO ON','AUTO OFF']],'resize_keyboard':True}
        requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
    except Exception as e:
        print("SEND",e)

def analyze(sym):
    candles=get_candles(sym)
    if len(candles) == 0:
        return None
    closes=[]
    for c in candles:
        closes.append(c[4])
    p=price(sym)
    if p == 0:
        p=closes[-1]
    ema9=ema_calc(closes,9)
    ema21=ema_calc(closes,21)
    rsi=rsi_calc(closes)
    if len(ema9) == 0 or len(ema21) == 0:
        return None
    e9=ema9[-1]
    e21=ema21
