import os, json, httpx, time, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'

# --- MISMO CODIGO TUYO, NO TOCO LOGICA ---
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
    try:
        os.makedirs(os.path.dirname(F), exist_ok=True)
        json.dump(s, open(F,'w'))
    except: pass

MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']
async def P(m):
    for url in [f'https://api.binance.com/api/v3/ticker/price?symbol={m}USDT',f'https://data-api.binance.vision/api/v3/ticker/price?symbol={m}USDT']:
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(url, headers={"User-Agent":"Mozilla/5.0"})
                if r.status_code==200: return float(r.json()['price'])
        except: continue
    return 0
async def CANDLES(sym):
    for url in [f'https://api.binance.com/api/v3/klines?symbol={sym}USDT&interval=1h&limit=100',f'https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=100']:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url, headers={"User-Agent":"Mozilla/5.0"})
                if r.status_code==200: return [float(x[4]) for x in r.json()]
        except: continue
    return []
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
    cl = await CANDLES(sym); pr = await P(sym)
    if not cl or len(cl) < 50 or pr==0: return {'p':pr,'score':50,'rsi':50,'cl':cl or []}
    cl[-1]=pr; e9=ema(cl,9); e21=ema(cl,21); e50=ema(cl,50); r=rsi(cl); sc=0
    if 20 <= r <= 40: sc+=40
    elif 40 < r <= 50: sc+=15
    if e9 and e21 and e9[-1] > e21[-1]: sc+=25
    if e9 and cl[-1] > e9[-1]: sc+=15
    if e50 and abs(cl[-1]-e50[-1])/cl[-1] < 0.025: sc+=20
    if len(cl)>2 and cl[-1]>cl[-2] and cl[-2]<cl[-3]: sc+=10
    return {'p':pr,'score':min(100,sc),'rsi':r,'cl':cl}
def monto_dinamico(s):
    if s['ganancia_total']>1000: return 150
    if s['ganancia_total']>500: return 100
    if s['ganancia_total']>200: return 70
    return 50
def BUY(s,sym,price,monto):
    if s['b'] < monto: return False
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
async def SEND(cid,txt):
    if not T: return
    try:
        async with httpx.AsyncClient(timeout=10) as c: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt})
    except: pass
async def check_fecha(s):
    hoy=time.strftime('%Y-%m-%d')
    if s['fecha_hoy']!=hoy:
        s['historial_diario'].insert(0,{'fecha':s['fecha_hoy'],'ganancia':round(s['ganancia_hoy'],2),'trades':s['trades_hoy']})
        s['historial_diario']=s['historial_diario'][:7]; s['ganancia_hoy']=0; s['trades_hoy']=0; s['fecha_hoy']=hoy; S(s)
    return s
async def PUTERO():
    s=L(); s=await check_fecha(s)
    if not s['auto']: return s
    btc=await SCORE('BTC'); btc_ok=btc['score']>=35
    for sym in MONEDAS:
        an = await SCORE(sym) if sym!='BTC' else btc
        if an['p']==0: continue
        monto=monto_dinamico(s)
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100; niv=s['h'][sym]['niveles']
            if chg>=3.5: SELL(s,sym,an['p'],100); S(s)
            elif chg>=2.0 and not s['h'][sym].get('tp2'): SELL(s,sym,an['p'],40); s['h'][sym]['tp2']=True; S(s)
            elif chg>=1.0 and not s['h'][sym].get('tp1'): SELL(s,sym,an['p'],30); s['h'][sym]['tp1']=True; S(s)
            elif chg<=-2.0 and niv==1 and s['b']>=monto and an['score']>=55: BUY(s,sym,an['p'],monto); S(s)
            elif chg<=-4.0 and niv==2 and s['b']>=monto*2: BUY(s,sym,an['p'],monto*2); S(s)
            elif chg<=-6.0: SELL(s,sym,an['p'],100); S(s)
        else:
            if an['score']>=70 and btc_ok and s['b']>=monto and len(s['h'])<5: BUY(s,sym,an['p'],monto); S(s)
    return L()
