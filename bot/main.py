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
            if 'b' not in d: d['b']=1000
            if 'h' not in d: d['h']={}
            if 'hs' not in d: d['hs']=[]
            if 'auto' not in d: d['auto']=False
            if 'ganancia_total' not in d: d['ganancia_total']=0
            if 'total_trades' not in d: d['total_trades']=0
            if 'alert_users' not in d: d['alert_users']=[]
            for k in d['h']:
                if 'half' not in d['h'][k]: d['h'][k]['half']=False
            return d
    except: pass
    return {'b':1000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[]}

def S(s):
    try: json.dump(s, open(F,'w'))
    except: pass

MONTO = 50
TP = 2.5
SL1 = -3.0
SL2 = -6.0

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD')
            return float(r.json()['USD'])
    except: return {'BTC':115000,'ETH':3450,'SOL':172,'XRP':1.02}.get(m,100)

async def C_FULL(sym):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit=120')
            data=r.json()['Data']['Data']
            return [{'time':int(x['time']),'open':float(x['open']),'high':float(x['high']),'low':float(x['low']),'close':float(x['close'])} for x in data if x['close']>0]
    except: return []

def ema(pr,n):
    if len(pr)<n: return []
    k=2/(n+1); s=sum(pr[:n])/n; o=[s]
    for x in pr[n:]: o.append(x*k+o[-1]*(1-k))
    return o

def rsi_arr(pr, per=14):
    if len(pr)<per+1: return [50]*len(pr)
    rsis=[]
    for i in range(len(pr)):
        if i<per: rsis.append(50); continue
        g=ll=0
        for j in range(i-per+1,i+1):
            d=pr[j]-pr[j-1]
            if d>0: g+=d
            else: ll-=d
        rs = 100 if ll==0 else 100-100/(1+g/ll) if g>0 else 0
        rsis.append(rs)
    return rsis

def predictor(candles):
    # Retorna score 0-100 y motivo
    if len(candles)<60: return 0, "pocas velas"
    closes=[c['close'] for c in candles]
    opens=[c['open'] for c in candles]
    e9=ema(closes,9); e21=ema(closes,21); e50=ema(closes,50)
    rsis=rsi_arr(closes)
    if not e9 or not e21: return 0, "sin emas"

    price=closes[-1]
    rsi_now=rsis[-1]
    rsi_prev=rsis[-2]
    score=0
    motivos=[]

    # 1. RSI en zona buena 25-40 = 30 pts
    if 25 <= rsi_now <= 40:
        score+=30; motivos.append(f"RSI {int(rsi_now)} barato")
    elif 40 < rsi_now <= 50 and rsi_now > rsi_prev:
        score+=15; motivos.append(f"RSI {int(rsi_now)} subiendo")

    # 2. Precio arriba de EMA9 = 20 pts
    if price > e9[-1]:
        score+=20; motivos.append("Precio > EMA9")
    # 3. EMA9 > EMA21 tendencia corta alcista = 20 pts
    if e9[-1] > e21[-1]:
        score+=20; motivos.append("EMA9 > EMA21 SUBE")
    # 4. Cerca de EMA50 soporte = 15 pts (rebote)
    if abs(price - e50[-1])/price < 0.015:
        score+=15; motivos.append("En soporte EMA50 rebote")

    # 5. Vela de rechazo = 15 pts
    if closes[-1] > opens[-1] and closes[-2] < opens[-2]:
        score+=15; motivos.append("Vela verde rebote")

    # FILTRO ANTI-TRAMPA: Si RSI muy bajo <20 no comprar cayendo a cuchillo
    if rsi_now < 22:
        score-=20; motivos.append("Cuchillo cayendo no")

    # FILTRO BTC: si BTC baja, no comprar alt
    return min(100,max(0,score)), ", ".join(motivos)

async def AN(sym):
    candles=await C_FULL(sym)
    p_real=await P(sym)
    if not candles or len(candles)<60: candles=make_candles(p_real,120)
    else: candles[-1]['close']=p_real
    score, motivo = predictor(candles)
    closes=[c['close'] for c in candles]
    e9=ema(closes,9); e21=ema(closes,21); e50=ema(closes,50)
    rsis=rsi_arr(closes)
    return {'p':p_real,'rsi':rsis[-1] if rsis else 50,'score':score,'motivo':motivo,'candles':candles,'e9':e9,'e21':e21,'e50':e50}

def make_candles(base, count=100):
    now=int(time.time()); price=base*0.97; out=[]
    for i in range(count,0,-1):
        price=max(price*(1+random.uniform(-0.01,0.01)), base*0.85)
        if i==1: price=base
        o=price*random.uniform(0.998,1.002)
        out.append({'time':now-i*3600,'open':round(o,4),'high':round(max(o,price)*1.003,4),'low':round(min(o,price)*0.997,4),'close':round(price,4)})
    return out

def do_buy(s, sym, price):
    if sym in s['h']: return False, "Ya tienes"
    if s['b'] < MONTO: return False, "Sin saldo"
    s['h'][sym]={'a':(MONTO/17.5*0.998)/price,'e':price,'half':False}
    s['b']-=MONTO
    return True, f"COMPRADO {sym} ${price:.2f}"

