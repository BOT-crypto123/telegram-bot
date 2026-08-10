import os, json, httpx, asyncio
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

# PRECIO REAL TRIPLE RESPALDO - NUNCA $0
async def P(m):
    # 1. Coinbase
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r=await c.get(f'https://api.coinbase.com/v2/prices/{m}-USD/spot')
            return float(r.json()['data']['amount'])
    except: pass
    # 2. Coingecko
    try:
        mp={'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple'}
        async with httpx.AsyncClient(timeout=6) as c:
            r=await c.get(f'https://api.coingecko.com/api/v3/simple/price?ids={mp[m]}&vs_currencies=usd')
            return float(r.json()[mp[m]]['usd'])
    except: pass
    # 3. Kraken
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r=await c.get(f'https://api.kraken.com/0/public/Ticker?pair={m}USD')
            k=list(r.json()['result'].values())[0]
            return float(k['c'][0])
    except: pass
    return 0

async def C(sym):
    # Usa coingecko para grafica, mas estable
    mp={'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple'}
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.coingecko.com/api/v3/coins/{mp[sym]}/market_chart?vs_currency=usd&days=2')
            prices=r.json().get('prices',[])
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
    if not cl or len(cl)<21:
        # si falla coingecko, intenta precio directo
        p=await P(sym)
        if p>0: return {'p':p,'rsi':50,'tend':'LATERAL','senal':'NADA'}
        return None
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
    return {'p':p,'rsi':rr,'tend':tend,'senal':senal,'cs':cs,'e9':e9,'e21':e21,'e50':e50}

