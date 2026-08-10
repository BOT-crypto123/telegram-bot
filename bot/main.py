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

# FIX PRECIOS REALES - COINGECKO
async def P(m):
    mp={'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple'}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://api.coingecko.com/api/v3/simple/price?ids={mp[m]}&vs_currencies=usd')
            return float(r.json()[mp[m]]['usd'])
    except: return 0

async def C(sym):
    mp={'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple'}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://api.coingecko.com/api/v3/coins/{mp[sym]}/market_chart?vs_currency=usd&days=3')
            j=r.json()
            # convierte formato coingecko [[timestamp,price],...] a [timestamp,0,0,0,price]
            prices=j.get('prices',[])
            return [[p[0],0,0,0,p[1]] for p in prices[-80:]]
    except:
        return []

def ema(pr,n):
    if len(pr)<n: return []
    k=2/(n+1); s=sum(pr[:n])/n; o=[s]
    for x in pr[n:]: o.append(x*k+o[-1]*(1-k))
    return o

def rsi(pr):
    if len(pr)<15: return 50
    g=ll=0
    for i in range(1,15):
        d=pr[i]-pr[i-1]
        if d>0: g+=d
        else: ll-=d
    if ll==0: return 79
    if g==0: return 21
    return 100-100/(1+g/ll)

async def AN(sym):
    cl=await C(sym)
    if not cl or len(cl)<21: return None
    cs=[float(x[4]) for x in cl]
    e9=ema(cs,9); e21=ema(cs,21); e50=ema(cs,50)
    if not e9: return None
    rr=rsi(cs); p=cs[-1]; a=e9[-1]; b=e21[-1]
    tend='LATERAL'; senal='NADA'
    if p>a and a>b: tend='SUBE'
    if p<a and a<b: tend='BAJA'
    if rr < 32: senal='COMPRA FUERTE'
    elif rr > 70: senal='VENTA FUERTE'
    elif p>a and rr<42: senal='COMPRA'
    elif p<a and rr>62: senal='VENTA'
    return {'p':p,'rsi':rr,'tend':tend,'senal':senal}

async def G(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link='https://'+h+'/dashboard' if h else 'https://example.com'
        kb={'inline_keyboard':[[{'text':'📈 DASHBOARD V933 REAL','url':link}]]}
        try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb})
        except: pass