def do_sell(s, sym, price, pct=100):
    if sym not in s['h']: return False, "No tienes", 0
    entry=s['h'][sym]['e']; amount=s['h'][sym]['a']
    chg=(price/entry-1)*100
    if pct==50:
        sell=amount*0.5; rec=sell*price*0.998*17.5
        gan=rec - MONTO*0.5
        s['b']+=rec; s['h'][sym]['a']=amount*0.5; s['h'][sym]['half']=True
        return True, f"VENTA 50% {sym} {round(chg,2)}%", gan
    else:
        rec=amount*price*0.998*17.5
        gan=rec - (MONTO*0.5 if s['h'][sym].get('half') else MONTO)
        s['b']+=rec; s['total_trades']+=1; s['ganancia_total']+=gan
        s['hs'].insert(0,{'sym':sym,'pct':round(chg,2),'ganancia':round(gan,2),'fecha':time.strftime('%d/%m %H:%M')})
        del s['h'][sym]
        return True, f"VENDIDO {sym} {round(chg,2)}% ${round(gan,2)}", gan

async def G(cid, txt):
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt})
        except: pass

async def BRAIN():
    s=L()
    # Checar BTC tendencia general
    btc_an=await AN('BTC')
    btc_tendencia = btc_an['e9'][-1] > btc_an['e21'][-1] if btc_an['e9'] and btc_an['e21'] else True

    for sym in ['BTC','ETH','SOL','XRP']:
        an=await AN(sym) if sym=='BTC' else await AN(sym)
        if not an: continue

        # VENTAS - igual anti-calzones
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100
            half=s['h'][sym].get('half',False)
            if chg>=TP:
                if s.get('auto'):
                    ok,msg,gan=do_sell(s,sym,an['p'],100)
                    if ok:
                        S(s)
                        for cid in s['alert_users']: await G(cid, f"✅ TP +2.5% {sym} {round(chg,2)}% {msg}\nSaldo ${int(s['b'])}")
                        s=L()
            elif chg<=SL2:
                if s.get('auto'):
                    ok,msg,gan=do_sell(s,sym,an['p'],100)
                    if ok:
                        S(s)
                        for cid in s['alert_users']: await G(cid, f"🛑 SL -6% FINAL {sym} {round(chg,2)}% {msg}")
                        s=L()
            elif chg<=SL1 and not half:
                if s.get('auto'):
                    ok,msg,gan=do_sell(s,sym,an['p'],50)
                    if ok:
                        S(s)
                        for cid in s['alert_users']: await G(cid, f"⚠️ ANTI-BARRIDO -3% {sym} vendi 50% {msg}")
                        s=L()
        else:
            # COMPRAS PREDICTOR - solo si score alto
            if an['score']>=70 and btc_tendencia:
                if s.get('auto') and s['b']>=MONTO:
                    ok,msg=do_buy(s,sym,an['p'])
                    if ok:
                        S(s)
                        for cid in s['alert_users']: await G(cid, f"🤖 PREDICTOR COMPRA {sym} SCORE {an['score']}/100\n{an['motivo']}\nPrecio ${an['p']:.2f} RSI {int(an['rsi'])}\n{msg}\nSaldo ${int(s['b'])}")
                        s=L()

@app.get('/check')
async def check(): await BRAIN(); return {"ok":"V953 predictor"}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    rows=""
    for sym in ['BTC','ETH','SOL','XRP']:
        an=await AN(sym)
        color="#00ff88" if an['score']>=70 else "#ffaa00" if an['score']>=50 else "#666"
        rows+=f"<div style=background:#1a1f30;padding:10px;margin:5px;border-radius:10px;border:2px solid {color}>{sym} ${an['p']:.2f} RSI {int(an['rsi'])}<br>SCORE <b style=color:{color}>{an['score']}/100</b><br><small>{an['motivo']}</small><br>{'✅ ENTRADA BUENA' if an['score']>=70 else '⏳ ESPERANDO'}</div>"
    html=f"<html><body style=background:#0b0e14;color:#fff;font-family:sans-serif><div style=padding:10px><h3>V953 PREDICTOR +2.5%/-3%/-6%</h3>Saldo ${int(s['b'])} G/P ${round(s['ganancia_total'],2)} AUTO {'ON' if s['auto'] else 'OFF'}<br><br>{rows}<br><div>Posiciones: {len(s['h'])} Trades: {s['total_trades']}</div></div></body></html>"
    return HTMLResponse(html)

@app.api_route('/', methods=['GET','POST'])
@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    msg=q.get('message',{}); cid=msg.get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(msg.get('text') or '').upper()
    if 'RESET' in t: S({'b':1000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users']}); await G(cid,"RESET V953"); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await G(cid,f"AUTO ON PREDICTOR Saldo ${int(s['b'])}"); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await G(cid,f"AUTO OFF Saldo ${int(s['b'])}"); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        await G(cid,f"{t} ${an['p']:.2f} SCORE {an['score']}/100\n{an['motivo']}\n{'COMPRARIA' if an['score']>=70 else 'NO COMPRAR AUN'}")
        return {'ok':1}
    await G(cid,f"V953 PREDICTOR\nSaldo ${int(s['b'])}\nAUTO ON = entra/sale solo con SCORE >=70\nBTC ETH SOL XRP = ver score")
    return {'ok':1}
