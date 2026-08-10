import os, json, httpx, asyncio, time
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
    pairs={'BTC':'XBTUSD','ETH':'ETHUSD','SOL':'SOLUSD','XRP':'XRPUSD'}
    ts=int(time.time())
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.kraken.com/0/public/Ticker?pair={pairs[m]}&t={ts}', headers={'Cache-Control':'no-cache','User-Agent':'Mozilla/5.0'})
            j=r.json()
            if 'result' in j:
                k=list(j['result'].values())[0]
                price=float(k['c'][0])
                if m=='BTC' and price < 80000: raise Exception("viejo")
                return price
    except: pass
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.allorigins.win/raw?url=https://api.binance.com/api/v3/ticker/price?symbol={m}USDT%26t={ts}')
            j=r.json()
            if 'price' in j: return float(j['price'])
    except: pass
    return {'BTC':114800,'ETH':3480,'SOL':149,'XRP':1.05}.get(m,0)

async def C_FULL(sym):
    pairs={'BTC':'XBTUSD','ETH':'ETHUSD','SOL':'SOLUSD','XRP':'XRPUSD'}
    ts=int(time.time())
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://api.kraken.com/0/public/OHLC?pair={pairs[sym]}&interval=60&t={ts}', headers={'Cache-Control':'no-cache','User-Agent':'Mozilla/5.0'})
            j=r.json()
            result=j.get('result',{})
            keys=[k for k in result.keys() if k!='last']
            if not keys: return []
            data=result[keys[0]]
            # time, open, high, low, close, vwap, volume, count
            out=[]
            for x in data[-100:]:
                out.append({'time':int(x[0]), 'open':float(x[1]), 'high':float(x[2]), 'low':float(x[3]), 'close':float(x[4])})
            if sym=='BTC' and out[-1]['close'] < 80000: return []
            return out
    except: return []

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
    return 100-100/(1+g/ll)

async def AN(sym):
    candles=await C_FULL(sym)
    p_real=await P(sym)
    if not candles or len(candles)<21:
        return {'p':p_real,'rsi':54,'tend':'LATERAL','senal':'NADA','candles':[{'time':int(time.time())-i*3600,'open':p_real,'high':p_real,'low':p_real,'close':p_real} for i in range(60,0,-1)], 'cs':[p_real]*60,'e9':[p_real]*60,'e21':[p_real]*60,'e50':[p_real]*60}
    cs=[c['close'] for c in candles]
    e9=ema(cs,9); e21=ema(cs,21); e50=ema(cs,50)
    rr=rsi(cs); p=p_real
    a=e9[-1] if e9 else p; b=e21[-1] if e21 else p
    tend='SUBE' if p>a and a>b else 'BAJA' if p<a and a<b else 'LATERAL'
    senal='COMPRA FUERTE' if rr<32 else 'VENTA FUERTE' if rr>70 else 'COMPRA' if p>a and rr<42 else 'VENTA' if p<a and rr>62 else 'NADA'
    return {'p':p,'rsi':rr,'tend':tend,'senal':senal,'candles':candles,'cs':cs,'e9':e9,'e21':e21,'e50':e50}

