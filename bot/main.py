import os, json, httpx, asyncio, time, datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'

def L():
    try:
        if os.path.exists(F):
            d = json.load(open(F))
            if 'b' not in d: d['b'] = 2000
            if 'h' not in d: d['h'] = {}
            if 'hs' not in d: d['hs'] = []
            if 'auto' not in d: d['auto'] = False
            if 'ganancia_total' not in d: d['ganancia_total'] = 0
            if 'total_trades' not in d: d['total_trades'] = 0
            if 'alert_users' not in d: d['alert_users'] = []
            if 'historial_diario' not in d: d['historial_diario'] = []
            if 'ganancia_hoy' not in d: d['ganancia_hoy'] = 0
            if 'trades_hoy' not in d: d['trades_hoy'] = 0
            if 'fecha_hoy' not in d: d['fecha_hoy'] = time.strftime('%Y-%m-%d')
            if 'inicial' not in d: d['inicial'] = 2000
            if d['b'] == 1000 and d['ganancia_total'] == 0 and len(d['h']) == 0:
                d['b'] = 2000
            return d
    except:
        pass
    return {'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000}

def S(s):
    try:
        json.dump(s, open(F,'w'))
    except:
        pass

BASE = 50
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f'https://min-api.cryptocompare.com/data/price?fsym={m}&tsyms=USD')
            return float(r.json()['USD'])
    except:
        return 100.0

async def CANDLES(sym):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://min-api.cryptocompare.com/data/v2/histohour?fsym={sym}&tsym=USD&limit=100')
            d = r.json()['Data']['Data']
            return [float(x['close']) for x in d if x['close']>0]
    except:
        return []

def ema(a,n):
    if len(a) < n: return []
    k = 2/(n+1)
    s = sum(a[:n])/n
    o = [s]
    for x in a[n:]:
        o.append(x*k + o[-1]*(1-k))
    return o

def rsi(a):
    if len(a) < 15: return 50
    g = l = 0
    for i in range(len(a)-14, len(a)):
        d = a[i]-a[i-1]
        if d > 0: g += d
        else: l -= d
    return 100-100/(1+g/l) if l!=0 else 80

async def SCORE(sym):
    cl = await CANDLES(sym)
    pr = await P(sym)
    if not cl or len(cl) < 50:
        return {'p':pr,'score':0,'rsi':50}
    cl[-1] = pr
    e9 = ema(cl,9)
    e21 = ema(cl,21)
    e50 = ema(cl,50)
    r = rsi(cl)
    sc = 0
    if 20 <= r <= 40: sc += 40
    elif 40 < r <= 50: sc += 15
    if e9 and e21 and e9[-1] > e21[-1]: sc += 25
    if e9 and cl[-1] > e9[-1]: sc += 15
    if e50 and abs(cl[-1]-e50[-1])/cl[-1] < 0.025: sc += 20
    if len(cl) > 2 and cl[-1] > cl[-2] and cl[-2] < cl[-3]: sc += 10
    return {'p':pr,'score':min(100,sc),'rsi':r}

def monto_dinamico(s):
    base = BASE
    if s['ganancia_total'] > 200: base = 70
    if s['ganancia_total'] > 500: base = 100
    if s['ganancia_total'] > 1000: base = 150
    return base

def BUY(s,sym,price,monto):
    if s['b'] < monto: return False
    if sym not in s['h']:
        s['h'][sym] = {'a':(monto/17.5*0.998)/price,'e':price,'niveles':1,'invertido':monto,'tp1':False,'tp2':False}
    else:
        extra = (monto/17.5*0.998)/price
        total_a = s['h'][sym]['a'] + extra
        avg = (s['h'][sym]['e']*s['h'][sym]['a'] + price*extra)/total_a
        s['h'][sym]['a'] = total_a
        s['h'][sym]['e'] = avg
        s['h'][sym]['niveles'] += 1
        s['h'][sym]['invertido'] += monto
    s['b'] -= monto
    return True

