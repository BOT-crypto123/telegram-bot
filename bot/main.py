import os,requests,re,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta

TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
print("TOKEN V99.99 LEN", len(TOKEN))

app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot9999.json'
CONFIG={'AUTO':False,'LAST_CID':0,'LAST_ALERT':''}

def load():
    try:
        if os.path.exists(FILE):
            d=json.load(open(FILE))
            ENTS.update(d.get('ENTS',{}))
            CONFIG.update(d.get('CONFIG',{}))
            print("V99.99 LOADED")
    except Exception as e:
        print("LOAD ERR",e)

def save():
    try:
        open(FILE,'w').write(json.dumps({'ENTS':ENTS,'CONFIG':CONFIG}))
    except Exception as e:
        print("SAVE ERR",e)

load()

def price(s):
    try:
        url='https://api.coinbase.com/v2/prices/'+s+'-USD/spot'
        r=requests.get(url,timeout=8).json()
        return float(r['data']['amount'])
    except:
        return 0

def get_candles(sym):
    try:
        url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
        r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=12).json()
        return sorted(r)[-70:]
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
        return 50
    gains=0
    losses=0
    for i in range(1,15):
        d=prices[i]-prices[i-1]
        if d >= 0:
            gains+=d
        else:
            losses-=d
    if losses == 0:
        return 88
    if gains == 0:
        return 12
    rs=gains/losses
    return 100-100/(1+rs)

def send_text(cid,txt):
    try:
        url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
        kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO'],['AUTO ON','AUTO OFF']],'resize_keyboard':True}
        requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
    except Exception as e:
        print("SEND ERR",e)

def analyze(sym):
    candles=get_candles(sym)
    if not candles:
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
    e21=ema21[-1]
    pred='NEUTRAL'
    senial='ESPERAR'
    score=50
    if p > e9 and e9 > e21:
        pred='SUBIDA'
        senial='COMPRA'
        score=67
    if p < e9 and e9 < e21:
        pred='BAJADA'
        senial='VENTA'
        score=66
    if rsi < 35 and p > e9:
        pred='SUBIDA FUERTE'
        senial='COMPRA FUERTE'
        score=89
    if rsi < 30:
        pred='SUBIDA FUERTE'
        senial='COMPRA FUERTE'
        score=92
    if rsi > 65 and p < e9:
        pred='BAJADA FUERTE'
        senial='VENTA FUERTE'
        score=87
    if rsi > 70:
        pred='BAJADA FUERTE'
        senial='VENTA FUERTE'
        score=91
    return {'p':p,'candles':candles,'closes':closes,'ema9':ema9,'ema21':ema21,'rsi':rsi,'pred':pred,'senial':senial,'score':score}

def auto_loop():
    print("V99.99 AUTO LOOP STARTED")
    while True:
        try:
            time.sleep(240)
            if CONFIG.get('AUTO') == False:
                continue
            cid=CONFIG.get('LAST_CID')
            if not cid:
                continue
            for sym in ['BTC','ETH','SOL','XRP']:
                info=analyze(sym)
                if not info:
                    continue
                if 'FUERTE' in info['senial']:
                    key=sym+info['senial']+str(int(info['p']))
                    if CONFIG.get('LAST_ALERT') == key:
                        continue
                    CONFIG['LAST_ALERT']=key
                    save()
                    txt='🚨 ALERTA V99.99 '+sym+' '+info['senial']+'\n'
                    txt=txt+'Precio: $'+str(round(info['p'],2))+'\n'
                    txt=txt+'RSI: '+str(round(info['rsi'],1))+' | SCORE: '+str(info['score'])+'%\n'
                    txt=txt+'EMA9: '+str(round(info['ema9'][-1],2))+' EMA21: '+str(round(info['ema21'][-1],2))+'\n'
                    txt=txt+'Manda: GRAF '+sym
                    send_text(cid,txt)
                    time.sleep(3)
        except Exception as e:
            print("AUTO LOOP ERR",e)
            time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()

@app.route('/')
def home():
    return 'V99.99 GOD MODE LIVE',200

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

        if 'AUTO ON' in t:
            CONFIG['AUTO']=True
            save()
            send_text(cid,'✅ V99.99 AUTO ON - Cada 4 min cazando COMPRA/VENTA FUERTE')
            return 'ok',200
        if 'AUTO OFF' in t:
            CONFIG['AUTO']=False
            save()
            send_text(cid,'⛔ V99.99 AUTO OFF')
            return 'ok',200

        for s in ['BTC','ETH','SOL','XRP']:
            if s in t:
                SEL=s

        p_now=price(SEL)
        if p_now == 0 and SEL in ENTS:
            p_now=ENTS[SEL]['entry']

        if 'GRAF' in t:
            from PIL import Image,ImageDraw
            info=analyze(SEL)
            if not info:
                send_text(cid,'Sin datos '+SEL)
                return 'ok',200
            candles=info['candles']
            closes=info['closes']
            rsi=info['rsi']
            pred=info['pred']
            senial=info['senial']
            score=info['score']
            ema9=info['ema9']
            ema21=info['ema21']
            p=info['p']
            W=900
            H=540
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
            # grid
            for y in [100,220,340,460]:
                dr.line([0,y,W,y],fill='#1a2332',width=1)
            # candles
            idx=0
            for c in candles:
                x=20+idx*12
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
            txt_head=SEL+' $'+str(round(p,4))+' | '+hora_mx
            if SEL in ENTS:
                entry=ENTS[SEL]['entry']
                pnl=(p/entry-1)*100
                sgn='+'
                if pnl < 0:
                    sgn=''
                txt_head=txt_head+' | '+sgn+str(round(pnl,2))+'%'
                ye=H-70-(entry-mn)/(mx-mn)*pad
                dr.line([0,ye,W,ye],fill='#ffea00',width=2)
            dr.rectangle([0,0,W,32],fill='#111827')
            dr.text((12,10),txt_head,fill='white')
            e9v=0
            e21v=0
            if len(ema9) > 0:
                e9v=round(ema9[-1],3)
            if len(ema21) > 0:
                e21v=round(ema21[-1],3)
            cap=txt_head+'\n'
            cap=cap+'EMA9:'+str(e9v)+' EMA21:'+str(e21v)+' RSI:'+str(round(rsi,1))+'\n'
            cap=cap+'PRED: '+pred+' '+str(score)+'% | SENAL: '+senial+'\n'
            cap=cap+'V99.99 GOD MODE'
            bio=io.BytesIO()
            bio.name='v9999.png'
            img.save(bio,'PNG')
            bio.seek(0)
            requests.post('https://api.telegram.org/bot'+TOKEN+'/sendPhoto',data={'chat_id':cid,'caption':cap},files={'photo':bio},timeout=20)
            return 'ok',200

        if 'COMPRAR' in t:
            nums=re.findall(r'[\d\.]+',text_raw)
            m=100.0
            if nums:
                try:
                    m=float(nums[0])
                except:
                    m=100.0
            ENTS[SEL]={'entry':p_now,'usd':m,'time':str(datetime.utcnow())}
            save()
            send_text(cid,'✅ COMPRADA '+SEL+' @ $'+str(round(p_now,2))+' ($'+str(m)+') V99.99')
            return 'ok',200

        if 'VENDER' in t:
            if SEL in ENTS:
                e=ENTS[SEL]['entry']
                usd=ENTS[SEL].get('usd',100)
                pnl=(p_now/e-1)*100
                profit=usd*(pnl/100)
                del ENTS[SEL]
                save()
                sgn='+'
                if pnl < 0:
                    sgn=''
                send_text(cid,'💰 CERRADA '+SEL+' '+sgn+str(round(pnl,2))+'% ($'+sgn+str(round(profit,2))+') V99.99')
            else:
                send_text(cid,'Sin partida '+SEL)
            return 'ok',200

        if 'PRO' in t:
            if not ENTS:
                send_text(cid,'Sin partidas V99.99')
            else:
                out='📊 PORTAFOLIO V99.99\n\n'
                total=0
                for k,v in ENTS.items():
                    pp=price(k)
                    if pp == 0:
                        pp=v['entry']
                    pnl=(pp/v['entry']-1)*100
                    usd=v.get('usd',100)
                    profit=usd*(pnl/100)
                    total+=profit
                    sgn='+'
                    if pnl
