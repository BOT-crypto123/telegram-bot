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

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.kraken.com/0/public/Ticker?pair={m}USD', headers={'User-Agent':'Mozilla/5.0'})
            k=list(r.json()['result'].values())[0]
            return float(k['c'][0])
    except: return 0

async def C(sym):
    # KRAKEN OHLC - SI FUNCIONA EN RENDER USA
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://api.kraken.com/0/public/OHLC?pair={sym}USD&interval=60', headers={'User-Agent':'Mozilla/5.0'})
            j=r.json()
            result=j.get('result',{})
            # Kraken devuelve { "XXBTZUSD": [...], "last":... }
            key=list(result.keys())[0]
            if key=='last': key=list(result.keys())[1]
            data=result[key]
            # data: [time, open, high, low, close, vwap, volume, count]
            return [[int(x[0]),0,0,0,float(x[4])] for x in data[-80:]]
    except Exception as e:
        print(f"Kraken OHLC fail {sym}: {e}")
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
    if ll==0: return 78
    if g==0: return 22
    rs=g/ll
    return 100-100/(1+rs)

async def AN(sym):
    cl=await C(sym)
    p_real=await P(sym)
    if not cl or len(cl)<21:
        return {'p':p_real,'rsi':50,'tend':'LATERAL','senal':'ESPERA','cs':[p_real]*60,'e9':[p_real]*60,'e21':[p_real]*60,'e50':[p_real]*60} if p_real>0 else None
    cs=[float(x[4]) for x in cl]
    e9=ema(cs,9); e21=ema(cs,21); e50=ema(cs,50)
    if not e9 or len(e9)<2: return None
    rr=rsi(cs); p=p_real if p_real>0 else cs[-1]; a=e9[-1]; b=e21[-1]
    tend='SUBE' if p>a and a>b else 'BAJA' if p<a and a<b else 'LATERAL'
    if rr < 32: senal='COMPRA FUERTE'
    elif rr > 70: senal='VENTA FUERTE'
    elif p>a and rr<42: senal='COMPRA'
    elif p<a and rr>62: senal='VENTA'
    else: senal='NADA'
    return {'p':p,'rsi':rr,'tend':tend,'senal':senal,'cs':cs,'e9':e9,'e21':e21,'e50':e50}

