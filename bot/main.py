import os, json, httpx, time, datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'
DASH_URL = os.getenv('DASHBOARD_URL','').strip()

BASE = 50
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']
TOP4 = ['BTC','ETH','SOL','XRP']

def L():
    try:
        if os.path.exists(F):
            d=json.load(open(F))
            if 'b' not in d: d['b']=2000
            if 'h' not in d: d['h']={}
            if 'auto' not in d: d['auto']=False
            if 'ganancia_total' not in d: d['ganancia_total']=0
            if 'total_trades' not in d: d['total_trades']=0
            if 'alert_users' not in d: d['alert_users']=[]
            if 'historial_diario' not in d: d['historial_diario']=[]
            if 'ganancia_hoy' not in d: d['ganancia_hoy']=0
            if 'trades_hoy' not in d: d['trades_hoy']=0
            if 'fecha_hoy' not in d: d['fecha_hoy']=time.strftime('%Y-%m-%d')
            if 'inicial' not in d: d['inicial']=2000
            return d
    except: pass
    return {'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000}

def S(s):
    try: json.dump(s, open(F,'w'))
    except: pass

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD')
            return float(r.json()['USD'])
    except: return 100.0

async def CANDLES_FULL(sym, limit=100):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit={limit}')
            data=r.json()['Data']['Data']
            out=[]
            for x in data:
                if x['close']>0:
                    out.append({'time':int(x['time']),'open':float(x['open']),'high':float(x['high']),'low':float(x['low']),'close':float(x['close'])})
            return out
    except: return []

def ema_calc(a,n):
    if len(a)<n: return [None]*len(a)
    k=2/(n+1); s=sum(a[:n])/n; o=[None]*(n-1)+[s]
    for x in a[n:]: o.append(x*k+o[-1]*(1-k))
    return o
def rsi_calc(a):
    if len(a)<15: return 50
    g=l=0
    for i in range(len(a)-14,len(a)):
        d=a[i]-a[i-1]
        if d>0: g+=d
        else: l-=d
    return 100-100/(1+g/l) if l!=0 else 80

async def SCORE_FULL(sym):
    cl_full=await CANDLES_FULL(sym,100)
    if not cl_full: return {'p':await P(sym),'rsi':50,'score':0,'tend':'LATERAL','senal':'NADA','emas':{}}
    closes=[c['close'] for c in cl_full]
    pr=await P(sym); closes[-1]=pr; cl_full[-1]['close']=pr
    e9=ema_calc(closes,9); e21=ema_calc(closes,21); e50=ema_calc(closes,50)
    r=rsi_calc(closes)
    # tendencia
    if e9[-1] and e21[-1]:
        if e9[-1]>e21[-1] and pr>e9[-1]: tend='SUBE'
        elif e9[-1]<e21[-1] and pr<e9[-1]: tend='BAJA'
        else: tend='LATERAL'
    else: tend='LATERAL'
    sc=0
    if 20<=r<=40: sc+=40
    elif 40<r<=50: sc+=15
    if e9[-1] and e21[-1] and e9[-1]>e21[-1]: sc+=25
    if e9[-1] and pr>e9[-1]: sc+=15
    if e50[-1] and abs(pr-e50[-1])/pr<0.025: sc+=20
    senal='COMPRA' if sc>=70 else 'NADA'
    return {'p':pr,'rsi':int(r),'score':sc,'tend':tend,'senal':senal,'candles':cl_full,'e9':e9,'e21':e21,'e50':e50}

# --- API PARA GRAFICA ---
@app.get('/api/chart/{sym}')
async def api_chart(sym: str):
    sym=sym.upper()
    data=await SCORE_FULL(sym)
    return JSONResponse(data)

# --- DASHBOARD COMO LA CAPTURA ---
@app.get('/dashboard', response_class=HTMLResponse)
async def dash(req: Request):
    sym=req.query_params.get('symbol','BTC').upper()
    if sym not in MONEDAS: sym='BTC'
    s=L()
    total=s['b']
    for k,v in s['h'].items():
        pr=await P(k); total+=v['a']*pr*17.5

    # datos top4
    top_data={}
    for t in TOP4:
        top_data[t]=await SCORE_FULL(t)

    pos_html=""
    for k,v in s['h'].items():
        pr=await P(k)
        chg=(pr/v['e']-1)*100
        col="#00ff88" if chg>=0 else "#ff4444"
        pos_html+=f"<div style=background:#1e253a;margin:6px;padding:10px;border-radius:10px;border-left:4px solid {col}><b>{k}</b> x{v['niveles']} ${v['invertido']} <span style=color:{col}>{chg:+.2f}%</span></div>"
    if not pos_html:
        pos_html="<div style=background:#1e253a;padding:15px;border-radius:12px;text-align:center;opacity:0.7>Sin posiciones abiertas</div>"

    html=f"""
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1"><title>V1003 DASH</title>
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
body{{background:#0e1220;color:#fff;font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:8px}}
.topgrid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}}
.card{{background:#1e253a;border-radius:14px;padding:12px;text-align:center}}
.card b{{color:#3b82f6;font-size:18px}}
.card small{{opacity:0.7;font-size:12px}}
.legend{{display:flex;gap:12px;justify-content:center;font-size:12px;margin:8px 0}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block}}
.btns{{display:flex;gap:8px;justify-content:center;margin:12px 0}}
.btn{{background:#252d4a;border:none;color:#5b8def;padding:8px 16px;border-radius:10px;font-weight:bold}}
.btn.active{{background:#3b82f6;color:#fff}}
#chart{{width:100%;height:420px;background:#0e1220;border-radius:12px}}
.pos-title{{color:#3b82f6;font-weight:bold;margin:15px 0 8px 5px}}
</style></head><body>

<div class=topgrid>
<div class=card><b>${top_data['BTC']['p']:.0f}</b><br><small>BTC<br>RSI {top_data['BTC']['rsi']}<br>{top_data['BTC']['senal']}<br>{top_data['BTC']['tend']}</small></div>
<div class=card><b>${top_data['ETH']['p']:.0f}</b><br><small>ETH<br>RSI {top_data['ETH']['rsi']}<br>{top_data['ETH']['senal']}<br>{top_data['ETH']['tend']}</small></div>
<div class=card><small>SOL</small><br><b>${top_data['SOL']['p']:.0f}</b><br><small>RSI {top_data['SOL']['rsi']}<br>{top_data['SOL']['senal']}<br>{top_data['SOL']['tend']}</small></div>
<div class=card><small>XRP</small><br><b>${top_data['XRP']['p']:.4f}</b><br><small>RSI {top_data['XRP']['rsi']}<br>{top_data['XRP']['senal']}<br>{top_data['XRP']['tend']}</small></div>
</div>

<div class=legend>
<span><span class=dot style=background:#2dd4bf></span> Velas</span>
<span><span class=dot style=background:#facc15></span> EMA9</span>
<span><span class=dot style=background:#f87171></span> EMA21</span>
<span><span class=dot style=background:#4ade80></span> EMA50</span>
</div>

<div id=chart></div>

<div class=btns>
<button class="btn {'active' if sym=='BTC' else ''}" onclick="location.href='/dashboard?symbol=BTC'">BTC</button>
<button class="btn {'active' if sym=='ETH' else ''}" onclick="location.href='/dashboard?symbol=ETH'">ETH</button>
<button class="btn {'active' if sym=='SOL' else ''}" onclick="location.href='/dashboard?symbol=SOL'">SOL</button>
<button class="btn {'active' if sym=='XRP' else ''}" onclick="location.href='/dashboard?symbol=XRP'">XRP</button>
</div>

<div class=pos-title>📦 Posiciones (Telegram = Dashboard)</div>
{pos_html}

<div style=text-align:center;margin:20px;opacity:0.5;font-size:12px>Saldo ${int(s['b'])} | Total ${int(total)} | G/P ${round(total-2000,2)} | HOY ${round(s['ganancia_hoy'],2)}<br>
<a href=/reporte_diario style=color:#3b82f6>Forzar reporte 10pm</a> | <a href=/check style=color:#3b82f6>Check</a></div>

<script>
async function loadChart(sym){{
  const res=await fetch('/api/chart/'+sym);
  const data=await res.json();
  const chartDiv=document.getElementById('chart');
  chartDiv.innerHTML='';
  const chart=LightweightCharts.createChart(chartDiv,{{layout:{{background:{{color:'#0e1220'}},textColor:'#8a8fa8'}},grid:{{vertLines:{{color:'#1e253a'}},horzLines:{{color:'#1e253a'}}}},width:chartDiv.clientWidth,height:420,rightPriceScale:{{borderColor:'#1e253a'}}}});
  const candleSeries=chart.addCandlestickSeries({{upColor:'#2dd4bf',downColor:'#f87171',borderVisible:false,wickUpColor:'#2dd4bf',wickDownColor:'#f87171'}});
  const e9Series=chart.addLineSeries({{color:'#facc15',lineWidth:1}});
  const e21Series=chart.addLineSeries({{color:'#f87171',lineWidth:1}});
  const e50Series=chart.addLineSeries({{color:'#4ade80',lineWidth:1.5}});

  const candles=data.candles.map(c=>({{time:c.time,open:c.open,high:c.high,low:c.low,close:c.close}}));
  candleSeries.setData(candles);

  const e9Data=[]; const e21Data=[]; const e50Data=[];
  for(let i=0;i<data.candles.length;i++){{
    if(data.e9[i]) e9Data.push({{time:data.candles[i].time,value:data.e9[i]}});
    if(data.e21[i]) e21Data.push({{time:data.candles[i].time,value:data.e21[i]}});
    if(data.e50[i]) e50Data.push({{time:data.candles[i].time,value:data.e50[i]}});
  }}
  e9Series.setData(e9Data); e21Series.setData(e21Data); e50Series.setData(e50Data);
  chart.timeScale().fitContent();
}}
loadChart('{sym}');
</script>
</body></html>
"""
    return HTMLResponse(html)

# --- RESTO DEL BOT IGUAL ---
async def SEND(cid,txt, boton_dash=False, teclado=False):
    payload={'chat_id':cid,'text':txt}
    url=DASH_URL if DASH_URL else str(req.base_url)+'dashboard' if 'req' in locals() else "https://tu-app.onrender.com/dashboard"
    if boton_dash:
        payload['reply_markup']={"inline_keyboard":[[{"text":"📊 ABRIR DASHBOARD COMO CAPTURA","url":DASH_URL or url}]]}
    elif teclado:
        payload['reply_markup']={"keyboard":[[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"},{"text":"XRP"}],[{"text":"PORTAFOLIO"},{"text":"📊 Dashboard"}],[{"text":"AUTO ON"},{"text":"AUTO OFF"}]],"resize_keyboard":True}
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.post(B+'/sendMessage',json=payload)
        except: pass

def monto_dinamico(s):
    base=BASE
    if s['ganancia_total']>200: base=70
    if s['ganancia_total']>500: base=100
    if s['ganancia_total']>1000: base=150
    return base
def BUY(s,sym,price,monto):
    if s['b']<monto: return False
    if sym not in s['h']: s['h'][sym]={'a':(monto/17.5*0.998)/price,'e':price,'niveles':1,'invertido':monto,'tp1':False,'tp2':False}
    else:
        extra=(monto/17.5*0.998)/price
        total_a=s['h'][sym]['a']+extra
        avg=(s['h'][sym]['e']*s['h'][sym]['a']+price*extra)/total_a
        s['h'][sym]['a']=total_a; s['h'][sym]['e']=avg; s['h'][sym]['niveles']+=1; s['h'][sym]['invertido']+=monto
    s['b']-=monto
    return True
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
async def check_fecha(s):
    hoy=time.strftime('%Y-%m-%d')
    if s['fecha_hoy']!=hoy:
        s['historial_diario'].insert(0,{'fecha':s['fecha_hoy'],'ganancia':round(s['ganancia_hoy'],2),'trades':s['trades_hoy']})
        s['historial_diario']=s['historial_diario'][:7]; s['ganancia_hoy']=0; s['trades_hoy']=0; s['fecha_hoy']=hoy; S(s)
    return s
async def PUTERO():
    s=L(); s=await check_fecha(s)
    btc=await SCORE_FULL('BTC'); btc_ok=btc['score']>=35
    for sym in MONEDAS:
        an=await SCORE_FULL(sym) if sym!='BTC' else btc
        monto=monto_dinamico(s)
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100; niv=s['h'][sym]['niveles']
            if chg>=3.5:
                g=SELL(s,sym,an['p'],100); S(s)
                for cid in s['alert_users']: await SEND(cid,f"💰💰 PUTERO +3.5% {sym} {round(chg,2)}% GAN ${round(g,2)}", boton_dash=True)
            elif chg>=2.0 and not s['h'][sym].get('tp2'):
                g=SELL(s,sym,an['p'],40); s['h'][sym]['tp2']=True; S(s)
                for cid in s['alert_users']: await SEND(cid,f"💸 TP2 +2% {sym} 40% ${round(g,2)}")
            elif chg>=1.0 and not s['h'][sym].get('tp1'):
                g=SELL(s,sym,an['p'],30); s['h'][sym]['tp1']=True; S(s)
                for cid in s['alert_users']: await SEND(cid,f"✅ TP1 +1% {sym} 30% ${round(g,2)}")
            elif chg<=-2.0 and niv==1 and s['b']>=monto and an['score']>=55:
                BUY(s,sym,an['p'],monto); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🔥 PIRAMIDE {sym} {round(chg,2)}% +${monto}")
            elif chg<=-4.0 and niv==2 and s['b']>=monto*2:
                BUY(s,sym,an['p'],monto*2); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🔥🔥 PIRAMIDE X2 {sym} +${monto*2}")
            elif chg<=-6.0:
                g=SELL(s,sym,an['p'],100); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🛑 SL -6% {sym} ${round(g,2)}", boton_dash=True)
        else:
            if an['score']>=70 and btc_ok and s['b']>=monto and len(s['h'])<5:
                BUY(s,sym,an['p'],monto); S(s)
                for cid in s['alert_users']: await SEND(cid,f"🚀 PUTERO ENTRA {sym} SCORE {an['score']} ${an['p']:.2f}", boton_dash=True)
    now_mx=datetime.datetime.utcnow()-datetime.timedelta(hours=6)
    if now_mx.hour==22 and now_mx.minute<5: await reporte_diario_logic()

async def reporte_diario_logic():
    s=L(); s=await check_fecha(s)
    total=s['b']
    for k,v in s['h'].items():
        pr=await P(k); total+=v['a']*pr*17.5
    gan_total=total-2000
    msg=f"📊 REPORTE 10PM V1003 $2000\n💰 Saldo ${int(s['b'])} Total ${int(total)}\n📈 G/P ${round(gan_total,2)} ({round((total/2000-1)*100,2)}%)\nHOY ${round(s['ganancia_hoy'],2)} Trades {s['trades_hoy']}"
    for cid in s.get('alert_users',[]): await SEND(cid,msg, boton_dash=True)
    return msg

@app.get('/check')
async def check(): await PUTERO(); return {"ok":"V1003"}

@app.get('/reporte_diario')
async def reporte_diario(): msg=await reporte_diario_logic(); return {"reporte":msg}

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
        await SEND(cid,"♻️ RESET $2000", teclado=True); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await SEND(cid,f"🔥 ON Saldo ${int(s['b'])}", teclado=True); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await SEND(cid,"OFF", teclado=True); return {'ok':1}
    if 'REPORTE' in t: await reporte_diario_logic(); return {'ok':1}
    if t in ['📊 DASHBOARD','DASHBOARD']: await SEND(cid,"📊 Dashboard V1003 como tu captura", boton_dash=True); return {'ok':1}
    if t in MONEDAS:
        an=await SCORE_FULL(t)
        await SEND(cid,f"📊 {t} ${an['p']:.2f} RSI {an['rsi']} {an['senal']} {an['tend']} SCORE {an['score']}", boton_dash=True); return {'ok':1}
    if 'PORTAFOLIO' in t:
        total=s['b']
        for k,v in s['h'].items(): pr=await P(k); total+=v['a']*pr*17.5
        await SEND(cid,f"💼 Total ${int(total)} Saldo ${int(s['b'])} G/P ${round(s['ganancia_total'],2)}", boton_dash=True); return {'ok':1}
    await SEND(cid,f"V1003 $2000 Saldo ${int(s['b'])}", teclado=True)
    return {'ok':1}