async def G(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link=f'https://{h}/dashboard'
        kb={'inline_keyboard':[[{'text':'📊 VER GRAFICA MITRADE V940','url':link}],[{'text':'🟢 AUTO ON','callback_data':'auto_on'},{'text':'🔴 AUTO OFF','callback_data':'auto_off'}]]}
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
    def fmt(an, fb):
        if not an: return {'p':fb,'rsi':54,'tend':'LATERAL','senal':'NADA','candles':[],'cs':[fb]*60,'e9':[fb]*60,'e21':[fb]*60,'e50':[fb]*60}
        return an
    an_btc=fmt(an_btc,114800); an_eth=fmt(an_eth,3480); an_sol=fmt(an_sol,149); an_xrp=fmt(an_xrp,1.05)
    if an_btc['p']<80000: an_btc['p']=114800
    import json as js

    btc_p=int(an_btc['p']); eth_p=int(an_eth['p']); sol_p=int(an_sol['p']); xrp_p=round(an_xrp['p'],3)
    pos_html=""
    if s['h']:
        for k,v in s['h'].items():
            an = {'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}.get(k)
            chg=(an['p']/v['e']-1)*100 if an and an['p']>0 else 0
            pos_html+=f"<div class=card style=border-color:#00ff88>{k} {round(chg,1)}%<br><b style=color:#00ff88>${int(an['p'])}</b></div>"
    else:
        pos_html="<div class=card style=grid-column:1/-1>Sin posiciones abiertas</div>"
    auto_txt="🟢 AUTO ON" if s.get('auto') else "🔴 AUTO OFF"
    auto_color="#00ff88" if s.get('auto') else "#ff4444"

    html=f'''<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<style>
body{{background:#0b0e14;color:#d1d4dc;font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:0;margin:0}}
.header{{padding:12px;background:#151a29;text-align:center;border-bottom:1px solid #1e2532}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px}}
.card{{background:#1a1f30;border:1px solid #2a3446;border-radius:12px;padding:10px;text-align:center;font-size:11px}}
.card b{{font-size:14px;color:#2a7fff}}.mxn{{color:#00ff88!important}}
#chart{{width:100%;height:420px;background:#0f1420}}
.ley{{display:flex;gap:12px;justify-content:center;padding:6px;font-size:10px;background:#0f1420}}
button{{background:#1e252f;color:#58a6ff;padding:7px 14px;border-radius:8px;margin:3px;border:1px solid #2a3446;font-size:12px}}
.s-COMPRA{{color:#26a69a}}.s-VENTA{{color:#ef5350}}.s-FUERTE{{color:#ffcc00;font-weight:bold}}
</style></head><body>
<div class=header><b style=color:#2a7fff>V940 MITRADE STYLE $1000 MXN</b><br><span style=background:{auto_color};color:black;padding:3px 10px;border-radius:20px;font-size:11px>{auto_txt}</span> Saldo <b class=mxn>${int(s["b"])} MXN</b></div>

<div class=grid>
<div class=card>BTC<br><b>${btc_p}</b><br>RSI {int(an_btc["rsi"])}<br><span class=s-{an_btc["senal"].split()[0]}>{an_btc["senal"]}</span><br>{an_btc["tend"]}</div>
<div class=card>ETH<br><b>${eth_p}</b><br>RSI {int(an_eth["rsi"])}<br><span class=s-{an_eth["senal"].split()[0]}>{an_eth["senal"]}</span><br>{an_eth["tend"]}</div>
<div class=card>SOL<br><b>${sol_p}</b><br>RSI {int(an_sol["rsi"])}<br><span class=s-{an_sol["senal"].split()[0]}>{an_sol["senal"]}</span><br>{an_sol["tend"]}</div>
<div class=card>XRP<br><b>${xrp_p}</b><br>RSI {int(an_xrp["rsi"])}<br><span class=s-{an_xrp["senal"].split()[0]}>{an_xrp["senal"]}</span><br>{an_xrp["tend"]}</div>
</div>

<div class=ley><span style=color:#26a69a>● Velas</span><span style=color:#ffcc00>● EMA9</span><span style=color:#ef5350>● EMA21</span><span style=color:#00ff88>● EMA50</span></div>
<div id=chart></div>
<div style=text-align:center;padding:6px><button onclick="load('BTC')">BTC</button><button onclick="load('ETH')">ETH</button><button onclick="load('SOL')">SOL</button><button onclick="load('XRP')">XRP</button></div>

<div style=padding:10px><b style=color:#2a7fff>📦 Posiciones (Telegram = Dashboard)</b><div class=grid style=padding:6px 0>{pos_html}</div></div>

<script>
const DATA={{
 BTC: {{candles: {js.dumps(an_btc['candles'])}, e9: {js.dumps(an_btc['e9'])}, e21: {js.dumps(an_btc['e21'])}, e50: {js.dumps(an_btc['e50'])}} }},
 ETH: {{candles: {js.dumps(an_eth['candles'])}, e9: {js.dumps(an_eth['e9'])}, e21: {js.dumps(an_eth['e21'])}, e50: {js.dumps(an_eth['e50'])}} }},
 SOL: {{candles: {js.dumps(an_sol['candles'])}, e9: {js.dumps(an_sol['e9'])}, e21: {js.dumps(an_sol['e21'])}, e50: {js.dumps(an_sol['e50'])}} }},
 XRP: {{candles: {js.dumps(an_xrp['candles'])}, e9: {js.dumps(an_xrp['e9'])}, e21: {js.dumps(an_xrp['e21'])}, e50: {js.dumps(an_xrp['e50'])}} }}
}};

let chart, candleSeries, ema9Series, ema21Series, ema50Series;
function initChart(){{
 const el=document.getElementById('chart');
 chart=LightweightCharts.createChart(el, {{
  width: el.clientWidth, height: 420,
  layout: {{background:{{type:'solid',color:'#0f1420'}}, textColor:'#8a8d97'}},
  grid: {{vertLines:{{color:'#1a1f2e'}}, horzLines:{{color:'#1a1f2e'}}}},
  timeScale:{{borderColor:'#2a3446', timeVisible:true}},
  rightPriceScale:{{borderColor:'#2a3446'}}
 }});
 candleSeries=chart.addCandlestickSeries({{upColor:'#26a69a', downColor:'#ef5350', borderVisible:false, wickUpColor:'#26a69a', wickDownColor:'#ef5350'}});
 ema9Series=chart.addLineSeries({{color:'#ffcc00', lineWidth:1}});
 ema21Series=chart.addLineSeries({{color:'#ef5350', lineWidth:1}});
 ema50Series=chart.addLineSeries({{color:'#00ff88', lineWidth:1.2}});
 window.addEventListener('resize', ()=>{{chart.applyOptions({{width:el.clientWidth}})}});
}}
function load(sym){{
 const d=DATA[sym]; if(!d||!d.candles.length) return;
 candleSeries.setData(d.candles);
 function toLine(arr){{
  let out=[]; let start=d.candles.length - arr.length;
  for(let i=0;i<arr.length;i++){{ if(arr[i]) out.push({{time:d.candles[start+i].time, value:arr[i]}}); }}
  return out;
 }}
 ema9Series.setData(toLine(d.e9));
 ema21Series.setData(toLine(d.e21));
 ema50Series.setData(toLine(d.e50));
 chart.timeScale().fitContent();
}}
initChart(); load('BTC');
</script>
</body></html>'''
    return HTMLResponse(html, headers={"Cache-Control":"no-cache"})

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
    if 'DASHBOARD' in t or 'DASH' in t: await G(cid,'📊 *Dashboard Mitrade V940*'); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        if an: await G(cid,f'*{t}* ${int(an["p"])} RSI {int(an["rsi"])} {an["senal"]} Saldo ${int(s["b"])} MXN')
        return {'ok':1}
    await G(cid,f'💹 *V940 MITRADE STYLE* ${int(s["b"])} MXN\nVelas japonesas + EMA9/21/50\nAUTO ON/OFF/RESET/DASHBOARD')
    return {'ok':1}
