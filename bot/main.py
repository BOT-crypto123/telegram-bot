import os, json, httpx, time, datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'
DASH_URL = "https://telegram-bot-cijp.onrender.com/dashboard"
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']
BASE = 50

def L():
    try:
        if os.path.exists(F):
            d=json.load(open(F))
            d.setdefault('b',2000); d.setdefault('h',{}); d.setdefault('hs',[])
            d.setdefault('auto',False); d.setdefault('ganancia_total',0)
            d.setdefault('total_trades',0); d.setdefault('alert_users',[])
            d.setdefault('historial_diario',[]); d.setdefault('ganancia_hoy',0)
            d.setdefault('trades_hoy',0); d.setdefault('fecha_hoy',time.strftime('%Y-%m-%d'))
            d.setdefault('inicial',2000)
            return d
    except: pass
    return {'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000}

def S(s):
    try: json.dump(s, open(F,'w'))
    except: pass

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.bybit.com/v5/market/tickers?category=spot&symbol={m}USDT')
            price=float(r.json()['result']['list'][0]['lastPrice'])
            if price>0: return price
    except: pass
    try:
        ids={'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple','DOGE':'dogecoin','AVAX':'avalanche-2','LINK':'chainlink','ADA':'cardano'}
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.coingecko.com/api/v3/simple/price?ids={ids[m]}&vs_currencies=usd')
            return float(r.json()[ids[m]]['usd'])
    except: pass
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.binance.com/api/v3/ticker/price?symbol={m}USDT')
            return float(r.json()['price'])
    except: return 50000.0 if m=='BTC' else 3000.0 if m=='ETH' else 150.0

async def CANDLES(m):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://api.bybit.com/v5/market/kline?category=spot&symbol={m}USDT&interval=60&limit=100')
            data=r.json()['result']['list']
            closes=[float(x[4]) for x in data[::-1]]
            if len(closes)>=50: return closes
    except: pass
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://api.binance.com/api/v3/klines?symbol={m}USDT&interval=1h&limit=100')
            return [float(x[4]) for x in r.json()]
    except: pass
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={m}&tsym=USD&limit=100')
            return [float(x['close']) for x in r.json()['Data']['Data'] if x['close']>0]
    except: return []

def ema(a,n):
    if len(a)<n: return []
    k=2/(n+1); s=sum(a[:n])/n; o=[s]
    for x in a[n:]: o.append(x*k+o[-1]*(1-k))
    return o
def rsi(a):
    if len(a)<15: return 50
    g=l=0
    for i in range(len(a)-14,len(a)):
        d=a[i]-a[i-1]
        g+=d if d>0 else 0; l-=d if d<0 else 0
    return 100-100/(1+g/l) if l!=0 else 70

async def SCORE(sym):
    cl=await CANDLES(sym); pr=await P(sym)
    if not cl or len(cl)<50:
        # Si no hay velas pero si precio, da score medio para no quedarse en 0
        return {'p':pr,'score':50,'rsi':45,'tend':'LATERAL'}
    cl[-1]=pr
    e9=ema(cl,9); e21=ema(cl,21); e50=ema(cl,50); r=rsi(cl)
    sc=0
    if 20<=r<=40: sc+=40
    elif 40<r<=50: sc+=15
    if e9 and e21 and e9[-1]>e21[-1]: sc+=25
    if e9 and cl[-1]>e9[-1]: sc+=15
    if e50 and abs(cl[-1]-e50[-1])/cl[-1]<0.025: sc+=20
    if len(cl)>2 and cl[-1]>cl[-2] and cl[-2]<cl[-3]: sc+=10
    tend="SUBE" if e9 and e21 and e9[-1]>e21[-1] and r>50 else "BAJA" if e9 and e21 and e9[-1]<e21[-1] else "LATERAL"
    return {'p':pr,'score':min(100,sc),'rsi':r,'tend':tend}

def monto_dinamico(s):
    b=BASE
    if s['ganancia_total']>200: b=70
    if s['ganancia_total']>500: b=100
    if s['ganancia_total']>1000: b=150
    return b

def BUY(s,sym,price,monto):
    if s['b']<monto: return False
    if sym not in s['h']: s['h'][sym]={'a':(monto/17.5*0.998)/price,'e':price,'niveles':1,'invertido':monto,'tp1':False,'tp2':False}
    else:
        extra=(monto/17.5*0.998)/price; total_a=s['h'][sym]['a']+extra
        avg=(s['h'][sym]['e']*s['h'][sym]['a']+price*extra)/total_a
        s['h'][sym]['a']=total_a; s['h'][sym]['e']=avg; s['h'][sym]['niveles']+=1; s['h'][sym]['invertido']+=monto
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
    else: s['h'][sym]['a']=amt-sell_amt; s['h'][sym]['invertido']=inv*(1-pct/100)
    return gan

async def SEND(cid,txt, boton_dash=False, teclado=False):
    payload={'chat_id':cid,'text':txt}
    if boton_dash: payload['reply_markup']={"inline_keyboard": [[{"text":"📊 ABRIR DASHBOARD","url":DASH_URL}]]}
    elif teclado: payload['reply_markup']={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"},{"text":"📊 Dashboard"}],[{"text":"AUTO ON"},{"text":"AUTO OFF"}]],"resize_keyboard":True}
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.post(B+'/sendMessage',json=payload)
        except: pass

async def check_fecha(s):
    hoy=time.strftime('%Y-%m-%d')
    if s['fecha_hoy']!=hoy:
        s['historial_diario'].insert(0,{'fecha':s['fecha_hoy'],'ganancia':round(s['ganancia_hoy'],2),'trades':s['trades_hoy']})
        s['historial_diario']=s['historial_diario'][:7]; s['ganancia_hoy']=0; s['trades_hoy']=0; s['fecha_hoy']=hoy; S(s)
    return s

async def PUTERO():
    s=L(); s=await check_fecha(s); btc=await SCORE('BTC'); btc_ok=btc['score']>=35
    for sym in MONEDAS:
        an=await SCORE(sym) if sym!='BTC' else btc; monto=monto_dinamico(s)
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100; niv=s['h'][sym]['niveles']
            if chg>=3.5:
                g=SELL(s,sym,an['p'],100); S(s)
                for cid in s['alert_users']: await SEND(cid,f"💰💰 +3.5% {sym} ${round(g,2)}", boton_dash=True); s=L()
            elif chg>=2.0 and not s['h'][sym].get('tp2'):
                g=SELL(s,sym,an['p'],40); s['h'][sym]['tp2']=True; S(s)
                for cid in s['alert_users']: await SEND(cid,f"💸 TP2 +2% {sym}"); s=L()
            elif chg>=1.0 and not s['h'][sym].get('tp1'):
                g=SELL(s,sym,an['p'],30); s['h'][sym]['tp1']=True; S(s)
                for cid in s['alert_users']: await SEND(cid,f"✅ TP1 +1% {sym}"); s=L()
            elif chg<=-2.0 and niv==1 and s['b']>=monto and an['score']>=55:
                BUY(s,sym,an['p'],monto); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🔥 PIRAMIDE {sym}"); s=L()
            elif chg<=-4.0 and niv==2 and s['b']>=monto*2:
                BUY(s,sym,an['p'],monto*2); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🔥🔥 X2 {sym}"); s=L()
            elif chg<=-6.0:
                g=SELL(s,sym,an['p'],100); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🛑 SL -6% {sym} ${round(g,2)}", boton_dash=True); s=L()
        else:
            if an['score']>=70 and btc_ok and s['b']>=monto and len(s['h'])<5:
                BUY(s,sym,an['p'],monto); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🚀 ENTRA {sym} SCORE {an['score']}", boton_dash=True); s=L()

async def reporte_diario_logic():
    s=L(); s=await check_fecha(s)
    total=s['b']
    for k,v in s['h'].items(): total+=v['a']*(await P(k))*17.5
    msg=f"📊 REPORTE V1004.2 Total ${int(total)} Gan ${round(total-2000,2)} HOY ${round(s['ganancia_hoy'],2)}"
    for cid in s.get('alert_users',[]): await SEND(cid,msg, boton_dash=True)
    return msg

@app.get('/check')
async def check(): await PUTERO(); return {"ok":"V1004.2 FIX BYBIT"}

@app.get('/reporte_diario')
async def reporte_diario(): return {"reporte":await reporte_diario_logic()}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L(); scores={}
    for sym in MONEDAS: scores[sym]=await SCORE(sym)
    total=s['b']
    for k,v in s['h'].items(): total+=v['a']*(scores[k]['p'] if k in scores else await P(k))*17.5
    gan_total=total-2000; pct=(total/2000-1)*100
    def card(sym, full):
        an=scores[sym]; col="#00ff88" if an['score']>=70 else "#ffcc33" if an['score']>=40 else "#ff3b4a"
        bg="#0f2218" if an['score']>=70 else "#221e0a" if an['score']>=40 else "#26101a"
        badge="BUY" if an['score']>=70 else "HOLD" if an['score']>=40 else "SELL"
        return f"""<div style="border:1.5px solid {col};background:{bg};border-radius:18px;padding:12px;display:flex;justify-content:space-between;align-items:center;margin:5px;flex:1 1 160px;box-shadow:0 0 15px {col}22">
        <div><div style="width:40px;height:40px;border-radius:50%;background:{col};color:#000;display:flex;align-items:center;justify-content:center;font-weight:900">{sym[0]}</div><div style="margin-top:6px"><b>{sym}</b><br><small style="opacity:.6">{full} ${an['p']:.2f if an['p']<100 else int(an['p'])}</small></div></div>
        <div style="text-align:center"><div style="background:{col};color:#000;font-weight:900;border-radius:12px;padding:6px 10px">SCORE<br><span style="font-size:20px">{an['score']}</span></div><div style="margin-top:5px;background:{col}33;color:{col};border:1px solid {col};border-radius:12px;padding:2px 8px;font-size:10px;font-weight:700">{badge}</div></div></div>"""
    cards="".join([card("BTC","Bitcoin"),card("ETH","Ethereum"),card("SOL","Solana"),card("XRP","XRP"),card("DOGE","Dogecoin"),card("AVAX","Avalanche"),card("LINK","Chainlink"),card("ADA","Cardano")])
    pos_html=""
    for k,v in s['h'].items():
        pr=scores[k]['p']; chg=(pr/v['e']-1)*100; col="#00ff88" if chg>=0 else "#ff3b4a"
        pos_html+=f"<div style='background:#151a2e;border-left:4px solid {col};padding:10px;border-radius:10px;margin-bottom:8px'><b>{k} x{v['niveles']}</b> <span style='color:{col};float:right'>{chg:+.2f}%</span><br><small>Ent {v['e']:.2f} Ahora {pr:.2f}</small><br><b>${round(v['a']*pr*17.5,2)} MXN</b></div>"
    if not pos_html: pos_html="<div style='background:#151a2e;padding:16px;border-radius:12px;text-align:center;opacity:.5'>Sin posiciones<br><small>Esperando SCORE 70+</small></div>"
    hist=""
    for h in s['historial_diario'][:6]:
        c="#00ff88" if h['ganancia']>=0 else "#ff3b4a"
        hist+=f"<div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2340;font-size:13px'><span>{h['fecha']}</span><span style='color:{c}'>{h['ganancia']:+.2f} MXN</span><span>{h['trades']}t</span></div>"
    if not hist: hist="<div style='opacity:.5;font-size:12px'>Primer dia corriendo - historial aparecera aqui</div>"
    last=""
    for t in s['hs'][:5]:
        c="#00ff88" if t['ganancia']>=0 else "#ff3b4a"
        last+=f"<div style='display:flex;justify-content:space-between;font-size:12px;padding:4px 0'><span>{t['fecha']} • {t['sym']} {t['pct']}%</span><span style='color:{c}'>{t['ganancia']:+.2f}</span></div>"
    if not last: last="<div style='opacity:.5;font-size:12px'>Sin trades cerrados</div>"
    html=f"""
    <html><head><meta name=viewport content='width=device-width,initial-scale=1'>
    <style>body{{background:#080b14;color:#fff;font-family:system-ui;margin:0;padding:10px}}.header{{border:1.5px solid #00ffcc55;border-radius:20px;padding:12px;background:#0e1324;display:flex;justify-content:space-between;align-items:center}}.top{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:12px 0}}.box{{background:#0f1326;border:1px solid #1e2a5a;border-radius:18px;padding:14px}}.big{{font-size:26px;font-weight:900}}.g{{color:#00ff88}}.grid{{display:flex;flex-wrap:wrap}}</style></head><body>
    <div class=header><div style='display:flex;align-items:center;gap:8px'><div style='width:44px;height:44px;border:2px solid #00ffcc;border-radius:50%;display:flex;align-items:center;justify-content:center'>◍</div><b style='color:#5dfdcb'>V1004.2 FIX</b></div><div style='background:#ffdd57;color:#000;padding:6px 12px;border-radius:20px;font-weight:900'>$2000</div></div>
    <div class=top>
      <div class=box><small>💰 Saldo</small><div class=big>${int(s['b'])}</div><small class=g>• 24h</small></div>
      <div class=box><small>📊 Total</small><div class=big>${int(total)}</div><small class=g>↑ +${int(gan_total)} ({pct:.2f}%)</small></div>
      <div class=box><small>📈 Ganancia</small><div class=big style='color:#00ff88'>+${int(gan_total)}</div><small class=g>• +{pct:.2f}%</small></div>
      <div class=box><small>📅 Hoy</small><div class=big style='color:{'#00ff88' if s['ganancia_hoy']>=0 else '#ff3b4a'}'>+${round(s['ganancia_hoy'],0)}</div><small>• {time.strftime('%H:%M')}</small></div>
      <div class=box><small>🎯 Trades</small><div class=big>{s['total_trades']+len(s['h'])}</div><small>• {s['total_trades']} Win</small></div>
      <div class=box><small>🤖 Auto</small><div class=big style='color:#00ff88'>{'ON' if s['auto'] else 'OFF'}</div><small class=g>• Bot</small></div>
    </div>
    <div style='display:flex;justify-content:space-between;margin:10px 0'><b style='color:#5dfdcb'>MONEDAS</b><small style='opacity:.5'>SCORE 0-100 BYBIT</small></div>
    <div class=grid>{cards}</div>
    <div style='display:flex;gap:10px;margin-top:14px;flex-wrap:wrap'>
      <div style='flex:1 1 300px' class=box><b>Posiciones abiertas</b> • ({len(s['h'])})<div style='margin-top:10px'>{pos_html}</div></div>
      <div style='flex:1 1 300px' class=box><b>Historial 7 dias</b><div style='height:60px;background:#0a1022;border-radius:8px;margin:10px 0'><svg width='100%' height='60'><polyline fill='none' stroke='#00ffcc' stroke-width='1.5' points='0,45 15,38 30,40 45,28 60,25 75,15 90,10 100,5'/></svg></div>{hist}<div style='margin-top:10px;border-top:1px solid #1a2340;padding-top:8px'><small style='opacity:.6'>Ultimos trades</small>{last}</div></div>
    </div>
    <div style='display:flex;gap:8px;margin:15px 0'><a href='/check' style='flex:1;background:#1a2a4a;color:#4df0ff;text-align:center;padding:12px;border-radius:12px;text-decoration:none'>🔄 Check</a><a href='/reporte_diario' style='flex:1;background:#00ff88;color:#000;text-align:center;padding:12px;border-radius:12px;text-decoration:none;font-weight:900'>📊 Reporte</a></div>
    </body></html>
    """
    return HTMLResponse(html)

@app.api_route('/', methods=['GET','POST'])
@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    cid=q.get('message',{}).get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(q.get('message',{}).get('text') or '').upper().strip()
    if 'RESET' in t:
        S({'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users'],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000})
        await SEND(cid,"♻️ RESET $2000 FIX", teclado=True); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await SEND(cid,f"🔥 FIX ON Saldo ${int(s['b'])}", teclado=True); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await SEND(cid,"⏸️ OFF", teclado=True); return {'ok':1}
    if 'DASHBOARD' in t or 'DASH' in t:
        total=s['b']
        for k,v in s['h'].items(): total+=v['a']*(await P(k))*17.5
        await SEND(cid,f"📊 V1004.2 FIX Total ${int(total)}", boton_dash=True); return {'ok':1}
    if t in MONEDAS:
        an=await SCORE(t); estado="🚀 ENTRARIA" if an['score']>=70 else "⏳ ESPERA" if an['score']>=40 else "❌ NADA"
        await SEND(cid,f"📊 {t} ${an['p']:.2f}\nSCORE {an['score']} RSI {int(an['rsi'])} {an['tend']}\n{estado}", boton_dash=True); return {'ok':1}
    if 'PORTAFOLIO' in t:
        total=s['b']
        for k,v in s['h'].items(): total+=v['a']*(await P(k))*17.5
        txt="".join([f"{k}: {round(((await P(k))/v['e']-1)*100,2)}% x{v['niveles']}\n" for k,v in s['h'].items()]) or "Sin posiciones"
        await SEND(cid,f"💼 Total ${int(total)}\n{txt}", boton_dash=True); return {'ok':1}
    await SEND(cid,f"V1004.2 Saldo ${int(s['b'])}", teclado=True)
    return {'ok':1}