# TELEGRAM CON TECLA AL DASHBOARD
async def G(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link=f'https://{h}/dashboard' if h else 'https://telegram-bot-c...nder.com/dashboard'
        kb={'inline_keyboard':[[{'text':'📊 ABRIR DASHBOARD','url':link}],[{'text':'🟢 AUTO ON','callback_data':'auto_on'},{'text':'🔴 AUTO OFF','callback_data':'auto_off'}]]}
        try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb,'parse_mode':'Markdown'})
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
                await G(cid,f'💸 *VENTA {sym}* {round(chg,1)}% RSI {int(an["rsi"])} Saldo ${int(s["b"])} MXN')
                s=L()
        if s.get('auto') and sym not in s['h'] and s['b']>=monto_mxn and an['rsi']<32:
            s['h'][sym]={'a':(monto_usd*0.998)/an['p'],'e':an['p']}
            s['b']-=monto_mxn; S(s)
            await G(cid,f'🟢 *COMPRA {sym}* ${int(an["p"])} RSI {int(an["rsi"])} {an["senal"]} Saldo ${int(s["b"])} MXN')
            s=L()

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    # Carga todo en paralelo
    an_btc, an_eth, an_sol, an_xrp = await asyncio.gather(AN('BTC'), AN('ETH'), AN('SOL'), AN('XRP'))
    def fmt(an):
        if not an: return {'p':0,'rsi':0,'tend':'...','senal':'CARGANDO','cs':[]}
        return an

    an_btc=fmt(an_btc); an_eth=fmt(an_eth); an_sol=fmt(an_sol); an_xrp=fmt(an_xrp)

    # Si P falla, usa AN.p para no mostrar $0
    btc_p=int(an_btc['p']) if an_btc['p']>0 else await P('BTC')
    eth_p=int(an_eth['p']) if an_eth['p']>0 else await P('ETH')
    sol_p=int(an_sol['p']) if an_sol['p']>0 else await P('SOL')
    xrp_p=round(an_xrp['p'],2) if an_xrp['p']>0 else await P('XRP')

    # Lista de posiciones (misma logica que telegram)
    pos_html=""
    if s['h']:
        for k,v in s['h'].items():
            an = {'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}.get(k)
            chg=(an['p']/v['e']-1)*100 if an and an['p']>0 else 0
            pos_html+=f"<div class=card style=border-color:#00ff88> {k} {round(chg,1)}%<br><b style=color:#00ff88>${int(an['p']) if an else 0}</b><br>Entrada ${int(v['e'])}</div>"
    else:
        pos_html="<div class=card style=grid-column:1/-1>Sin posiciones abiertas</div>"

    auto_txt="🟢 AUTO ON" if s.get('auto') else "🔴 AUTO OFF"
    auto_color="#00ff88" if s.get('auto') else "#ff4444"

    html=f'''<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#0a0e1a;color:white;font-family:monospace;padding:12px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.card{{background:#151a28;border:1px solid #1e2532;border-radius:16px;padding:12px;text-align:center;font-size:12px}}
.card b{{font-size:14px}}
.mxn{{color:#00ff88!important}}.blue{{color:#2a7fff}}
.senal-COMPRA{{color:#00ff88}}.senal-VENTA{{color:#ff4444}}.senal-FUERTE{{color:#ffcc00;font-weight:bold}}
#c{{background:#0f1420;border-radius:16px;padding:10px}}
.ley{{display:flex;gap:8px;justify-content:center;margin:8px 0;font-size:10px;flex-wrap:wrap}}
button{{background:#1e252f;color:#58a6ff;padding:8px 14px;border-radius:10px;margin:3px;border:1px solid #2a3446;font-size:12px}}
h3{{text-align:center;color:#2a7fff;font-size:14px}}
</style></head><body>
<h3>V934 $1000 MXN - TELEGRAM = DASHBOARD</h3>
<div style=text-align:center;margin-bottom:8px><span style=background:{auto_color};color:black;padding:4px 10px;border-radius:20px;font-size:11px>{auto_txt}</span> Saldo <b class=mxn>${int(s["b"])} MXN</b></div>

<div class=grid>
<div class=card>BTC REAL<br><b class=blue>${btc_p}</b><br>RSI {int(an_btc["rsi"])}<br><span class=senal-{an_btc["senal"].split()[0]}>{an_btc["senal"]}</span><br>{an_btc["tend"]}</div>
<div class=card>ETH REAL<br><b class=blue>${eth_p}</b><br>RSI {int(an_eth["rsi"])}<br><span class=senal-{an_eth["senal"].split()[0]}>{an_eth["senal"]}</span><br>{an_eth["tend"]}</div>
<div class=card>SOL REAL<br><b class=blue>${sol_p}</b><br>RSI {int(an_sol["rsi"])}<br><span class=senal-{an_sol["senal"].split()[0]}>{an_sol["senal"]}</span><br>{an_sol["tend"]}</div>
<div class=card>XRP REAL<br><b class=blue>${xrp_p}</b><br>RSI {int(an_xrp["rsi"])}<br><span class=senal-{an_xrp["senal"].split()[0]}>{an_xrp["senal"]}</span><br>{an_xrp["tend"]}</div>
</div>

<h3>📦 Posiciones (misma que Telegram)</h3>
<div class=grid>{pos_html}</div>

<div class=ley><span style=color:#2a7fff>● Precio</span><span style=color:#ffcc00>● EMA9</span><span style=color:#ff4444>● EMA21</span><span style=color:#00ff88>● EMA50</span></div>
<canvas id=c height=140></canvas>
<div style=text-align:center;margin-top:8px><button onclick=sM("bitcoin")>BTC</button><button onclick=sM("ethereum")>ETH</button><button onclick=sM("solana")>SOL</button><button onclick=sM("ripple")>XRP</button></div>
<script>
let ch; function ema(pr,n){{if(pr.length<n)return[];let k=2/(n+1),s=pr.slice(0,n).reduce((a,b)=>a+b)/n,o=[s];for(let i=n;i<pr.length;i++)o.push(pr[i]*k+o[o.length-1]*(1-k));return o;}}
async function sM(id){{
 let r=await fetch("https://api.coingecko.com/api/v3/coins/"+id+"/market_chart?vs_currency=usd&days=2").then(r=>r.json());
 let cs=r.prices.map(x=>x[1]).slice(-70);
 let e9=ema(cs,9), e21=ema(cs,21), e50=ema(cs,50);
 let pad=(arr,len)=>Array(len-arr.length).fill(null).concat(arr);
 if(ch)ch.destroy();
 ch=new Chart(document.getElementById("c"),{{
  type:"line",
  data:{{labels:cs.map((_,i)=>i),datasets:[
   {{data:cs,borderColor:"#2a7fff",backgroundColor:"rgba(42,127,255,0.12)",fill:true,tension:0.4,pointRadius:0,borderWidth:2}},
   {{data:pad(e9,cs.length),borderColor:"#ffcc00",tension:0.4,pointRadius:0,borderWidth:1.2}},
   {{data:pad(e21,cs.length),borderColor:"#ff4444",tension:0.4,pointRadius:0,borderWidth:1.2}},
   {{data:pad(e50,cs.length),borderColor:"#00ff88",tension:0.4,pointRadius:0,borderWidth:1.2}}
  ]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{color:"#1a1f2e"}},ticks:{{display:false}}}},y:{{grid:{{color:"#1a1f2e"}},ticks:{{color:"#888",font:{{size:9}}}}}} }}
 }});
}}
sM("bitcoin");
</script></body></html>'''
    return HTMLResponse(html)

@app.get('/')
@app.post('/')
@app.get('/webhook')
@app.post('/webhook')
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    # callback de botones
    if 'callback_query' in q:
        cid=q['callback_query']['message']['chat']['id']
        data=q['callback_query']['data']
        s=L()
        if data=='auto_on':
            s['auto']=True; S(s); await G(cid,'🚀 *AUTO ON* Activado desde boton'); await BRAIN(cid)
        else:
            s['auto']=False; S(s); await G(cid,'🔴 *AUTO OFF*')
        return {'ok':1}
    msg=q.get('message',{}); cid=msg.get('chat',{}).get('id')
    if not cid: return {'ok':1}
    t=(msg.get('text') or '').upper(); s=L()
    if 'RESET' in t:
        S({'b':1000,'h':{},'hs':[],'auto':False}); await G(cid,'💰 *RESET* $1000 MXN'); return {'ok':1}
    if 'AUTO ON' in t:
        s['auto']=True; S(s); await G(cid,f'🚀 *AUTO ON* Saldo ${int(s["b"])} MXN'); await BRAIN(cid); return {'ok':1}
    if 'AUTO OFF' in t:
        s['auto']=False; S(s); await G(cid,'🔴 *AUTO OFF*'); return {'ok':1}
    if 'DASHBOARD' in t or 'DASH' in t:
        await G(cid,'📊 *Tu Dashboard V934:*'); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        if an: await G(cid,f'*{t} REAL* ${int(an["p"])} RSI {int(an["rsi"])} {an["senal"]} {an["tend"]} Saldo ${int(s["b"])} MXN')
        else: await G(cid,f'{t} cargando...')
        return {'ok':1}
    # Menu default con tecla dashboard
    await G(cid,f'💰 *V934* Saldo ${int(s["b"])} MXN\nRSI<32 COMPRA FUERTE\nEscribe BTC/ETH/SOL/XRP\nAUTO ON / OFF / RESET')
    return {'ok':1}
