import os,requests,re,io,json
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
print("V102 TOKEN", len(TOKEN), flush=True)

app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot_102.json'
CONFIG={'AUTO':False,'LAST_CID':0}

def load():
    try:
        if os.path.exists(FILE):
            import json as js
            d=js.load(open(FILE))
            ENTS.update(d.get('ENTS',{}))
            CONFIG.update(d.get('CONFIG',{}))
    except:
        pass

def save():
    try:
        import json as js
        open(FILE,'w').write(js.dumps({'ENTS':ENTS,'CONFIG':CONFIG}))
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
    return 'V102 LIVE',200

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
                if price(SEL)!= 0:
                    p=price(SEL)
            ema9=ema_calc(closes,9)
            ema21=ema_calc(closes,21)
            rsi=rsi_calc(closes)
            pred='NEUTRAL'
            senial='ESPERAR'
            score=50
            if len(ema9) > 0 and len(ema21) > 0:
                e9=ema9[-1]
                e21=ema21[-1]
                if p > e9 and e9 > e21:
                    pred='SUBIDA'
                    senial='COMPRA'
                    score=67
                if p < e9 and e9 < e21:
                    pred='BAJADA'
                    senial='VENTA'
                    score=66
                if rsi < 30:
                    pred='SUBIDA FUERTE'
                    senial='COMPRA FUERTE'
                    score=92
                if rsi > 70:
                    pred='BAJADA FUERTE'
                    senial='VENTA FUERTE'
                    score=91
            W=900
            H=520
            img=Image.new('RGB',(W,H),'#0a0e15')
            dr=ImageDraw.Draw(img)
            mn=p
            mx=p
            for c in candles:
                if c[1] < mn:
                    mn=c[1]
                if c[2] > mx:
                    mx=c[2]
            if mn == mx:
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
                if y_top == y_bot:
                    y_bot=y_top+2
                col='#00e676'
                if cl < o:
                    col='#ff3d57'
                dr.line([x+3,y1,x+3,y2],fill=col,width=1)
                dr.rectangle([x,y_top,x+6,y_bot],fill=col)
                idx+=1
            hora_mx=(datetime.utcnow()-timedelta(hours=6)).strftime('%I:%M %p')
            txt_head=SEL+' '+str(round(p,4))+' '+hora_mx
            if SEL in ENTS:
                entry=ENTS[SEL]['entry']
                pnl=(p/entry-1)*100
                sgn='+'
                if pnl < 0:
                    sgn=''
                txt_head=txt_head+' '+sgn+str(round(pnl,2))+' pct'
            dr.text((12,10),txt_head,fill='white')
            cap=txt_head+' RSI '+str(round(rsi,1))+' PRED '+pred+' SENAL '+senial+' V102'
            bio=io.BytesIO()
            bio.name='g.png'
            img.save(bio,'PNG')
            bio.seek(0)
            requests.post('https://api.telegram.org/bot'+TOKEN+'/sendPhoto',data={'chat_id':cid,'caption':cap},files={'photo':bio},timeout=15)
            return 'ok',200
        if 'COMPRAR' in t:
            nums=re.findall(r'[\d\.]+',text_raw)
            m=100.0
            if len(nums) > 0:
