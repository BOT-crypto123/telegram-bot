import os,requests,re,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
print("V104 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot_104.json'
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
    if len(prices).__lt__(period):
        return []
    k=2/(period+1)
    ema=[sum(prices[:period])/period]
    for p in prices[period:]:
        ema.append(p*k+ema[-1]*(1-k))
    return ema

def rsi_calc(prices):
    if len(prices).__lt__(15):
        return 50.0
    gains=0.0
    losses=0.0
    for i in range(1,15):
        d=prices[i]-prices[i-1]
        if d.__ge__(0):
            gains+=d
        else:
            losses-=d
    if losses.__eq__(0):
        return 88.0
    if gains.__eq__(0):
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
    return 'V104 LIVE',200

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
        if p_now.__eq__(0) and SEL in ENTS:
            p_now=ENTS[SEL]['entry']
        if 'GRAF' in t:
            from PIL import Image,ImageDraw
            candles=get_candles(SEL)
            closes=[]
            for c in candles:
                closes.append(c[4])
            if len(closes).__eq__(0):
                closes=[p_now]
            p=p_now
            if len(candles).__gt__(0):
                p=closes[-1]
                tmp=price(SEL)
                if tmp.__ne__(0):
                    p=tmp
            ema9=ema_calc(closes,9)
            ema21=ema_calc(closes,21)
            rsi=rsi_calc(closes)
            pred='NEUTRAL'
            senial='ESPERAR'
            score=50
            if len(ema9).__gt__(0) and len(ema21).__gt__(0):
                e9=ema9[-1]
                e21=ema21[-1]
                if p.__gt__(e9) and e9.__gt__(e21):
                    pred='SUBIDA'
                    senial='COMPRA'
                    score=67
                if p.__lt__(e9) and e9.__lt__(e21):
                    pred='BAJADA'
                    senial='VENTA'
                    score=66
                if rsi.__lt__(30):
                    pred='SUBIDA FUERTE'
                    senial='COMPRA FUERTE'
                    score=92
                if rsi.__gt__(70):
                    pred='BAJADA FUERTE'
                    senial='VENTA FUERTE'
                    score=91
            W=900
            H=520
            img=Image.new('RGB',(W,H),(10,14,21))
            dr=ImageDraw.Draw(img)
            mn=p
            mx=p
            for c in candles:
                if c[1].__lt__(mn):
                    mn=c[1]
                if c[2].__gt__(mx):
                    mx=c[2]
            if mn.__eq__(mx):
                mn=mn*0.998
                mx=mx*1.002
            pad=H-100
            idx=0
            for c in candles:
                x=20+idx*14
                low=c[1]
                high=c[2]
                o=c[3]
                cl=c[4]
                y1=H-70-(low-mn)/(mx-mn)*pad
                y2=H-70-(high-mn)/(mx-mn)*pad
                yo=H-70-(o-mn)/(mx-mn)*pad
                yc=H-70-(cl-mn)/(mx-mn)*pad
                y_top=min(yo,yc)
                y_bot=max(yo,yc)
                if y_top.__eq__(y_bot):
                    y_bot=y_top+2
                col=(0,230,118)
                if cl.__lt__(o):
                    col=(255,61,87)
                dr.line([x+3,y1,x+3,y2],fill=col,width=1)
                dr.rectangle([x,y_top,x+6,y_bot],fill=col)
                idx+=1
            hora_mx=(datetime.utcnow()-timedelta(hours=6)).strftime('%I:%M %p')
            txt_head=SEL+' '+