def SELL(s,sym,price,pct):
    if sym not in s['h']: return 0
    amt = s['h'][sym]['a']
    inv = s['h'][sym]['invertido']
    ent = s['h'][sym]['e']
    sell_amt = amt*pct/100
    rec = sell_amt*price*0.998*17.5
    gan = rec - inv*pct/100
    s['b'] += rec
    s['ganancia_hoy'] += gan
    if pct >= 99:
        s['total_trades'] += 1
        s['trades_hoy'] += 1
        s['ganancia_total'] += gan
        s['hs'].insert(0,{'sym':sym,'ganancia':round(gan,2),'pct':round((price/ent-1)*100,2),'fecha':time.strftime('%d/%m %H:%M')})
        del s['h'][sym]
    else:
        s['h'][sym]['a'] = amt - sell_amt
        s['h'][sym]['invertido'] = inv*(1-pct/100)
    return gan

async def SEND(cid,txt):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt})
        except:
            pass

async def check_fecha(s):
    hoy = time.strftime('%Y-%m-%d')
    if s['fecha_hoy']!= hoy:
        s['historial_diario'].insert(0,{'fecha':s['fecha_hoy'],'ganancia':round(s['ganancia_hoy'],2),'trades':s['trades_hoy']})
        s['historial_diario'] = s['historial_diario'][:7]
        s['ganancia_hoy'] = 0
        s['trades_hoy'] = 0
        s['fecha_hoy'] = hoy
        S(s)
    return s

async def PUTERO():
    s = L()
    s = await check_fecha(s)
    btc = await SCORE('BTC')
    btc_ok = btc['score'] >= 35

    for sym in MONEDAS:
        an = await SCORE(sym) if sym!= 'BTC' else btc
        monto = monto_dinamico(s)

        if sym in s['h']:
            chg = (an['p']/s['h'][sym]['e']-1)*100
            niv = s['h'][sym]['niveles']
            if chg >= 3.5:
                g = SELL(s,sym,an['p'],100)
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"💰💰 PUTERO +3.5% {sym} {round(chg,2)}% GAN ${round(g,2)}\nSaldo ${int(s['b'])}")
                s = L()
            elif chg >= 2.0 and not s['h'][sym].get('tp2'):
                g = SELL(s,sym,an['p'],40)
                s['h'][sym]['tp2'] = True
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"💸 TP2 +2% {sym} 40% ${round(g,2)}")
                s = L()
            elif chg >= 1.0 and not s['h'][sym].get('tp1'):
                g = SELL(s,sym,an['p'],30)
                s['h'][sym]['tp1'] = True
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"✅ TP1 +1% {sym} 30% ${round(g,2)}")
                s = L()
            elif chg <= -2.0 and niv == 1 and s['b'] >= monto and an['score'] >= 55:
                BUY(s,sym,an['p'],monto)
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"🔥 PIRAMIDE {sym} {round(chg,2)}% +${monto}")
                s = L()
            elif chg <= -4.0 and niv == 2 and s['b'] >= monto*2:
                BUY(s,sym,an['p'],monto*2)
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"🔥🔥 PIRAMIDE X2 {sym} +${monto*2}")
                s = L()
            elif chg <= -6.0:
                g = SELL(s,sym,an['p'],100)
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"🛑 SL -6% {sym} ${round(g,2)} Saldo ${int(s['b'])}")
                s = L()
        else:
            if an['score'] >= 70 and btc_ok and s['b'] >= monto and len(s['h']) < 5:
                BUY(s,sym,an['p'],monto)
                S(s)
                for cid in s['alert_users']:
                    await SEND(cid,f"🚀 PUTERO ENTRA {sym} SCORE {an['score']} ${an['p']:.2f} Monto ${monto}")
                s = L()

    now_mx = datetime.datetime.utcnow() - datetime.timedelta(hours=6)
    if now_mx.hour == 22 and now_mx.minute < 5:
        await reporte_diario_logic()

