import os, json, httpx, time, datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'

def L():
    try:
        if os.path.exists(F):
            d = json.load(open(F))
            d.setdefault('b',2000); d.setdefault('h',{}); d.setdefault('hs',[])
            d.setdefault('auto',True); d.setdefault('ganancia_total',0)
            d.setdefault('total_trades',0); d.setdefault('alert_users',[])
            d.setdefault('historial_diario',[]); d.setdefault('ganancia_hoy',0)
            d.setdefault('trades_hoy',0); d.setdefault('fecha_hoy',time.strftime('%Y-%m-%d'))
            d.setdefault('inicial',2000)
            return d
    except: pass
    return {'b':2000,'h':{},'hs':[],'auto':True,'ganancia_total':0,'total_trades':0,'alert_users':[],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000}

def S(s):
    try: json.dump(s, open(F,'w'))
    except: pass

BASE = 50
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']
MAPA = {'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple','DOGE':'dogecoin','AVAX':'avalanche-2','LINK':'chainlink','ADA':'cardano'}

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.coingecko.com/api/v3/simple/price?ids={MAPA[m]}&vs_currencies=usd', headers={"User-Agent":"Mozilla/5.0"})
            return float(r.json()[MAPA[m]]['usd'])
    except:
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD')
                return float(r.json()['USD'])
        except: return 0

async def CANDLES(sym):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit=100', headers={"User-Agent":"Mozilla/5.0"})
            d = r.json()['Data']['Data']
            return [float(x['close']) for x in d if x['close']>0]
    except: return []

def ema(a,n):
    if len(a) < n: return []
    k=2/(n+1); s=sum(a[:n])/n; o=[s]
    for x in a[n:]: o.append(x*k+o[-1]*(1-k))
    return o

def rsi(a):
    if len(a) < 15: return 50
    g=l=0
    for i in range(len(a)-14,len(a)):
        d=a[i]-a[i-1]
        if d>0: g+=d
        else: l-=d
    return 100-100/(1+g/l) if l!=0 else 80

async def SCORE(sym):
    cl = await CANDLES(sym)
    pr = await P(sym)
    if not cl or len(cl) < 50:
        return {'p':pr,'score':50,'rsi':50}
    cl[-1]=pr
    e9=ema(cl,9); e21=ema(cl,21); e50=ema(cl,50)
    r=rsi(cl); sc=0
    if 20 <= r <= 40: sc+=40
    elif 40 < r <= 50: sc+=15
    if e9 and e21 and e9[-1] > e21[-1]: sc+=25
    if e9 and cl[-1] > e9[-1]: sc+=15
    if e50 and abs(cl[-1]-e50[-1])/cl[-1] < 0.025: sc+=20
    if len(cl)>2 and cl[-1]>cl[-2] and cl[-2]<cl[-3]: sc+=10
    return {'p':pr,'score':min(100,sc),'rsi':r}

def monto_dinamico(s):
    if s['ganancia_total']>1000: return 150
    if s['ganancia_total']>500: return 100
    if s['ganancia_total']>200: return 70
    return BASE

def BUY(s,sym,price,monto):
    if s['b'] < monto: return False
    if sym not in s['h']:
        s['h'][sym]={'a':(monto/17.5*0.998)/price,'e':price,'niveles':1,'invertido':monto,'tp1':False,'tp2':False}
    else:
        extra=(monto/17.5*0.998)/price
        total_a=s['h'][sym]['a']+extra
        avg=(s['h'][sym]['e']*s['h'][sym]['a']+price*extra)/total_a
        s['h'][sym]['a']=total_a; s['h'][sym]['e']=avg
        s['h'][sym]['niveles']+=1; s['h'][sym]['invertido']+=monto
    s['b']-=monto; return True

def SELL(s,sym,price,pct):
    if sym not in s['h']: return 0
    amt=s['h'][sym]['a']; inv=s['h'][sym]['invertido']; ent=s['h'][sym]['e']
    sell_amt=amt*pct/100; rec=sell_amt*price*0.998*17.5; gan=rec-inv*pct/100
    s['b']+=rec; s['ganancia_hoy']+=gan
    if pct>=99:
        s['total_trades']+=1; s['trades_hoy']+=1; s['ganancia_total']+=gan
        s['hs'].insert(0,{'sym':sym,'ganancia':round(gan,2),'pct':round((price/ent-1)*100,2),'fecha':time.strftime('%d/%m %H:%M')})
        del s['h'][sym]
    else:
        s['h'][sym]['a']=amt-sell_amt; s['h'][sym]['invertido']=inv*(1-pct/100)
    return gan