async def G(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link=f'https://{h}/dashboard'
        kb={'inline_keyboard':[[{'text':'📊 ABRIR DASHBOARD V938','url':link}],[{'text':'🟢 AUTO ON','callback_data':'auto_on'},{'text':'🔴 AUTO OFF','callback_data':'auto_off'}]]}
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
    an_btc, an_eth, an_sol, an_xrp = await asyncio.gather(AN('BTC'), AN('ETH'), AN('SOL'), AN('XRP'))
    def fmt(an, fallback):
        if not an: return {'p':fallback,'rsi':50,'tend':'LATERAL','senal':'NADA','cs':[fallback]*60,'e9':[fallback]*60,'e21':[fallback]*60,'e50':[fallback]*60}
        return an
    an_btc=fmt(an_btc,114500); an_eth=fmt(an_eth,3450); an_sol=fmt(an_sol,148); an_xrp=fmt(an_xrp,1.02)

    btc_p=int(an_btc['p']); eth_p=int(an_eth['p']); sol_p=int(an_sol['p']); xrp_p=round(an_xrp['p'],3)
    pos_html=""
    if s['h']:
        for k,v in s['h'].items():
            an = {'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}.get(k)
            chg=(an['p']/v['e']-1)*100 if an and an['p']>0 else 0
            pos_html+=f"<div class=card style=border-color:#00ff88>{k} {round(chg,1)}%<br><b style=color:#00ff88>${int(an['p'])}</b><br>Entrada ${int(v['e'])}</div>"
    else:
        pos_html="<div class=card style=grid-column:1/-1>Sin posiciones abiertas</div>"

    auto_txt="🟢 AUTO ON" if s.get('auto') else "🔴 AUTO OFF"
    auto_color="#00ff88" if s.get('auto') else "#ff4444"
    import json as js

    html=f'''<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#0a0e1a;color:white;font-family:monospace;padding:12px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.card{{background:#151a28;border:1px solid #1e2532;border-radius:16px;padding:12px;text-align:center;font-size:11px}}
.card b{{font-size:13px}}.mxn{{color:#00ff88}}.blue{{color:#2a7fff}}
#c{{background:#0f1420;border-radius:16px;padding:10px}}
button{{background:#1e252f;color:#58a6ff;padding:8px 14px;border-radius:10px;margin:3px;border:1px solid #2a3446;font-size:11px}}
.s-COMPRA{{color:#00ff88}}.s-VENTA{{color:#ff4444}}.s-FUERTE{{color:#ffcc00}}
</style></head><body>
<h3 style=text-align:center;color:#2a7fff>V938 KRAKEN REAL + RSI + GRAFICA</h3>
<div style=text-align:center;margin-bottom:8px><span style=background:{auto_color};color:black;padding:4px 10px;border-radius:20px>{auto_txt}</span> Saldo <b class=mxn>${int(s["b"])} MXN</b></div>
<div class=grid>
<div class=card>BTC<br><b class=blue>${btc_p}</b><br>RSI {int(an_btc["rsi"])}<br><span class=s-{an_btc["senal"].split()[0]}>{an_btc["senal"]}</span><br>{an_btc["tend"]}</div>
<div class=card>ETH<br><b class=blue>${eth_p}</b><br>RSI {int(an_eth["rsi"])}<br><span class=s-{an_eth["senal"].split()[0]}>{an_eth["senal"]}</span><br>{an_eth["tend"]}</div>
<div class=card>SOL<br><b class=blue>${sol_p}</b><br>RSI {int(an_sol["rsi"])}<br><span class=s-{an_sol["senal"].split()[0]}>{an_sol["senal"]}</span><br>{an_sol["tend"]}</div>
<div class=card>XRP<br><b class=blue>${xrp_p}</b><br>RSI {int(an_xrp["rsi"])}<br><span class=s-{an_xrp["senal"].split()[0]}>{an_xrp["senal"]}</span><br>{an_xrp["tend"]}</div>
</div>
<h3 style=color:#2a7fff;text-align:center;margin-top:12px>📦 Posiciones (Telegram = Dashboard)</h3>
<div class=grid>{pos_html}</div>
<div style=text-align:center;margin:8px 0;font-size:10px><span style=color:#2a7fff>● Precio</span> <span style=color:#ffcc00>● EMA9</span> <span style=color:#ff4444>● EMA21</span> <span style=color:#00ff88>● EMA50</span></div>
<canvas id=c height=160></canvas>
<div style=text-align:center><button onclick="sM('BTC')">BTC</button><button onclick="sM('ETH')">ETH</button><button onclick="sM('SOL')">SOL</button><button onclick="sM('XRP')">XRP</button></div>
<script>
let ch;
const DATA={{BTC:{{cs:{js.dumps(an_btc['cs'][-60:])},e9:{js.dumps(an_btc['e9'][-60:])},e21:{js.dumps(an_btc['e21'][-60:])},e50:{js.dumps(an_btc['e50'][-60:])}}}, ETH:{{cs:{js.dumps(an_eth['cs'][-60:])},e9:{js.dumps(an_eth['e9'][-60:])},e21:{js.dumps(an_eth['e21'][-60:])},e50:{js.dumps(an_eth['e50'][-60:])}}}, SOL:{{cs:{js.dumps(an_sol['cs'][-60:])},e9:{js.dumps(an_sol['e9'][-60:])},e21:{js.dumps(an_sol['e21'][-60:])},e50:{js.dumps(an_sol['e50'][-60:])}}}, XRP:{{cs:{js.dumps(an_xrp['cs'][-60:])},e9:{js.dumps(an_xrp['e9'][-60:])},e21:{js.dumps(an_xrp['e21'][-60:])},e50:{js.dumps(an_xrp['e50'][-60:])}}} }};
function pad(a,l){{return Array(l-a.length).fill(null).concat(a)}}
function sM(s){{
 let d=DATA[s]; if(!d) return; if(ch)ch.destroy();
 ch=new Chart(document.getElementById("c"),{{type:"line",data:{{labels:d.cs.map((_,i)=>i),datasets:[
   {{data:d.cs,borderColor:"#2a7fff",backgroundColor:"rgba(42,127,255,0.15)",fill:true,tension:0.4,pointRadius:0,borderWidth:2}},
   {{data:pad(d.e9,d.cs.length),borderColor:"#ffcc00",tension:0.4,pointRadius:0,borderWidth:1.2}},
   {{data:pad(d.e21,d.cs.length),borderColor:"#ff4444",tension:0.4,pointRadius:0,borderWidth:1.2}},
   {{data:pad(d.e50,d.cs.length),borderColor:"#00ff88",tension:0.4,pointRadius:0,borderWidth:1.2}}
 ]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{color:"#1a1f2e"}},ticks:{{display:false}}}},y:{{grid:{{color:"#1a1f2e"}},ticks:{{color:"#888",font:{{size:9}}}}}} }} }});
}}
sM('BTC');
</script></body></html>'''
    return HTMLResponse(html)

@app.get('/')
@app.post('/')
@app.get('/webhook')
@app.post('/webhook')
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    if 'callback_query' in q:
        cid=q['callback_query']['message']['chat']['id']; data=q['callback_query']['data']; s=L()
        if data=='auto_on': s['auto']=True; S(s); await G(cid,'🚀 *AUTO ON*'); await BRAIN(cid)
        else: s['auto']=False; S(s); await G(cid,'🔴 *AUTO OFF*')
        return {'ok':1}
    msg=q.get('message',{}); cid=msg.get('chat',{}).get('id')
    if not cid: return {'ok':1}
    t=(msg.get('text') or '').upper(); s=L()
    if 'RESET' in t: S({'b':1000,'h':{},'hs':[],'auto':False}); await G(cid,'💰 *RESET $1000 MXN*'); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await G(cid,f'🚀 *AUTO ON* ${int(s["b"])} MXN'); await BRAIN(cid); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await G(cid,'🔴 *AUTO OFF*'); return {'ok':1}
    if 'DASHBOARD' in t or 'DASH' in t: await G(cid,'📊 *Dashboard V938*'); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        if an: await G(cid,f'*{t} KRAKEN* ${int(an["p"])} RSI {int(an["rsi"])} {an["senal"]} {an["tend"]} Saldo ${int(s["b"])} MXN')
        return {'ok':1}
    await G(cid,f'💰 *V938* ${int(s["b"])} MXN Kraken Real + Grafica + 3 EMAs\nBTC/ETH/SOL/XRP - AUTO ON/OFF/RESET/DASHBOARD')
    return {'ok':1}
