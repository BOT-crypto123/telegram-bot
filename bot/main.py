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
            if 'alert_users' not in d: d['alert_users']=[]
            if 'b' not in d: d['b']=1000
            if 'h' not in d: d['h']={}
            if 'hs' not in d: d['hs']=[]
            if 'auto' not in d: d['auto']=False
            if 'ganancia_total' not in d: d['ganancia_total']=0
            if 'total_trades' not in d: d['total_trades']=0
            return d
    except: pass
    return {'b':1000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[],'inicial':1000}

def S(s):
    try:
        json.dump(s, open(F,'w'))
        json.dump(s, open('/tmp/bot_backup.json','w'))
    except: pass

MONTO_MXN = 50
TAKE_PROFIT = 2.5
STOP_LOSS = -3.0

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD&ts={int(time.time())}')
            j=r.json()
            if 'USD' in j: return float(j['USD'])
    except: pass
    return {'BTC':114800,'ETH':3450,'SOL':172,'XRP':1.021}.get(m,0)

async def C_FULL(sym):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit=100')
            j=r.json()
            data=j.get('Data',{}).get('Data',[])
            out=[{'time':int(x['time']),'open':float(x['open']),'high':float(x['high']),'low':float(x['low']),'close':float(x['close'])} for x in data if float(x['close'])>0]
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
    return 78 if ll==0 else 22 if g==0 else 100-100/(1+g/ll)

def make_candles(base, count=100):
    now=int(time.time()); price=base*0.97; candles=[]
    for i in range(count,0,-1):
        price=max(price*(1+random.uniform(-0.01,0.01)), base*0.85)
        if i==1: price=base
        o=price*random.uniform(0.998,1.002)
        candles.append({'time':now-i*3600,'open':round(o,4),'high':round(max(o,price)*1.003,4),'low':round(min(o,price)*0.997,4),'close':round(price,4)})
    return candles

async def AN(sym):
    candles=await C_FULL(sym)
    p_real=await P(sym)
    if not candles or len(candles)<30: candles=make_candles(p_real,100)
    else: candles[-1]['close']=p_real
    cs=[c['close'] for c in candles]
    e9=ema(cs,9); e21=ema(cs,21); e50=ema(cs,50)
    rr=rsi(cs)
    tend='SUBE' if p_real>e9[-1]>e21[-1] else 'BAJA' if p_real<e9[-1]<e21[-1] else 'LATERAL'
    senal='COMPRA FUERTE' if rr<30 else 'VENTA FUERTE' if rr>70 else 'COMPRA' if p_real>e9[-1] and rr<40 else 'VENTA' if p_real<e9[-1] and rr>60 else 'NADA'
    return {'p':p_real,'rsi':rr,'tend':tend,'senal':senal,'candles':candles,'e9':e9,'e21':e21,'e50':e50}

def do_buy(s, sym, price):
    if sym in s['h']: return False, f"Ya tienes {sym}"
    if s['b'] < MONTO_MXN: return False, f"Saldo insuficiente ${MONTO_MXN}"
    s['h'][sym]={'a':(MONTO_MXN/17.5*0.998)/price,'e':price}
    s['b']-=MONTO_MXN
    return True, f"✅ COMPRADO {sym} ${price:.2f} con ${MONTO_MXN}"

def do_sell(s, sym, price):
    if sym not in s['h']: return False, f"No tienes {sym}", 0
    entry=s['h'][sym]['e']; amount=s['h'][sym]['a']
    chg=(price/entry-1)*100
    ganancia_mxn = (amount*price*0.998*17.5) - MONTO_MXN
    s['b']+=amount*price*0.998*17.5
    s['total_trades']+=1; s['ganancia_total']+=ganancia_mxn
    s['hs'].insert(0,{'sym':sym,'entry':entry,'exit':price,'pct':round(chg,2),'ganancia':round(ganancia_mxn,2),'fecha':time.strftime('%d/%m %H:%M')})
    s['hs']=s['hs'][:50]
    del s['h'][sym]
    return True, f"💸 VENDIDO {sym} {round(chg,2)}% {'GANASTE' if ganancia_mxn>=0 else 'PERDISTE'} ${round(ganancia_mxn,2)} MXN", ganancia_mxn

async def G(cid, txt, sym_focus=None):
    async with httpx.AsyncClient(timeout=10) as c:
        h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
        link=f'https://{h}/dashboard'
        if sym_focus in ['BTC','ETH','SOL','XRP']:
            kb={'inline_keyboard':[[{'text':f'🟢 COMPRAR {sym_focus} ${MONTO_MXN}','callback_data':f'buy_{sym_focus}'},{'text':f'🔴 VENDER {sym_focus}','callback_data':f'sell_{sym_focus}'}],[{'text':'🟢 AUTO ON','callback_data':'auto_on'},{'text':'🔴 AUTO OFF','callback_data':'auto_off'}],[{'text':'📊 DASHBOARD','url':link}]]}
        else:
            kb={'inline_keyboard':[[{'text':f'🟢 BTC ${MONTO_MXN}','callback_data':'buy_BTC'},{'text':f'🔴 VENDER BTC','callback_data':'sell_BTC'}],[{'text':f'🟢 ETH ${MONTO_MXN}','callback_data':'buy_ETH'},{'text':f'🔴 VENDER ETH','callback_data':'sell_ETH'}],[{'text':f'🟢 SOL ${MONTO_MXN}','callback_data':'buy_SOL'},{'text':f'🔴 VENDER SOL','callback_data':'sell_SOL'}],[{'text':f'🟢 XRP ${MONTO_MXN}','callback_data':'buy_XRP'},{'text':f'🔴 VENDER XRP','callback_data':'sell_XRP'}],[{'text':'🟢 AUTO ON (Compra+Vende solo)','callback_data':'auto_on'},{'text':'🔴 AUTO OFF (Solo alertas 🚨)','callback_data':'auto_off'}],[{'text':'📊 DASHBOARD V950 -3%','url':link}]]}
        try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb,'parse_mode':'Markdown'})
        except: pass

async def ALERTAR_TODOS(msg, sym_focus=None):
    s=L()
    for cid in s.get('alert_users',[]):
        await G(cid, msg, sym_focus)

async def BRAIN_CHECK():
    s=L()
    for sym in ['BTC','ETH','SOL','XRP']:
        an=await AN(sym)
        if not an: continue
        if sym in s['h']:
            chg=(an['p']/s['h'][sym]['e']-1)*100
            # LOGICA V950: +2.5% / -3% / RSI 72
            if chg>=TAKE_PROFIT or chg<=STOP_LOSS or an['rsi']>=72:
                if s.get('auto'):
                    ok,msg,gan=do_sell(s,sym,an['p'])
                    if ok:
                        S(s)
                        await ALERTAR_TODOS(f"🤖 AUTO VENTA {sym} {round(chg,2)}% (TP {TAKE_PROFIT}% SL {STOP_LOSS}%)\n{msg}\nSaldo ${int(s['b'])} MXN\nG/P Total ${round(s['ganancia_total'],2)}", sym)
                        s=L()
                else:
                    await ALERTAR_TODOS(f"🚨 OPORTUNIDAD VENTA {sym}\nTienes {round(chg,2)}% {'ganancia' if chg>0 else 'perdida'}\nPrecio ${an['p']:.2f} RSI {int(an['rsi'])}\nTP {TAKE_PROFIT}% SL {STOP_LOSS}%\n¿Vender?\nSaldo ${int(s['b'])}", sym)
        else:
            if an['rsi']<35:
                if s.get('auto') and s['b']>=MONTO_MXN:
                    ok,msg=do_buy(s,sym,an['p'])
                    if ok:
                        S(s)
                        await ALERTAR_TODOS(f"🤖 AUTO COMPRA {sym} RSI {int(an['rsi'])} ${an['p']:.2f}\n{msg}\nSaldo ${int(s['b'])}", sym)
                        s=L()
                else:
                    await ALERTAR_TODOS(f"🚨 OPORTUNIDAD COMPRA {sym}\nPrecio ${an['p']:.2f} RSI {int(an['rsi'])} {an['senal']}\nBarato, ¿comprar ${MONTO_MXN}?\nAUTO OFF - Solo alerta", sym)

@app.get('/check')
async def check():
    await BRAIN_CHECK()
    return {"ok":f"V950 TP {TAKE_PROFIT}% SL {STOP_LOSS}% check hecho"}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    an_btc, an_eth, an_sol, an_xrp = await asyncio.gather(AN('BTC'), AN('ETH'), AN('SOL'), AN('XRP'))
    def fmt(an, fb):
        if not an: return {'p':fb,'rsi':50,'senal':'NADA','candles':make_candles(fb),'e9':[fb]*100,'e21':[fb]*100,'e50':[fb]*100}
        return an
    an_btc=fmt(an_btc,114800); an_eth=fmt(an_eth,3450); an_sol=fmt(an_sol,172); an_xrp=fmt(an_xrp,1.021)
    import json as js
    btc_c=js.dumps(an_btc['candles']); eth_c=js.dumps(an_eth['candles']); sol_c=js.dumps(an_sol['candles']); xrp_c=js.dumps(an_xrp['candles'])
    btc_e9=js.dumps(an_btc['e9']); btc_e21=js.dumps(an_btc['e21']); btc_e50=js.dumps(an_btc['e50'])
    eth_e9=js.dumps(an_eth['e9']); eth_e21=js.dumps(an_eth['e21']); eth_e50=js.dumps(an_eth['e50'])
    sol_e9=js.dumps(an_sol['e9']); sol_e21=js.dumps(an_sol['e21']); sol_e50=js.dumps(an_sol['e50'])
    xrp_e9=js.dumps(an_xrp['e9']); xrp_e21=js.dumps(an_xrp['e21']); xrp_e50=js.dumps(an_xrp['e50'])
    pos_html="".join([f"<div class=card style=border-color:{'#00ff88' if ( {'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}[k]['p']/v['e']-1)*100>=0 else '#ff4444'}>{k} {round(({'BTC':an_btc,'ETH':an_sol,'SOL':an_sol,'XRP':an_xrp}[k]['p']/v['e']-1)*100,2)}%<br>${ {'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}[k]['p']:.2f}</div>" for k,v in s['h'].items()]) if s['h'] else "<div class=card style=grid-column:1/-1>Sin posiciones</div>"
    hist_html="".join([f"<div class=card style=border-color:{'#00ff88' if h['ganancia']>=0 else '#ff4444'}>{h['sym']} {h['pct']}% <b style=color:{'#00ff88' if h['ganancia']>=0 else '#ff4444'}>${h['ganancia']}</b><br>{h['fecha']}</div>" for h in s['hs'][:8]]) if s.get('hs') else "<div class=card style=grid-column:1/-1>Sin historial - Se conserva real</div>"
    total=s['b']+sum([s['h'][k]['a']*{'BTC':an_btc,'ETH':an_eth,'SOL':an_sol,'XRP':an_xrp}[k]['p']*17.5 for k in s['h']]) if s['h'] else s['b']
    auto_txt="AUTO ON - Compra+Vende solo" if s.get('auto') else "AUTO OFF - Solo alertas 🚨"
    auto_color="#00ff88" if s.get('auto') else "#ffaa00"
    html=f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script><style>body{{background:#0b0e14;color:#d1d4dc;font-family:sans-serif;margin:0}}.header{{padding:12px;background:#151a29;text-align:center;position:sticky;top:0;z-index:10}}.grid4{{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px}}.card{{background:#1a1f30;border:2px solid #2a3446;border-radius:16px;padding:12px;text-align:center;cursor:pointer;font-size:11px}}.card.active{{border-color:#2a7fff!important;background:#1e2a45!important}} #chart{{width:100%;height:460px;background:#0f1420}}.buy{{background:#00ff88;color:#000;padding:14px;width:48%;border:none;border-radius:12px;font-weight:bold}}.sell{{background:#ff4444;color:#fff;padding:14px;width:48%;border:none;border-radius:12px;font-weight:bold}}.stats{{background:#151a29;padding:8px;display:flex;justify-content:space-around;font-size:11px}}</style></head><body><div class=header><b style=color:#2a7fff>V950 TP +2.5% SL -3% $50</b><br><span style="background:{auto_color};color:black;padding:4px 10px;border-radius:10px;font-size:11px">{auto_txt}</span> Saldo <b style=color:#00ff88>${int(s['b'])} MXN</b></div><div class=stats><div>Total <b style=color:#00ff88>${int(total)} MXN</b></div><div>Trades {s.get('total_trades',0)}</div><div>G/P <b style=color:{'#00ff88' if s.get('ganancia_total',0)>=0 else '#ff4444'}>${round(s.get('ganancia_total',0),2)}</b></div><div>SL {STOP_LOSS}%</div></div><div class=grid4><div id=cBTC class=card onclick="loadSym('BTC')">BTC<br><b>${int(an_btc['p'])}</b><br>RSI {int(an_btc['rsi'])}<br>{an_btc['senal']}</div><div id=cETH class=card onclick="loadSym('ETH')">ETH<br><b>${int(an_eth['p'])}</b><br>RSI {int(an_eth['rsi'])}<br>{an_eth['senal']}</div><div id=cSOL class=card onclick="loadSym('SOL')">SOL<br><b>${int(an_sol['p'])}</b><br>RSI {int(an_sol['rsi'])}<br>{an_sol['senal']}</div><div id=cXRP class=card onclick="loadSym('XRP')">XRP<br><b>{an_xrp['p']:.3f}</b><br>RSI {int(an_xrp['rsi'])}<br>{an_xrp['senal']}</div></div><div id=chart></div><div style=text-align:center;padding:10px;display:flex;gap:10px;justify-content:center><button class=buy onclick="trade('buy',current)">🟢 COMPRAR <span id=symTxt>BTC</span> $50</button><button class=sell onclick="trade('sell',current)">🔴 VENDER <span id=symTxt2>BTC</span></button></div><div style=padding:10px><b>📦 Posiciones abiertas</b><div class=grid4>{pos_html}</div></div><div style=padding:10px><b>📜 Historial REAL (ganes o pierdas se conserva)</b><div class=grid4>{hist_html}</div></div><script>let current='BTC'; const DATA={{BTC:{{candles:{btc_c},e9:{btc_e9},e21:{btc_e21},e50:{btc_e50},price:{int(an_btc['p'])}}},ETH:{{candles:{eth_c},e9:{eth_e9},e21:{eth_e21},e50:{eth_e50},price:{int(an_eth['p'])}}},SOL:{{candles:{sol_c},e9:{sol_e9},e21:{sol_e21},e50:{sol_e50},price:{int(an_sol['p'])}}},XRP:{{candles:{xrp_c},e9:{xrp_e9},e21:{xrp_e21},e50:{xrp_e50},price:{an_xrp['p']}}}}}; let chart,candleSeries,e9S,e21S,e50S; function createChart(){{const el=document.getElementById('chart');el.innerHTML='';chart=LightweightCharts.createChart(el,{{width:el.clientWidth,height:460,layout:{{background:{{type:'solid',color:'#0f1420'}},textColor:'#8a8d97'}},grid:{{vertLines:{{color:'#1a1f2e'}},horzLines:{{color:'#1a1f2e'}}}}}});candleSeries=chart.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350'}});e9S=chart.addLineSeries({{color:'#ffcc00',lineWidth:1}});e21S=chart.addLineSeries({{color:'#ef5350',lineWidth:1}});e50S=chart.addLineSeries({{color:'#00ff88',lineWidth:1.2}});}} function toLine(c,a){{let o=[],s=c.length-a.length;if(s<0)s=0;for(let i=0;i<a.length;i++){{let idx=s+i;if(idx>=0&&c[idx]&&a[i])o.push({{time:c[idx].time,value:a[i]}})}}return o;}} function loadSym(s){{current=s;document.getElementById('symTxt').innerText=s;document.getElementById('symTxt2').innerText=s;['BTC','ETH','SOL','XRP'].forEach(x=>document.getElementById('c'+x).classList.remove('active'));document.getElementById('c'+s).classList.add('active');createChart();const d=DATA[s];candleSeries.setData(d.candles);e9S.setData(toLine(d.candles,d.e9));e21S.setData(toLine(d.candles,d.e21));e50S.setData(toLine(d.candles,d.e50));chart.timeScale().fitContent();}} async function trade(a,s){{if(!s)s=current;let r=await fetch('/trade/'+a+'?sym='+s+'&t='+Date.now());let j=await r.json();alert(j.msg+' Saldo $'+j.saldo);location.reload();}} createChart();loadSym('BTC');</script></body></html>"""
    return HTMLResponse(html)

@app.get('/trade/{action}')
async def trade_api(action: str, sym: str):
    s=L(); an=await AN(sym.upper())
    if action=='buy': ok,msg=do_buy(s,sym.upper(),an['p'])
    else: ok,msg,_=do_sell(s,sym.upper(),an['p'])
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
        cq=q['callback_query']; cid=cq['message']['chat']['id']; data=cq.get('data',''); s=L()
        if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
        if data=='auto_on': s['auto']=True; S(s); await G(cid,f'🚀 AUTO ON TP {TAKE_PROFIT}% SL {STOP_LOSS}%\nCompra y vende solo\nSaldo ${int(s["b"])}', None)
        elif data=='auto_off': s['auto']=False; S(s); await G(cid,f'🔴 AUTO OFF - Solo alertas 🚨\nTP {TAKE_PROFIT}% SL {STOP_LOSS}%\nTe avisaré oportunidades\nSaldo ${int(s["b"])}', None)
        elif data.startswith('buy_'):
            sym=data.split('_')[1]; an=await AN(sym); ok,msg=do_buy(s,sym,an['p'])
            if ok: S(s); await G(cid,f'{msg}\nSaldo ${int(s["b"])}', sym)
            else: await G(cid,f'⚠️ {msg}', sym)
        elif data.startswith('sell_'):
            sym=data.split('_')[1]; an=await AN(sym); ok,msg,_=do_sell(s,sym,an['p'])
            if ok: S(s); await G(cid,f'{msg}\nSaldo ${int(s["b"])} G/P ${round(s["ganancia_total"],2)}', sym)
            else: await G(cid,f'⚠️ {msg}', sym)
        elif data.startswith('info_'):
            sym=data.split('_')[1]; an=await AN(sym); await G(cid,f'*{sym} ${an["p"]:.2f}* RSI {int(an["rsi"])} {an["senal"]}', sym)
        return {'ok':1}
    msg=q.get('message',{}); cid=msg.get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(msg.get('text') or '').upper()
    if 'RESET' in t: S({'b':1000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users']}); await G(cid,'♻️ RESET $1000 V950', None); return {'ok':1}
    if 'AUTO ON' in t: s['auto']=True; S(s); await G(cid,f'🚀 AUTO ON TP {TAKE_PROFIT}% SL {STOP_LOSS}%\nSaldo ${int(s["b"])}', None); return {'ok':1}
    if 'AUTO OFF' in t: s['auto']=False; S(s); await G(cid,f'🔴 AUTO OFF - Solo alertas 🚨 TP {TAKE_PROFIT}% SL {STOP_LOSS}%\nSaldo ${int(s["b"])}', None); return {'ok':1}
    if t in ['BTC','ETH','SOL','XRP']: an=await AN(t); await G(cid,f'*{t} ${an["p"]:.2f}* RSI {int(an["rsi"])} {an["senal"]}\nTP {TAKE_PROFIT}% SL {STOP_LOSS}%', t); return {'ok':1}
    if 'PORTAFOLIO' in t or 'BALANCE' in t:
        total=s['b']+sum([s['h'][k]['a']*(await P(k))*17.5 for k in s['h']]) if s['h'] else s['b']
        txt=f'V950 TP {TAKE_PROFIT}% SL {STOP_LOSS}%\nSaldo ${int(s["b"])} Total ${int(total)} G/P ${round(s.get("ganancia_total",0),2)} Trades {s.get("total_trades",0)}\nAUTO {"ON" if s.get("auto") else "OFF"}\n'
        await G(cid,txt, None); return {'ok':1}
    await G(cid,f'V950 TP +{TAKE_PROFIT}% SL {STOP_LOSS}% $50\nSaldo ${int(s["b"])}\nAUTO ON = compra+vende solo\nAUTO OFF = solo alertas 🚨\nPORTAFOLIO = historial real', None)
    return {'ok':1}