async def SEND(cid,txt):
    if not T: return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt})
    except: pass

async def check_fecha(s):
    hoy=time.strftime('%Y-%m-%d')
    if s['fecha_hoy']!=hoy:
        s['historial_diario'].insert(0,{'fecha':s['fecha_hoy'],'ganancia':round(s['ganancia_hoy'],2),'trades':s['trades_hoy']})
        s['historial_diario']=s['historial_diario'][:7]
        s['ganancia_hoy']=0; s['trades_hoy']=0; s['fecha_hoy']=hoy; S(s)
    return s

async def PUTERO():
    s=L(); s=await check_fecha(s)
    btc=await SCORE('BTC'); btc_ok=btc['score']>=35
    for sym in MONEDAS:
        an = await SCORE(sym) if sym!='BTC' else btc
        monto=monto_dinamico(s)
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100; niv=s['h'][sym]['niveles']
            if chg>=3.5:
                g=SELL(s,sym,an['p'],100); S(s)
                for cid in s['alert_users']: await SEND(cid,f"💰💰 PUTERO +3.5% {sym} {round(chg,2)}% GAN ${round(g,2)}\nSaldo ${int(s['b'])}"); s=L()
            elif chg>=2.0 and not s['h'][sym].get('tp2'):
                g=SELL(s,sym,an['p'],40); s['h'][sym]['tp2']=True; S(s)
                for cid in s['alert_users']: await SEND(cid,f"💸 TP2 +2% {sym} 40% ${round(g,2)}"); s=L()
            elif chg>=1.0 and not s['h'][sym].get('tp1'):
                g=SELL(s,sym,an['p'],30); s['h'][sym]['tp1']=True; S(s)
                for cid in s['alert_users']: await SEND(cid,f"✅ TP1 +1% {sym} 30% ${round(g,2)}"); s=L()
            elif chg<=-2.0 and niv==1 and s['b']>=monto and an['score']>=55:
                BUY(s,sym,an['p'],monto); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🔥 PIRAMIDE {sym} {round(chg,2)}% +${monto}"); s=L()
            elif chg<=-4.0 and niv==2 and s['b']>=monto*2:
                BUY(s,sym,an['p'],monto*2); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🔥🔥 PIRAMIDE X2 {sym} +${monto*2}"); s=L()
            elif chg<=-6.0:
                g=SELL(s,sym,an['p'],100); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🛑 SL -6% {sym} ${round(g,2)} Saldo ${int(s['b'])}"); s=L()
        else:
            if an['score']>=70 and btc_ok and s['b']>=monto and len(s['h'])<5:
                BUY(s,sym,an['p'],monto); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🚀 PUTERO ENTRA {sym} SCORE {an['score']} ${an['p']:.2f} Monto ${monto}"); s=L()

async def reporte_diario_logic():
    s=L(); s=await check_fecha(s)
    total=s['b']
    for k,v in s['h'].items():
        pr=await P(k); total+=v['a']*pr*17.5
    gan_total=total-s['inicial']; pct_total=(total/s['inicial']-1)*100 if s['inicial'] else 0
    hist_txt="".join([f"{h['fecha']} {h['ganancia']:+.2f} MXN {h['trades']} trades\n" for h in s['historial_diario'][:6]]) or "Primer dia"
    pos_txt=" ".join([f"{k} {round(((await P(k))/v['e']-1)*100,2)}% " for k,v in s['h'].items()]) or "Ninguna"
    msg=f"""📊 REPORTE DIARIO 10PM - V1002.3 PUTERO DEMO $2000
💰 Saldo: ${int(s['b'])} MXN
📦 En pos: ${int(total-s['b'])} MXN
💵 Total: ${int(total)} MXN
📈 Gan total: ${round(gan_total,2)} MXN ({round(pct_total,2)}%)
🔄 Hoy: ${round(s['ganancia_hoy'],2)} MXN
🎯 Trades Hoy: {s['trades_hoy']}
Pos: {len(s['h'])}/5 {pos_txt}
Dias:
{hist_txt}"""
    for cid in s.get('alert_users',[]): await SEND(cid, msg)
    return msg

@app.get('/')
def home(): return {"status":"V1002.4 MILLONARIO","dashboard":"/dashboard"}

@app.get('/check')
async def check():
    await PUTERO()
    s=L()
    return {"ok":"PUTERO EJECUTADO","saldo":s['b'],"pos":len(s['h']),"gan_hoy":s['ganancia_hoy']}