async def reporte_diario_logic():
    s=L(); s=await check_fecha(s)
    total=s['b']
    for k,v in s['h'].items():
        pr=await P(k); total+=v['a']*pr*17.5
    gan_total=total-s['inicial']; pct_total=(total/s['inicial']-1)*100 if s['inicial'] else 0
    hist_txt="".join([f"{h['fecha']} {h['ganancia']:+.2f} MXN {h['trades']} trades\n" for h in s['historial_diario'][:6]]) or "Primer dia"
    pos_txt=" ".join([f"{k} {round(((await P(k))/v['e']-1)*100,2)}% " for k,v in s['h'].items()]) or "Ninguna"
    msg=f"""📊 REPORTE V1002.10 24/7
💰 Saldo: ${int(s['b'])} MXN
💵 Total: ${int(total)} MXN
📈 Gan total: ${round(gan_total,2)} ({round(pct_total,2)}%)
🔄 Hoy: ${round(s['ganancia_hoy'],2)} Trades hoy: {s['trades_hoy']}
Pos: {len(s['h'])}/5 {pos_txt}
Guardado en: {F}
Dias:
{hist_txt}"""
    return msg, s

# --- NUEVO: LOOP INTERNO 24/7 ---
async def loop_24_7():
    print("LOOP 24/7 INICIADO")
    while True:
        try:
            await PUTERO()
            # Reporte automático 22:00 hora México (04:00 UTC)
            now = datetime.datetime.now()
            if now.hour == 4 and now.minute < 3: # 22:00 México = 04:00 UTC
                msg,s = await reporte_diario_logic()
                for cid in s['alert_users']:
                    await SEND(cid, msg)
            await asyncio.sleep(180) # cada 3 minutos solito
        except Exception as e:
            print(f"Error loop: {e}")
            await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(loop_24_7())
    yield

app = FastAPI(lifespan=lifespan)

@app.get('/')
def home(): return {"status":"V1002.10 24/7 AUTO","file":F,"data_exists":os.path.exists(F)}
@app.get('/check')
async def check(): s=await PUTERO(); return {"ok":"check","auto":s['auto'],"file":F}
@app.get('/api/data')
async def api_data():
    out={}
    for sym in MONEDAS: out[sym]=await SCORE(sym)
    s=L(); total=s['b']
    for k,v in s['h'].items():
        if k in out and out[k]['p']: total+=v['a']*out[k]['p']*17.5
    return JSONResponse({"prices":out,"saldo":s['b'],"total":total,"ganancia":total-s['inicial'],"pos":s['h'],"auto":s['auto'],"trades":s['total_trades'],"gan_hoy":s['ganancia_hoy'],"gan_total":s['ganancia_total'],"file":F})
@app.get('/api/toggle')
async def toggle(): s=L(); s['auto']=not s['auto']; S(s); return {"auto":s['auto']}
@app.get('/api/buy/{sym}')
async def api_buy(sym: str):
    sym=sym.upper(); s=L(); pr=await P(sym)
    if pr==0: return JSONResponse({"error":"precio no disponible"},status_code=400)
    monto=monto_dinamico(s)
    if s['b']<monto: return JSONResponse({"error":"sin saldo"},status_code=400)
    BUY(s,sym,pr,monto); S(s); return {"ok":True}
@app.get('/api/sell/{sym}')
async def api_sell(sym: str):
    sym=sym.upper(); s=L()
    if sym not in s['h']: return JSONResponse({"error":"no tienes"},status_code=400)
    pr=await P(sym); SELL(s,sym,pr,100); S(s); return {"ok":True}
@app.get('/api/reporte')
async def api_reporte():
    msg,s=await reporte_diario_logic()
    for cid in s['alert_users']: await SEND(cid, msg)
    return {"reporte":msg}
