import os,requests,re,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
print("V102.1 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot_102.json'
CONFIG={'AUTO':False,'LAST_CID':0}

def load():
    try:
        if os.path.exists(FILE):
            d=json.load(open(FILE))
            ENTS.update(d.get('ENTS',{}))
            CONFIG.update(d.get('CONFIG',{}))
    except:
        pass

def save():
    try:
        open(FILE,'w').write(json.dumps({'ENTS':ENTS,'CONFIG':CONFIG}))
    except:
        pass

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
        r=requests.get(u,headers={'User-Agent':'Mozilla/5.0'},timeout=10).json()
        return sorted(r)[-60:]
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
        kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO']],'resize_keyboard':True}
        requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=12)
    except:
        pass

@app.route('/')
def home():
    return 'V102.1 LIVE',200

@app.route('/webhook',methods=['POST'])
def wh():
    global SEL
    try:
        d=request.get_json(force=True,silent=True)
        if not d or 'message' not in d:
            return 'ok',200
        msg=d.get('message')
        cid=msg.get('chat').get('id')
        text_raw=msg.get('text','')
        t=text_raw.upper().strip()
        CONFIG['LAST_CID']=cid
        save()
        for s in ['BTC','ETH','SOL','XRP']:
            if s in t:
                SEL=s
        p_now=price(SEL)
        if p_now == 0 and SEL in ENTS:
            p_now=ENTS[SEL]['entry']
        if 'GRAF' in t:
            from PIL import Image,ImageDraw
            candles=get_candles(SEL)
            closes=[]
            for c in candles:
                closes.append(c[4])
            if len(closes) == 0:
                closes=[p_now]
            p=p_now
            if len(candles) > 0:
                p=closes[-1]
                tmp=price(SEL)
                if tmp!= 0:
                    p=tmp
            ema9=ema_calc(closes,9)
            ema21=ema_calc(closes,21)
            rsi=rsi_calc(closes)
            pred='NEUTRAL'
            senial='ESPERAR'
            score=50
            if len(ema9) > 0