@app.get('/reporte_diario')
async def reporte_diario():
    msg=await reporte_diario_logic()
    return {"reporte":msg}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    total=s['b']; precios={}; scores={}
    for sym in MONEDAS:
        an=await SCORE(sym); precios[sym]=an['p']; scores[sym]=an
        if sym in s['h']: total+=s['h'][sym]['a']*an['p']*17.5
    gan_total=total-s['inicial']; pct_total=(total/s['inicial']-1)*100 if s['inicial'] else 0
    coins_html=""
    for sym in MONEDAS:
        an=scores[sym]; sc=an['score']
        if sc>=70: col="#00ff88"; lbl="BUY"
        elif sc>=50: col="#ffcc00"; lbl="HOLD"
        else: col="#ff4444"; lbl="SELL"
        coins_html+=f"""<div style="background:#11172a;border:1px solid {col};border-radius:16px;padding:12px;display:flex;justify-content:space-between;align-items:center"><div><b>{sym}</b> ${an['p']:.2f}<br><span style=font-size:12px;opacity:0.6>RSI {int(an['rsi'])}</span></div><div style=text-align:right><div style="border:1px solid {col};padding:4px 10px;border-radius:10px">SCORE<br><b style="color:{col};font-size:18px">{sc}</b></div><div style="background:{col};color:#000;font-size:11px;font-weight:800;padding:2px 8px;border-radius:8px;margin-top:4px;text-align:center">{lbl}</div></div></div>"""
    pos_html="".join([f"<div style=background:#1a1f30;margin:4px 0;padding:8px;border-radius:8px>{k} x{v['niveles']} inv ${v['invertido']} {round(((precios.get(k,0))/v['e']-1)*100,2)}%</div>" for k,v in s['h'].items()]) or "Sin pos - esperando SCORE>=70"
    html=f"""<html><head><meta name=viewport content='width=device-width,initial-scale=1'><style>body{{background:#080b14;color:#fff;font-family:system-ui;padding:10px}}.card{{background:#0e1324;border:1px solid #1a2a4a;border-radius:16px;padding:12px}}.header{{background:#0e1324;border:2px solid #00ffcc55;border-radius:20px;padding:12px;display:flex;justify-content:space-between}}</style></head><body>
<div class=header><b style=color:#5dfdcb>V1002.4 PUTERO MILLONARIO</b><div style=background:#ffdd57;color:#000;padding:8px 14px;border-radius:20px;font-weight:900>${int(s['b'])}</div></div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:10px">
<div class=card>Saldo<br><b style=font-size:22px>${int(s['b'])}</b></div><div class=card>Total<br><b style=font-size:22px>${int(total)}</b><br><span style=color:#00ff88>+${int(gan_total)} ({pct_total:.2f}%)</span></div><div class=card>Ganancia<br><b style=font-size:22px;color:#00ff88>+${int(gan_total)}</b></div>
<div class=card>Hoy<br><b>+${int(s['ganancia_hoy'])}</b></div><div class=card>Trades<br><b>{s['total_trades']}</b> • {len(s['h'])} Open</div><div class=card>Auto<br><b style=color:#00ff88>ON</b></div>
</div><div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px">{coins_html}</div>
<div style=margin-top:12px class=card><b>Posiciones abiertas ({len(s['h'])})</b><div style=margin-top:6px>{pos_html}</div></div>
<div style=margin-top:12px><a href='/check' style=color:#00ff88>Forzar Check</a> | <a href='/reporte_diario' style=color:#ffdd57>Forzar Reporte 10PM</a></div>
</body></html>"""
    return HTMLResponse(html)

@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    cid=q.get('message',{}).get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(q.get('message',{}).get('text') or '').upper()
    if 'RESET' in t:
        S({'b':2000,'h':{},'hs':[],'auto':True,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users'],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000})
        await SEND(cid,"♻️ RESET DEMO $2000 - TODO LIMPIO"); return {'ok':1}
    if 'AUTO ON' in t:
        s['auto']=True; S(s); await SEND(cid,"🔥 PUTERO $2000 ON - Reporte 10pm activo"); return {'ok':1}
    if 'AUTO OFF' in t:
        s['auto']=False; S(s); await SEND(cid,"OFF"); return {'ok':1}
    if 'REPORTE' in t:
        msg=await reporte_diario_logic(); await SEND(cid,msg); return {'ok':1}
    await SEND(cid,f"V1002.4 MILLONARIO\nSaldo ${int(s['b'])} Total ${int(sum([v['a']*(await P(k))*17.5 for k,v in s['h'].items()], s['b'])):.0f} G/P ${round(s['ganancia_total'],2)}\nHOY ${round(s['ganancia_hoy'],2)} Trades hoy {s['trades_hoy']}\nComandos: AUTO ON, AUTO OFF, REPORTE, RESET")
    return {'ok':1}