@app.get('/api/force_check')
async def api_force_check():
    s=await PUTERO()
    return {"ok":True,"saldo":s['b'],"pos":len(s['h']),"file":F}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    return HTMLResponse("""
<html translate="no"><head><meta name=viewport content='width=device-width,initial-scale=1'><meta name="google" content="notranslate">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#080b14;color:#fff;font-family:system-ui;padding:8px;margin:0}
.card{background:#0e1324;border:1px solid #1a2a4a;border-radius:16px;padding:12px}
.header{background:#0e1324;border:2px solid #00ffcc55;border-radius:20px;padding:12px;display:flex;justify-content:space-between;align-items:center}
.coin{background:#11172a;border-radius:16px;padding:10px}
canvas{width:100%!important;height:55px!important}
.btn{border:none;padding:10px 14px;border-radius:12px;font-weight:900;margin:4px}
</style></head><body>
<div class=header><b style=color:#5dfdcb>V1002.10 24/7 AUTO</b><div style=display:flex;gap:6px><div id=saldo style=background:#ffdd57;color:#000;padding:8px 14px;border-radius:20px;font-weight:900>$2000</div><button id=autoBtn onclick="toggle()" class=btn style="background:#00ff88;color:#000">ENCENDIDO</button></div></div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:10px">
<div class=card>Saldo<br><b id=s1>$2000</b></div><div class=card>Total<br><b id=s2>$2000</b><br><span id=s2g style=color:#00ff88>+ $0</span></div><div class=card>Hoy<br><b id=s3>+$0</b><br><span id=s4 style=opacity:0.6>0 trades</span></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:10px">
<button onclick="forceCheck()" class=btn style="background:#00ff88;color:#000">CHECK AHORA</button>
<button onclick="reporte()" class=btn style="background:#5dfdcb;color:#000">REPORTE 22:00</button>
<button onclick="enviarTG()" class=btn style="background:#0088cc;color:#fff">ENVIAR A TG</button>
</div>
<div id=status style=margin-top:8px class=card>Estado: Verificando...</div>
<div id=grid style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px"></div>
<div id=pos style=margin-top:12px class=card>Posiciones...</div>
<script>
async function toggle(){ await fetch('/api/toggle'); load(); }
async function comprar(sym){ let r=await fetch('/api/buy/'+sym); if(r.ok) load(); else alert((await r.json()).error); }
async function vender(sym){ if(!confirm('Vender '+sym+' TODO?')) return; let r=await fetch('/api/sell/'+sym); if(r.ok) load(); else alert((await r.json()).error); }
async function forceCheck(){ let r=await fetch('/api/force_check'); let j=await r.json(); alert('CHECK - Saldo $'+j.saldo+' Pos '+j.pos+' File:'+j.file); load(); }
async function reporte(){ let r=await fetch('/api/reporte'); let j=await r.json(); alert(j.reporte); }
async function enviarTG(){ let r=await fetch('/api/reporte'); alert('Enviado a Telegram'); }
async function load(){
 let r=await fetch('/api/data'); let d=await r.json();
 document.getElementById('saldo').innerText='$'+Math.round(d.saldo);
 document.getElementById('s1').innerText='$'+Math.round(d.saldo);
 document.getElementById('s2').innerText='$'+Math.round(d.total);
 document.getElementById('s2g').innerText='+ $'+Math.round(d.ganancia);
 document.getElementById('s3').innerText='+$'+Math.round(d.gan_hoy);
 document.getElementById('s4').innerText=d.trades+' trades';
 document.getElementById('autoBtn').innerText=d.auto?'ENCENDIDO':'APAGADO';
 document.getElementById('autoBtn').style.background=d.auto?'#00ff88':'#ff4444';
 document.getElementById('status').innerHTML=`24/7: <b style=color:#00ff88>ACTIVO cada 3 min</b><br>Archivo: ${d.file} | Posiciones: ${Object.keys(d.pos).length} | Reporte auto 22:00 MX`;
 let g=document.getElementById('grid'); g.innerHTML='';
 for(let sym in d.prices){
  let an=d.prices[sym]; let price=an.p? '$'+Number(an.p).toLocaleString(undefined,{maximumFractionDigits:2}): '$0.00';
  let score=an.score; let col=score>=70?'#00ff88':score>=50?'#ffcc00':'#ff4444'; let lbl=score>=70?'COMPRAR':score>=50?'SOSTENER':'VENDER';
  let enPos=d.pos[sym]!=null;
  let btn=enPos?`<button onclick="vender('${sym}')" style="background:#ff3344;color:#fff;border:none;width:100%;padding:10px;border-radius:10px;font-weight:900;margin-top:6px">VENDER</button>`:`<button onclick="comprar('${sym}')" style="background:#00ff88;color:#000;border:none;width:100%;padding:10px;border-radius:10px;font-weight:900;margin-top:6px">COMPRAR</button>`;
  g.innerHTML+=`<div class=coin style="border:2px solid ${col}"><div style="display:flex;justify-content:space-between"><div><b>${sym} ${price}</b><br><span style="font-size:11px;opacity:0.6">SCORE ${score} • RSI ${Math.round(an.rsi)}</span></div><div style=text-align:right><div style="border:2px solid ${col};padding:4px 12px;border-radius:12px"><b style="color:${col};font-size:20px">${score}</b></div><div style="background:${col};color:#000;font-size:10px;font-weight:900;padding:3px 8px;border-radius:8px;margin-top:4px">${lbl}</div></div></div><canvas id="c_${sym}"></canvas>${btn}</div>`;
 }
 for(let sym in d.prices){
  let cl=d.prices[sym].cl || [];
  if(cl.length>10){
    let ctx=document.getElementById('c_'+sym);
    if(ctx){
      let color=d.prices[sym].score>=70?'#00ff88':d.prices[sym].score<50?'#ff4444':'#ffcc00';
      new Chart(ctx,{type:'line',data:{labels:cl.map((_,i)=>i),datasets:[{data:cl,borderColor:color,backgroundColor:color+'33',borderWidth:2,pointRadius:0,tension:0.4,fill:true}]},options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{display:false}},animation:false,responsive:true}});
    }
  }
 }
 let posHtml='';
 for(let k in d.pos){ let v=d.pos[k]; let pr=d.prices[k]?.p||0; let pct=v.e?((pr/v.e-1)*100):0; posHtml+=`<div style=background:#1a1f30;margin:4px 0;padding:8px;border-radius:8px;display:flex;justify-content:space-between><span>${k} x${v.niveles} ${pct.toFixed(2)}% $${v.invertido}</span><button onclick="vender('${k}')" style=background:#ff3344;color:#fff;border:none;padding:4px 10px;border-radius:6px>VENDER</button></div>`; }
 document.getElementById('pos').innerHTML=`<b>Posiciones abiertas (${Object.keys(d.pos).length})</b><div style=margin-top:6px>${posHtml||'Sin pos - esperando SCORE>=70'}</div>`;
}
load(); setInterval(load,15000);
</script></body></html>
""")

@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    cid=q.get('message',{}).get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(q.get('message',{}).get('text') or '').upper()
    if 'REPORTE' in t:
        msg,_=await reporte_diario_logic(); await SEND(cid,msg); return {'ok':1}
    if 'CHECK' in t:
        await PUTERO(); await SEND(cid,f"CHECK Saldo ${int(L()['b'])}"); return {'ok':1}
    await SEND(cid,f"V1002.10 24/7 ACTIVO\nFile: {F}\nDashboard: https://telegram-bot-cijp.onrender.com/dashboard")
    return {'ok':1}