async def reporte_diario_logic():
    s = L()
    s = await check_fecha(s)
    total = s['b']
    for k,v in s['h'].items():
        pr = await P(k)
        total += v['a']*pr*17.5
    inicial = s.get('inicial',2000)
    gan_total = total - inicial
    pct_total = (total/inicial-1)*100

    hist_txt = ""
    for h in s['historial_diario'][:6]:
        hist_txt += f"{h['fecha']} {h['ganancia']:+.2f} MXN {h['trades']} trades\n"
    if not hist_txt:
        hist_txt = "Primer dia corriendo"

    pos_txt = ""
    for k,v in s['h'].items():
        pr = await P(k)
        pos_txt += f"{k} {round((pr/v['e']-1)*100,2)}% "
    if not pos_txt:
        pos_txt = "Ninguna"

    msg = f"""📊 REPORTE DIARIO 10PM - V1002 PUTERO DEMO $2000

💰 Saldo disponible: ${int(s['b'])} MXN
📦 En posiciones: ${int(total - s['b'])} MXN
💵 Total: ${int(total)} MXN
📈 Ganancia total: ${round(gan_total,2)} MXN ({round(pct_total,2)}%)
🔄 Ganancia HOY: ${round(s['ganancia_hoy'],2)} MXN
🎯 Trades HOY: {s['trades_hoy']}
📊 Trades totales: {s['total_trades']}

📅 Ultimos dias:
{hist_txt}
Pos abiertas: {len(s['h'])}/5 {pos_txt}

Mañana seguimos 🚀
"""
    for cid in s.get('alert_users',[]):
        await SEND(cid, msg)
    return msg

@app.get('/check')
async def check():
    await PUTERO()
    return {"ok":"V1002 $2000 PUTERO"}

@app.get('/reporte_diario')
async def reporte_diario():
    msg = await reporte_diario_logic()
    return {"reporte":msg}

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s = L()
    txt = ""
    for sym in MONEDAS:
        an = await SCORE(sym)
        col = "#00ff88" if an['score']>=70 else "#ffaa00" if an['score']>=50 else "#555"
        txt += f"<div style=border:1px solid {col};padding:6px;margin:4px;border-radius:8px;background:#1a1f30>{sym} ${an['p']:.2f} SCORE <b style=color:{col}>{an['score']}</b> RSI {int(an['rsi'])}</div>"
    total = s['b']
    for k,v in s['h'].items():
        pr = await P(k)
        total += v['a']*pr*17.5
    pos = "".join([f"<div style=background:#1a1f30;margin:3px;padding:6px;border-radius:6px>{k} x{v['niveles']} inv ${v['invertido']} {round(((await P(k))/v['e']-1)*100,2)}%</div>" for k,v in s['h'].items()]) or "Sin pos"
    hist = "".join([f"<div style=background:#1a1f30;margin:2px;padding:4px;font-size:11px>{h['fecha']} {h['ganancia']} MXN {h['trades']}t</div>" for h in s['historial_diario'][:7]])
    html = f"<html><body style=background:#0b0e14;color:#fff;font-family:sans-serif;padding:10px><h3>V1002 PUTERO DEMO $2000</h3>Saldo ${int(s['b'])} Total ${int(total)} G/P ${round(total-2000,2)} ({round((total/2000-1)*100,2)}%)<br>HOY ${round(s['ganancia_hoy'],2)} Trades hoy {s['trades_hoy']}<br>{txt}<br>Pos {pos}<br>Historial 7 dias {hist}<br><br><a href='/reporte_diario' style=color:#00ff88>Forzar reporte 10pm</a></body></html>"
    return HTMLResponse(html)

@app.api_route('/', methods=['GET','POST'])
@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try:
        q = await req.json()
    except:
        q = {}
    cid = q.get('message',{}).get('chat',{}).get('id')
    if not cid:
        return {'ok':1}
    s = L()
    if cid not in s['alert_users']:
        s['alert_users'].append(cid)
        S(s)
    t = (q.get('message',{}).get('text') or '').upper()
    if 'RESET' in t:
        S({'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users'],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000})
        await SEND(cid,"♻️ RESET DEMO $2000 PUTERO")
        return {'ok':1}
    if 'AUTO ON' in t:
        s['auto'] = True
        S(s)
        await SEND(cid,f"🔥 PUTERO $2000 ON - Reporte 10pm activo")
        return {'ok':1}
    if 'AUTO OFF' in t:
        s['auto'] = False
        S(s)
        await SEND(cid,"OFF")
        return {'ok':1}
    if 'REPORTE' in t:
        msg = await reporte_diario_logic()
        await SEND(cid,msg)
        return {'ok':1}
    await SEND(cid,f"V1002 DEMO $2000\nSaldo ${int(s['b'])} G/P ${round(s['ganancia_total'],2)}\nHOY ${round(s['ganancia_hoy'],2)} Trades hoy {s['trades_hoy']}\nComandos: AUTO ON, AUTO OFF, REPORTE, RESET")
    return {'ok':1}
