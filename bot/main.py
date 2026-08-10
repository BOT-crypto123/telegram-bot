import os, json, httpx, asyncio, time, random
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'

def L():
    try:
        if os.path.exists(F):
            d=json.load(open(F))
            for k in ['b','h','hs','auto','ganancia_total','total_trades','alert_users']:
                if k not in d: d[k]=1000 if k=='b' else {} if k=='h' else [] if k in ('hs','alert_users') else 0 if 'ganancia' in k or 'trades' in k else False
            return d
    except: pass
    return {'b':1000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[]}
def S(s):
    try: json.dump(s, open(F,'w'))
    except: pass

MONTO=50
TP1=1.5
TP2=2.5
TP3=4.0
SL1=-3.0
SL2=-6.0

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD')
            return float(r.json()['USD'])
    except: return 115000

async def CANDLES(sym):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit=120')
            d=r.json()['Data']['Data']
            return [{'t':int(x['time']),'o':float(x['open']),'h':float(x['high']),'l':float(x['low']),'c':float(x['close'])} for x in d if x['close']>0]
    except: return []

def ema(a,n):
    if len(a)<n: return []
    k=2/(n+1); s=sum(a[:n])/n; o=[s]
    for x in a[n:]: o.append(x*k+o[-1]*(1-k))
    return o
def rsi_arr(a):
    if len(a)<15: return [50]*len(a)
    r=[]
    for i in range(len(a)):
        if i<14: r.append(50); continue
        g=l=0
        for j in range(i-13,i+1):
            d=a[j]-a[j-1]
            if d>0: g+=d
            else: l-=d
        r.append(100-100/(1+g/l) if l!=0 else 80)
    return r

def SCORE(candles):
    if len(candles)<60: return 0,"esperando velas"
    cl=[x['c'] for x in candles]
    op=[x['o'] for x in candles]
    e9=ema(cl,9); e21=ema(cl,21); e50=ema(cl,50); rs=rsi_arr(cl)
    if not e9 or not e21: return 0,"sin datos"
    price=cl[-1]; rnow=rs[-1]; rprev=rs[-2]
    sc=0; mot=[]
    if 25<=rnow<=42: sc+=35; mot.append(f"RSI {int(rnow)} ganga")
    elif 42<rnow<=52 and rnow>rprev: sc+=15; mot.append(f"RSI {int(rnow)} subiendo")
    if price>e9[-1]: sc+=15; mot.append(">EMA9")
    if e9[-1]>e21[-1]: sc+=20; mot.append("EMA9>EMA21 ALZA")
    if cl[-1]>op[-1] and cl[-2]<op[-2]: sc+=15; mot.append("Rebote vela")
    if abs(price-e50[-1])/price<0.02: sc+=15; mot.append("Soporte EMA50")
    if rnow<20: sc-=30; mot.append("Cuchillo")
    return max(0,min(100,sc)), ", ".join(mot)

async def ANALIZA(sym):
    cs=await CANDLES(sym)
    pr=await P(sym)
    if not cs or len(cs)<60:
        now=int(time.time()); prb=pr*0.97
        cs=[{'t':now-i*3600,'o':prb,'h':prb*1.01,'l':prb*0.99,'c':prb} for i in range(60)]
        cs[-1]['c']=pr
    else: cs[-1]['c']=pr
    sc,mo=SCORE(cs)
    cl=[x['c'] for x in cs]
    return {'p':pr,'score':sc,'mot':mo,'cl':cl,'e9':ema(cl,9),'e21':ema(cl,21),'e50':ema(cl,50),'rsi':rsi_arr(cl)[-1]}

def BUY(s,sym,price):
    if s['b']<MONTO: return False,"Sin saldo"
    if sym not in s['h']:
        s['h'][sym]={'a':(MONTO/17.5*0.998)/price,'e':price,'half':False,'entries':1,'tp1':False}
    else:
        # piramidacion - promedia
        extra_a=(MONTO/17.5*0.998)/price
        total_a=s['h'][sym]['a']+extra_a
        avg_e=(s['h'][sym]['e']*s['h'][sym]['a'] + price*extra_a)/total_a
        s['h'][sym]['a']=total_a; s['h'][sym]['e']=avg_e; s['h'][sym]['entries']+=1
    s['b']-=MONTO
    return True,f"COMPRADO {sym} ${price:.2f} Entrada #{s['h'][sym]['entries']}"

def SELL(s,sym,price,pct):
    if sym not in s['h']: return False,"No",0
    ent=s['h'][sym]['e']; amt=s['h'][sym]['a']
    chg=(price/ent-1)*100
    sell_amt=amt*pct/100
    rec=sell_amt*price*0.998*17.5
    # ganancia proporcional
    gan=rec - (MONTO*s['h'][sym]['entries']*pct/100)
    s['b']+=rec
    if pct>=99:
        s['total_trades']+=1; s['ganancia_total']+=gan
        s['hs'].insert(0,{'sym':sym,'pct':round(chg,2),'ganancia':round(gan,2),'fecha':time.strftime('%d/%m %H:%M')})
        del s['h'][sym]
    else:
        s['h'][sym]['a']=amt-sell_amt
        if pct==50: s['h'][sym]['half']=True
    return True,f"VENDIDO {pct}% {sym} {round(chg,2)}% ${round(gan,2)}",gan

async def SEND(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt})
        except: pass