async def BRAIN(cid):
    s=L(); monto_mxn=200; usd_mxn=17.5; monto_usd=monto_mxn/usd_mxn
    for sym in ['BTC','ETH','SOL','XRP']:
        an=await AN(sym)
        if not an: continue
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100
            if chg>=2.5 or chg<=-3 or an['rsi']>=72:
                s['b']+=s['h'][sym]['a']*an['p']*0.998*usd_mxn
                del s['h'][sym]; S(s)
                await G(cid,f'💸 VENTA {sym} {round(chg,1)}% Saldo ${int(s["b"])} MXN')
                s=L()
        if s.get('auto') and sym not in s['h'] and s['b']>=monto_mxn and an['rsi']<32:
            s['h'][sym]={'a':(monto_usd*0.998)/an['p'],'e':an['p']}
            s['b']-=monto_mxn; S(s)
            await G(cid,f'🟢 COMPRA {sym} ${int(an["p"])} RSI{int(an["rsi"])} Saldo ${int(s["b"])} MXN')
            s=L()

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    btc=await P('BTC'); eth=await P('ETH'); sol=await P('SOL'); xrp=await P('XRP')
    if btc==0: # fallback
        a=await AN('BTC'); btc=a['p'] if a else 0
        a=await AN('ETH'); eth=a['p'] if a else 0
        a=await AN('SOL'); sol=a['p'] if a else 0
        a=await AN('XRP'); xrp=a['p'] if a else 0

    html=f'''<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#0a0e1a;color:white;font-family:monospace;padding:12px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.card{{background:#151a28;border:1px solid #1e2532;border-radius:16px;padding:14px;text-align:center}}
.card b{{color:#2a7fff;font-size:15px}}.mxn{{color:#00ff88!important}}
#c{{background:#0f1420;border-radius:16px;padding:10px}}
.ley{{display:flex;gap:10px;justify-content:center;margin:8px 0;font-size:11px;flex-wrap:wrap}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block}}
button{{background:#1e252f;color:#58a6ff;padding:10px 18px;border-radius:10px;margin:4px;border:1px solid #2a3446}}
</style></head><body>
<h3 style=color:#2a7fff;text-align:center>V933 REAL $1000 MXN - 3 LINEAS RSI32</h3>
<div class=grid>
<div class=card>Saldo MXN<br><b class=mxn>${int(s["b"])} MXN</b></div>
<div class=card>BTC REAL<br><b>${int(btc)}</b></div>
<div class=card>ETH REAL<br><b>${int(eth)}</b></div>
<div class=card>SOL REAL<br><b>${int(sol)}</b></div>
</div>
<div style=text-align:center;margin:10px 0><div class=card>XRP<br><b>${round(xrp,2)}</b></div></div>
<div class=ley><span><i class=dot style=background:#2a7fff></i> Precio</span><span><i class=dot style=background:#ffcc00></i> EMA9</span><span><i class=dot style=background:#ff4444></i> EMA21</span><span><i class=dot style=background:#00ff88></i> EMA50</span></div>
<canvas id=c height=140></canvas>
<div style=text-align:center;margin-top:10px><button onclick=sM("bitcoin","BTC")>BTC</button><button onclick=sM("ethereum","ETH")>ETH</button><button onclick=sM("solana","SOL")>SOL</button><button onclick=sM("ripple","XRP")>XRP</button></div>
<script>
let ch;
function ema(pr,n){{if(pr.length<n)return[];let k=2/(n+1),s=pr.slice(0,n).reduce((a,b)=>a+b)/n,o=[s];for(let i=n;i<pr.length;i++)o.push(pr[i]*k+o[o.length-1]*(1-k));return o;}}
async function sM(id,sym){{
 let r=await fetch("https://api.coingecko.com/api/v3/coins/"+id+"/market_chart?vs_currency=usd&days=3").then(r=>r.json());
 let cs=r.prices.map(x=>x[1]).slice(-70);
 let e9=ema(cs,9), e21=ema(cs,21), e50=ema(cs,50);
 let pad=(arr,len)=>Array(len-arr.length).fill(null).concat(arr);
 let L=cs.length;
 if(ch)ch.destroy();
 ch=new Chart(document.getElementById("c"),{{
  type:"line",
  data:{{
   labels:cs.map((_,i)=>i),
   datasets:[
    {{data:cs,borderColor:"#2a7fff",backgroundColor:"rgba(42,127,255,0.15)",fill:true,tension:0.4,pointRadius:0,borderWidth:2,label:"Precio"}},
    {{data:pad(e9,L),borderColor:"#ffcc00",tension:0.4,pointRadius:0,borderWidth:1.5,label:"EMA9"}},
    {{data:pad(e21,L),borderColor:"#ff4444",tension:0.4,pointRadius:0,borderWidth:1.5,label:"EMA21"}},
    {{data:pad(e50,L),borderColor:"#00ff88",tension:0.4,pointRadius:0,borderWidth:1.5,label:"EMA50"}}
   ]
  }},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{color:"#1a1f2e"}},ticks:{{display:false}}}},y:{{grid:{{color:"#1a1f2e"}},ticks:{{color:"#888"}}}}}} }}
 }});
}}
sM("bitcoin","BTC");
</script></body></html>'''
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
    if 'RESET' in t:
        S({'b':1000,'h':{},'hs':[],'auto':False}); await G(cid,'💰 RESET $1000 MXN V933 REAL'); return {'ok':1}
    if 'AUTO ON' in t:
        s['auto']=True; S(s); await G(cid,f'🚀 AUTO ON V933 REAL RSI<32 Saldo ${int(s["b"])} MXN'); await BRAIN(cid); return {'ok':1}
    if 'AUTO OFF' in t:
        s['auto']=False; S(s); await G(cid,'🔴 AUTO OFF'); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        if an: await G(cid,f'{t} REAL ${int(an["p"])} RSI{int(an["rsi"])} {an["senal"]} Saldo ${int(s["b"])} MXN')
        else: await G(cid,f'{t} cargando precio real...')
        return {'ok':1}
    await G(cid,f'💰 V933 REAL ${int(s["b"])} MXN | Precios reales Coingecko | 3 LINEAS')
    return {'ok':1}
