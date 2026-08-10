import os, json, httpx, asyncio, time, random
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
    ts=int(time.time())
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            pairs={'BTC':'XBTUSD','ETH':'ETHUSD','SOL':'SOLUSD','XRP':'XRPUSD'}
            r=await c.get(f'https://api.kraken.com/0/public/Ticker?pair={pairs[m]}&t={ts}', headers={'Cache-Control':'no-cache','User-Agent':'Mozilla/5.0'})
            j=r.json()
            if 'result' in j:
                k=list(j['result'].values())[0]
                price=float(k['c'][0])
                if m=='BTC' and price < 90000: raise Exception("viejo")
                if m=='ETH' and price < 2500: raise Exception("viejo")
                if m=='SOL' and price < 100: raise Exception("viejo")
                if m=='XRP' and price < 0.5: raise Exception("viejo")
                return price
    except: pass
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD&t={ts}', headers={'User-Agent':'Mozilla/5.0'})
            j=r.json()
            if 'USD' in j and float(j['USD'])>0:
                return float(j['USD'])
    except: pass
    return {'BTC':114800,'ETH':3450,'SOL':172,'XRP':1.05}.get(m,0)

async def C_FULL(sym):
    ts=int(time.time())
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit=100&t={ts}', headers={'User-Agent':'Mozilla/5.0'})
            j=r.json()
            data=j.get('Data',{}).get('Data',[])
            if len(data)>20:
                out=[]
                for x in data:
                    if float(x['close'])==0: continue
                    out.append({'time':int(x['time']), 'open':float(x['open']), 'high':float(x['high']), 'low':float(x['low']), 'close':float(x['close'])})
                return out
    except: pass
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
    return 100-100/(1+g/ll)

def make_candles(base, count=100):
    candles=[]; now=int(time.time()); price=base*0.96
    for i in range(count,0,-1):
        t=now - i*3600
        change = random.uniform(-0.012, 0.012)
        price = price * (1+change)
        if i==1: price=base
        o=price*random.uniform(0.998,1.002)
        h=max(o,price)*random.uniform(1.0,1.006)
        l=min(o,price)*random.uniform(0.994,1.0)
        candles.append({'time':t,'open':o,'high':h,'low':l,'close':price})
    return candles

async def AN(sym):
    candles=await C_FULL(sym)
    p_real=await P(sym)
    if not candles or len(candles)<21:
        candles=make_candles(p_real, 100)
    cs=[c['close'] for c in candles]
    # fuerza ultima vela al precio real
    if cs:
        candles[-1]['close']=p_real
        cs[-1]=p_real
    e9=ema(cs,9); e21=ema(cs,21); e50=ema(cs,50)
    rr=rsi(cs); p=p_real
    a=e9[-1] if e9 else p; b=e21[-1] if e21 else p
    tend='SUBE' if p>a and a>b else 'BAJA' if p<a and a<b else 'LATERAL'
    senal='COMPRA FUERTE' if rr<32 else 'VENTA FUERTE' if rr>70 else 'COMPRA' if p>a and rr<42 else 'VENTA' if p<a and rr>62 else 'NADA'
    return {'p':p,'rsi':rr,'tend':tend,'senal':senal,'candles':candles,'cs':cs,'e9':e9,'e21':e21,'e50':e50}

# --- LOGICA DE COMPRA/VENTA COMPARTIDA TELEGRAM + DASHBOARD ---
def do_buy(s, sym, price):
    if sym in s['h']: return False, "Ya tienes "+sym
    if s['b'] < 200: return False, "Saldo insuficiente"
    monto_usd=200/17.5
    s['h'][sym]={'a':(monto_usd*0.998)/price,'e':price}
    s['b']-=200
    return True, f"COMPRA {sym} ${int(price)}"

def do_sell(s, sym, price):
    if sym not in s['h']: return False, "No tienes "+sym
    entry=s['h'][sym]['e']
    chg=(price/entry-1)*100
    s['b']+=s['h'][sym]['a']*price*0.998*17.5
    del s['h'][sym]
    return True, f"VENTA {sym} {round(chg,1)}%"