async def MAQUINA():
    s=L()
    btc=await ANALIZA('BTC')
    btc_alza= btc['e9'] and btc['e21'] and btc['e9'][-1]>btc['e21'][-1]

    for sym in ['BTC','ETH','SOL','XRP']:
        an=await ANALIZA(sym) if sym!='BTC' else btc
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100
            ent=s['h'][sym]['entries']
            half=s['h'][sym].get('half',False)
            tp1done=s['h'][sym].get('tp1',False)

            if chg>=TP3:
                ok,msg,gan=SELL(s,sym,an['p'],100)
                if ok:
                    S(s)
                    for cid in s['alert_users']: await SEND(cid,f"💰 RUNNER +4% {sym} {round(chg,2)}% VENDIDO TODO\n{msg}\nSaldo ${int(s['b'])} G/P ${round(s['ganancia_total'],2)}")
                    s=L()
            elif chg>=TP2 and tp1done:
                ok,msg,gan=SELL(s,sym,an['p'],60) # vende 60% del resto
                if ok:
                    S(s)
                    for cid in s['alert_users']: await SEND(cid,f"💸 TP2 +2.5% {sym} {msg}\nDejo 20% runner")
                    s=L()
            elif chg>=TP1 and not tp1done:
                ok,msg,gan=SELL(s,sym,an['p'],50) # primera toma
                if ok:
                    s['h'][sym]['tp1']=True; S(s)
                    for cid in s['alert_users']: await SEND(cid,f"✅ TP1 +1.5% {sym} VENDI 50% ASEGURO\n{msg}\nSaldo ${int(s['b'])}")
                    s=L()
            elif chg<=SL2:
                ok,msg,gan=SELL(s,sym,an['p'],100)
                if ok:
                    S(s)
                    for cid in s['alert_users']: await SEND(cid,f"🛑 SL -6% {sym} FUERA {msg}\nSaldo ${int(s['b'])}")
                    s=L()
            elif chg<=SL1 and not half and ent<3:
                # Si sigue con score alto, promedia en vez de vender, si score bajo vende 50%
                if an['score']>=60 and s['b']>=MONTO:
                    ok,msg=BUY(s,sym,an['p'])
                    if ok:
                        S(s)
                        for cid in s['alert_users']: await SEND(cid,f"🔥 PROMEDIANDO {sym} {round(chg,2)}% SCORE {an['score']} sigue bueno\n{msg}\nAhora entrada avg ${s['h'][sym]['e']:.2f}")
                        s=L()
                elif not half:
                    ok,msg,gan=SELL(s,sym,an['p'],50)
                    if ok:
                        S(s)
                        for cid in s['alert_users']: await SEND(cid,f"⚠️ ANTI-BARRIDO -3% {sym} 50% {msg}")
                        s=L()
        else:
            if an['score']>=75 and btc_alza and s['b']>=MONTO:
                ok,msg=BUY(s,sym,an['p'])
                if ok:
                    S(s)
                    for cid in s['alert_users']: await SEND(cid,f"🚀 MAQUINA ENTRA {sym} SCORE {an['score']}/100\n{an['mot']}\n${an['p']:.2f} RSI {int(an['rsi'])}\n{msg}\nSaldo ${int(s['b'])}")
                    s=L()

@app.get('/check')
async def check(): await MAQUINA(); return {"ok":"V1000 MAQUINA PERRONA"}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    txt=""
    for sym in ['BTC','ETH','SOL','XRP']:
        an=await ANALIZA(sym)
        col="#00ff88" if an['score']>=75 else "#ffaa00" if an['score']>=50 else "#ff4444"
        txt+=f"<div style=border:2px solid {col};padding:10px;margin:6px;border-radius:12px;background:#1a1f30>{sym} ${an['p']:.2f} RSI {int(an['rsi'])}<br>SCORE <b style=color:{col}>{an['score']}</b> {an['mot']}<br>{'🚀 COMPRARIA' if an['score']>=75 else '⏳ ESPERA'}</div>"
    pos="".join([f"<div style=background:#1a1f30;padding:8px;margin:4px;border-radius:8px>{k} x{v['entries']} {round((await P(k)/v['e']-1)*100,2)}% e:{v['e']:.2f}</div>" for k,v in s['h'].items()]) or "Sin posiciones"
    return HTMLResponse(f"<html><body style=background:#0b0e14;color:#fff;font-family:sans-serif;padding:10px><h2>V1000 PERRONA TP 1.5/2.5/4% SL -3/-6%</h2>Saldo ${int(s['b'])} G/P ${round(s['ganancia_total'],2)} Trades {s['total_trades']} AUTO {'ON' if s['auto'] else 'OFF'}<br><br>{txt}<br><h3>Posiciones</h3>{pos}</body></html>")

@app.api_route('/', methods=['GET','POST'])
@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    cid=q.get('message',{}).get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(q.get('message',{}).get('text') or '').upper()
    if 'RESET' in t: S({'b':1000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users']}); await SEND(cid,"RESET V1000 $1000"); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await SEND(cid,f"🔥 MAQUINA PERRONA ON Saldo ${int(s['b'])}"); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await SEND(cid,f"AUTO OFF Saldo ${int(s['b'])}"); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await ANALIZA(t); await SEND(cid,f"{t} SCORE {an['score']}\n{an['mot']}\n${an['p']:.2f}")
        return {'ok':1}
    await SEND(cid,f"V1000 PERRONA\nSaldo ${int(s['b'])} G/P ${round(s['ganancia_total'],2)}\nAUTO ON = maquina entra/sale sola\nSCORE 75+ entra\nTP 1.5/2.5/4% SL -3/-6% con piramidacion")
    return {'ok':1}
