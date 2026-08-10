import os, json, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/tmp/b.json'

def L():
    try: return json.load(open(F))
    except: return {'b':1000,'h':{},'hs':[],'auto':False}

def S(s): json.dump(s, open(F,'w'))

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
            return float(r.json()['data']['amount'])
    except: return 0

async def C(sym):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=3600', headers={'User-Agent':'Mozilla'})
            d = r.json()
            return sorted(d)[-80:] if isinstance(d,list) else []
    except: return []

def ema(pr,n):
    if len(pr)<n: return []
    k=2/(n+1)
    s=sum(pr[:n])/n
    o=[s]
    for x in pr[n:]: o.append(x*k+o[-1]*(1-k))
    return o

def rsi(pr):
    if len(pr)<15: return 50
    g=ll=0
    for i in range(1,15):
        d=pr[i]-pr[i-1]
        if d>0: g+=d
        else: ll-=d
    if ll==0: return 80
    if g==0: return 20
    return 100-100/(1+g/ll)

async def AN(sym):
    cl=await C(sym)
    if not cl: return None
    cs=[x[4] for x in cl]
    e9=ema(cs,9); e21=ema(cs,21)
    if not e9: return None
    rr=rsi(cs); p=cs[-1]; a=e9[-1]; b=e21[-1]
    tend='LATERAL'
    if p>a and a>b: tend='SUBE'
    if p<a and a<b: tend='BAJA'
    senal='NADA'
    if rr<30: senal='COMPRA FUERTE'
    elif rr>70: senal='VENTA FUERTE'
    elif p>a and rr<42: senal='COMPRA'
    elif p<a and rr>62: senal='VENTA'
    return {'p':p,'rsi':rr,'tend':tend,'senal':senal}

async def G(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link='https://'+h+'/dashboard' if h else 'https://example.com'
        kb={'inline_keyboard':[[{'text':'DASHBOARD V928','url':link}]]}
        try: await c.post(B+'/sendMessage', json={'chat_id':cid,'text':txt,'reply_markup':kb})
        except: pass

async def BRAIN(cid):
    s=L()
    for sym in ['BTC','ETH','SOL','XRP']:
        an=await AN(sym)
        if not an: continue
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100
            if chg>=2.5 or chg<=-3 or an['rsi']>=72:
                s['b']+=s['h'][sym]['a']*an['p']*0.998
                del s['h'][sym]; S(s)
                await G(cid,f'AUTO VENTA {sym} {round(chg,1)}% RSI{int(an["rsi"])}')
                s=L()
        if s.get('auto') and sym not in s['h'] and s['b']>=100 and an['rsi']<32:
            s['h'][sym]={'a':(100*0.998)/an['p'],'e':an['p']}
            s['b']-=100; S(s)
            await G(cid,f'AUTO COMPRA {sym} RSI{int(an["rsi"])} {an["senal"]}')
            s=L()

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    btc=await P('BTC'); eth=await P('ETH'); sol=await P('SOL'); xrp=await P('XRP')
    html = '<html><head><meta name=viewport content="width=device-width,initial-scale=1">'
    html += '<script src=https://cdn.jsdelivr.net/npm/chart.js></script>'
    html += '<style>body{background:#090c13;color:white;font-family:monospace;padding:12px}.card{background:#12151e;border:1px solid #1e2532;border-radius:12px;padding:14px;margin:6px;display:inline-block;width:18%}button{background:#1e252f;color:#58a6ff;padding:10px 16px;border-radius:8px;margin:4px;border:1px solid #2a3446}</style>'
    html += '</head><body><h2 style=color:#2a7fff>V928 BONITO FULL - 4 MONEDAS + LOGICA RSI</h2>'
    html += f'<div><div class=card>Saldo<br><b>${int(s["b"])}</b></div><div class=card>BTC<br><b>${int(btc)}</b></div><div class=card>ETH<br><b>${int(eth)}</b></div><div class=card>SOL<br><b>${int(sol)}</b></div><div class=card>XRP<br><b>${int(xrp)}</b></div></div>'
    html += '<br><canvas id=c height=200></canvas><br><button onclick=sM("BTC")>BTC</button><button onclick=sM("ETH")>ETH</button><button onclick=sM("SOL")>SOL</button><button onclick=sM("XRP")>XRP</button>'
    html += '<script>let ch;async function sM(m){let r=await fetch("https://api.exchange.coinbase.com/products/"+m+"-USD/candles?granularity=3600").then(r=>r.json());let cs=r.sort((a,b)=>a[0]-b[0]).slice(-50).map(x=>x[4]);if(ch)ch.destroy();ch=new Chart(document.getElementById("c"),{type:"line",data:{labels:cs.map((_,i)=>i),datasets:[{data:cs,borderColor:"#2a7fff",backgroundColor:"rgba(42,127,255,0.2)",fill:true,tension:0.3}]}})}sM("BTC")</script></body></html>'
    return HTMLResponse(html)

@app.get('/')
@app.post('/')
@app.get('/webhook')
@app.post('/webhook')
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    msg=q.get('message',{}); cid=msg.get('chat',{}).get('id')
    if not cid: return {'ok':1}
    t=(msg.get('text') or '').upper(); s=L()
    if 'AUTO ON' in t:
        s['auto']=True; S(s); await G(cid,'AUTO ON V928 FULL RSI<32 LOGICA COMPLETA'); await BRAIN(cid); return {'ok':1}
    if 'AUTO OFF' in t:
        s['auto']=False; S(s); await G(cid,'AUTO OFF'); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        await G(cid,f"{t} ${int(an['p'])} RSI{int(an['rsi'])} {an['senal']} {an['tend']}" if an else f"{t} cargando...")
        return {'ok':1}
    await G(cid,f'V928 FULL Saldo ${int(s["b"])} 4 monedas con logica RSI<32')
    return {'ok':1}