async def G(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link=f'https://{h}/dashboard'
        kb={'inline_keyboard':[[{'text':'📊 ABRIR DASHBOARD V943','url':link}],[{'text':'🟢 AUTO ON','callback_data':'auto_on'},{'text':'🔴 AUTO OFF','callback_data':'auto_off'}]]}
        try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb,'parse_mode':'Markdown'})
        except: pass

async def BRAIN(cid):
    s=L()
    for sym in ['BTC','ETH','SOL','XRP']:
        an=await AN(sym)
        if not an: continue
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100
            if chg>=2.5 or chg<=-3 or an['rsi']>=72:
                ok,msg=do_sell(s,sym,an['p']); S(s)
                await G(cid,f'💸 {msg} Saldo ${int(s["b"])} MXN')
                s=L()
        if s.get('auto') and sym not in s['h'] and s['b']>=200 and an['rsi']<32:
            ok,msg=do_buy(s,sym,an['p']); S(s)
            if ok: await G(cid,f'🟢 {msg} RSI {int(an["rsi"])} Saldo ${int(s["b"])} MXN')
            s=L()

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    an_btc, an_eth, an_sol, an_xrp = await asyncio.gather(AN('BTC'), AN('ETH'), AN('SOL'), AN('XRP'))
    def fmt(an, fb):
        if not an: return {'p':fb,'rsi':50,'tend':'LATERAL','senal':'NADA','candles':make_candles(fb),'cs':[fb]*100,'e9':[fb]*100,'e21':[fb]*100,'e50':[fb]*100}
        return an
    an_btc=fmt(an_btc,114800); an_eth=fmt(an_eth,3450); an_sol=fmt(an_sol,172); an_xrp=fmt(an_xrp,1.05)

    import json as js
    btc_c=js.dumps(an_btc['candles']); eth_c=js.dumps(an_eth['candles']); sol_c=js.dumps(an_sol['candles']); xrp_c=js.dumps(an_xrp['candles'])
    btc_e9=js.dumps(an_btc['e9']); btc_e21=js.dumps(an_btc['e21']); btc_e50=js.dumps(an_btc['e50'])
    eth_e9=js.dumps(an_eth['e9']); eth_e21=js.dumps(an_eth['e21']); eth_e50=js.dumps(an_eth['e50'])
    sol_e9=js.dumps(an_sol['e9']); sol_e21=js.dumps(an_sol['e21']); sol_e50=js.dumps(an_sol['e50'])
    xrp_e9=js.dumps(an_xrp['e9']); xrp_e21=js.dumps(an_xrp['e21']); xrp_e50=js.dumps(an_xrp['e50'])

    btc_p=int(an_btc['p']); eth_p=int(an_eth['p']); sol_p=int(an_sol['p']); xrp_p=round(an_xrp['p'],3)
    pos_html=""
    if s['h']:
        for k,v in s['h'].items():
            an = {'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}.get(k)
            chg=(an['p']/v['e']-1)*100 if an else 0
            color="#00ff88" if chg>=0 else "#ff4444"
            pos_html+=f"<div class=card style=border-color:{color}>{k} <b style=color:{color}>{round(chg,1)}%</b><br>Entrada ${int(v['e'])}<br>Ahora ${int(an['p'])}<br><button onclick=\"trade('sell','{k}')\" style=background:#ff4444;color:white>VENDER {k}</button></div>"
    else:
        pos_html="<div class=card style=grid-column:1/-1>Sin posiciones abiertas</div>"

    auto_txt="AUTO ON" if s.get('auto') else "AUTO OFF"
    auto_color="#00ff88" if s.get('auto') else "#ff4444"

    html = """
<html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
body{background:#0b0e14;color:#d1d4dc;font-family:sans-serif;padding:0;margin:0}
.header{padding:12px;background:#151a29;text-align:center;border-bottom:1px solid #1e2532;position:sticky;top:0;z-index:10}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px}
.card{background:#1a1f30;border:1px solid #2a3446;border-radius:12px;padding:10px;text-align:center;font-size:11px}
.card b{font-size:14px;color:#2a7fff}.mxn{color:#00ff88}
#chart{width:100%;height:430px;background:#0f1420}
.ley{display:flex;gap:12px;justify-content:center;padding:6px;font-size:10px;background:#0f1420}
button{background:#1e252f;color:#58a6ff;padding:7px 14px;border-radius:8px;margin:3px;border:1px solid #2a3446;font-size:12px}
.buy{background:#00ff88;color:#000;font-weight:bold;padding:12px 20px;border-radius:10px;font-size:14px;width:48%}
.sell{background:#ff4444;color:#fff;font-weight:bold;padding:12px 20px;border-radius:10px;font-size:14px;width:48%}
.active{border:2px solid #2a7fff!important;background:#2a7fff!important;color:white!important}
</style></head><body>
<div class=header><b style=color:#2a7fff>V943 MITRADE + TRADING $1000 MXN</b><br><span style="background:__AUTO_COLOR__;color:black;padding:3px 10px;border-radius:20px;font-size:11px">__AUTO_TXT__</span> Saldo <b class=mxn>$__SALDO__ MXN</b></div>
<div class=grid>
<div class=card>BTC<br><b>$__BTC_P__</b><br>RSI __BTC_RSI__<br>__BTC_SENAL__<br>__BTC_TEND__</div>
<div class=card>ETH<br><b>$__ETH_P__</b><br>RSI __ETH_RSI__<br>__ETH_SENAL__<br>__ETH_TEND__</div>
<div class=card>SOL<br><b>$__SOL_P__</b><br>RSI __SOL_RSI__<br>__SOL_SENAL__<br>__SOL_TEND__</div>
<div class=card>XRP<br><b>$__XRP_P__</b><br>RSI __XRP_RSI__<br>__XRP_SENAL__<br>__XRP_TEND__</div>
</div>
<div class=ley><span style=color:#26a69a>● Velas</span><span style=color:#ffcc00>● EMA9</span><span style=color:#ef5350>● EMA21</span><span style=color:#00ff88>● EMA50</span></div>
<div id=chart></div>
<div style=text-align:center;padding:8px>
<button id=bBTC onclick="loadSym('BTC')" class="active">BTC</button><button id=bETH onclick="loadSym('ETH')">ETH</button><button id=bSOL onclick="loadSym('SOL')">SOL</button><button id=bXRP onclick="loadSym('XRP')">XRP</button>
</div>
<div style=text-align:center;padding:10px;display:flex;gap:8px;justify-content:center>
<button class=buy onclick="trade('buy',current)">🟢 COMPRAR <span id=symTxt>BTC</span></button>
<button class=sell onclick="trade('sell',current)">🔴 VENDER <span id=symTxt2>BTC</span></button>
</div>
<div id=msg style=text-align:center;padding:6px;color:#00ff88;font-size:12px></div>
<div style=padding:10px><b style=color:#2a7fff>📦 Posiciones (Telegram = Dashboard)</b><div class=grid style=padding:6px 0>__POS__</div></div>
<script>
let current='BTC';
const DATA = {
 BTC: {candles: __BTC_C__, e9: __BTC_E9__, e21: __BTC_E21__, e50: __BTC_E50__},
 ETH: {candles: __ETH_C__, e9: __ETH_E9__, e21: __ETH_E21__, e50: __ETH_E50__},
 SOL: {candles: __SOL_C__, e9: __SOL_E9__, e21: __SOL_E21__, e50: __SOL_E50__},
 XRP: {candles: __XRP_C__, e9: __XRP_E9__, e21: __XRP_E21__, e50: __XRP_E50__}
};
let chart, candleSeries, e9S, e21S, e50S;
function init(){
 const el=document.getElementById('chart');
 chart=LightweightCharts.createChart(el,{width:el.clientWidth,height:430,layout:{background:{type:'solid',color:'#0f1420'},textColor:'#8a8d97'},grid:{vertLines:{color:'#1a1f2e'},horzLines:{color:'#1a1f2e'}},timeScale:{borderColor:'#2a3446',timeVisible:true},rightPriceScale:{borderColor:'#2a3446'}});
 candleSeries=chart.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',borderVisible:false,wickUpColor:'#26a69a',wickDownColor:'#ef5350'});
 e9S=chart.addLineSeries({color:'#ffcc00',lineWidth:1});
 e21S=chart.addLineSeries({color:'#ef5350',lineWidth:1});
 e50S=chart.addLineSeries({color:'#00ff88',lineWidth:1.2});
}
function toLine(candles, arr){
 let out=[]; let start=candles.length - arr.length;
 for(let i=0;i<arr.length;i++){ if(arr[i]) out.push({time:candles[start+i].time, value:arr[i]}); }
 return out;
}
function loadSym(sym){
 current=sym;
 document.getElementById('symTxt').innerText=sym;
 document.getElementById('symTxt2').innerText=sym;
 ['BTC','ETH','SOL','XRP'].forEach(s=>{document.getElementById('b'+s).classList.remove('active')});
 document.getElementById('b'+sym).classList.add('active');
 const d=DATA[sym]; if(!d||!d.candles.length) return;
 candleSeries.setData(d.candles);
 e9S.setData(toLine(d.candles, d.e9));
 e21S.setData(toLine(d.candles, d.e21));
 e50S.setData(toLine(d.candles, d.e50));
 chart.timeScale().fitContent();
}
async function trade(action,sym){
 if(!sym) sym=current;
 document.getElementById('msg').innerText='Procesando '+action+' '+sym+'...';
 try{
  let r=await fetch('/trade/'+action+'?sym='+sym+'&t='+Date.now());
  let j=await r.json();
  document.getElementById('msg').innerText=j.msg+' | Saldo $'+j.saldo+' MXN';
  setTimeout(()=>location.reload(), 1200);
 }catch(e){ document.getElementById('msg').innerText='Error'; }
}
init(); loadSym('BTC');
</script>
</body></html>
"""
    html = html.replace("__AUTO_COLOR__", auto_color).replace("__AUTO_TXT__", auto_txt).replace("__SALDO__", str(int(s["b"])))
    html = html.replace("__BTC_P__", str(btc_p)).replace("__ETH_P__", str(eth_p)).replace("__SOL_P__", str(sol_p)).replace("__XRP_P__", str(xrp_p))
    html = html.replace("__BTC_RSI__", str(int(an_btc["rsi"]))).replace("__ETH_RSI__", str(int(an_eth["rsi"]))).replace("__SOL_RSI__", str(int(an_sol["rsi"]))).replace("__XRP_RSI__", str(int(an_xrp["rsi"])))
    html = html.replace("__BTC_SENAL__", an_btc["senal"]).replace("__ETH_SENAL__", an_eth["senal"]).replace("__SOL_SENAL__", an_sol["senal"]).replace("__XRP_SENAL__", an_xrp["senal"])
    html = html.replace("__BTC_TEND__", an_btc["tend"]).replace("__ETH_TEND__", an_eth["tend"]).replace("__SOL_TEND__", an_sol["tend"]).replace("__XRP_TEND__", an_xrp["tend"])
    html = html.replace("__POS__", pos_html)
    html = html.replace("__BTC_C__", btc_c).replace("__ETH_C__", eth_c).replace("__SOL_C__", sol_c).replace("__XRP_C__", xrp_c)
    html = html.replace("__BTC_E9__", btc_e9).replace("__BTC_E21__", btc_e21).replace("__BTC_E50__", btc_e50)
    html = html.replace("__ETH_E9__", eth_e9).replace("__ETH_E21__", eth_e21).replace("__ETH_E50__", eth_e50)
    html = html.replace("__SOL_E9__", sol_e9).replace("__SOL_E21__", sol_e21).replace("__SOL_E50__", sol_e50)
    html = html.replace("__XRP_E9__", xrp_e9).replace("__XRP_E21__", xrp_e21).replace("__XRP_E50__", xrp_e50)
    return HTMLResponse(html, headers={"Cache-Control":"no-cache"})

@app.get('/trade/{action}')
async def trade_api(action: str, sym: str):
    s=L()
    an=await AN(sym.upper())
    if not an: return {"msg":"Error precio","saldo":int(s['b'])}
    price=an['p']
    if action=='buy':
        ok,msg=do_buy(s,sym.upper(),price)
        if ok: S(s)
        return {"msg":msg,"saldo":int(s['b'])}
    else:
        ok,msg=do_sell(s,sym.upper(),price)
        if ok: S(s)
        return {"msg":msg,"saldo":int(s['b'])}

@app.get('/')
@app.post('/')
@app.get('/webhook')
@app.post('/webhook')
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    if 'callback_query' in q:
        cid=q['callback_query']['message']['chat']['id']; data=q['callback_query']['data']; s=L()
        if data=='auto_on': s['auto']=True; S(s); await G(cid,'AUTO ON'); await BRAIN(cid)
        else: s['auto']=False; S(s); await G(cid,'AUTO OFF')
        return {'ok':1}
    msg=q.get('message',{}); cid=msg.get('chat',{}).get('id')
    if not cid: return {'ok':1}
    t=(msg.get('text') or '').upper(); s=L()
    # COMANDOS TELEGRAM COMPLETOS
    if 'RESET' in t: S({'b':1000,'h':{},'hs':[],'auto':False}); await G(cid,'RESET $1000 MXN - Todo igual Dashboard'); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await G(cid,f'AUTO ON ${int(s["b"])} MXN'); await BRAIN(cid); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await G(cid,'AUTO OFF'); return {'ok':1}
    if 'DASHBOARD' in t or 'DASH' in t: await G(cid,'Dashboard V943 con compra/venta'); return {'ok':1}
    if t.startswith('COMPRAR ') or t.startswith('BUY '):
        sym=t.split()[-1]
        if sym in ['BTC','ETH','SOL','XRP']:
            an=await AN(sym)
            ok,msg=do_buy(s,sym,an['p'])
            if ok: S(s); await G(cid,f'{msg} RSI {int(an["rsi"])} Saldo ${int(s["b"])} MXN')
            else: await G(cid,msg)
        return {'ok':1}
    if t.startswith('VENDER ') or t.startswith('SELL '):
        sym=t.split()[-1]
        if sym in ['BTC','ETH','SOL','XRP']:
            an=await AN(sym)
            ok,msg=do_sell(s,sym,an['p'])
            if ok: S(s); await G(cid,f'{msg} Saldo ${int(s["b"])} MXN')
            else: await G(cid,msg)
        return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']:
        an=await AN(t)
        if an: await G(cid,f'{t} ${int(an["p"])} RSI {int(an["rsi"])} {an["senal"]} {an["tend"]} Saldo ${int(s["b"])} MXN')
        return {'ok':1}
    if 'BALANCE' in t or 'SALDO' in t:
        txt=f'Saldo ${int(s["b"])} MXN\n'
        for k,v in s['h'].items():
            an=await AN(k)
            chg=(an['p']/v['e']-1)*100 if an else 0
            txt+=f'{k}: {round(chg,1)}%\n'
        await G(cid,txt)
        return {'ok':1}
    await G(cid,f'V943 COMPLETO ${int(s["b"])} MXN\nDashboard: velas + EMA + comprar/vender\nTelegram: COMPRAR BTC, VENDER BTC, BALANCE, AUTO ON/OFF, RESET, DASHBOARD')
    return {'ok':1}
