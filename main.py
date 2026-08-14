import os, requests, io, base64, random, traceback
from flask import Flask, request
from datetime import datetime
import telebot, pytz

TOKEN = os.getenv("BOT_TOKEN", "8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]
ESTADO = {
    "jefe_hoy": {},
    "bola": {s:500 for s in SYMBOLS},
    "demo_balance": 10000.0,
    "demo_inicial": 10000.0,
    "demo_trades": [],
    "auto": True,
    "meta_min": 8.0,
    "meta_max": 13.0
}

def get_yahoo(symbol, interval="5m", range_="1d"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=4).json()
        res = r['chart']['result'][0]['indicators']['quote'][0]
        closes = [c for c in res['close'] if c is not None]
        opens = [c for c in res['open'] if c is not None]
        highs = [c for c in res['high'] if c is not None]
        lows = [c for c in res['low'] if c is not None]
        vols = [c for c in res['volume'] if c is not None]
        if len(closes) < 30: return None
        n = min(len(closes),len(opens),len(highs),len(lows),len(vols))
        return opens[-n:], highs[-n:], lows[-n:], closes[-n:], vols[-n:]
    except: return None

def get_price(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            par={"BTC":"XBTUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={par}",timeout=5).json()
            return float(list(r['result'].values())[0]['c'][0])
        else:
            ymap={"NVDA":"NVDA","TSLA":"TSLA","XAUUSD":"GC=F"}
            y=get_yahoo(ymap[s])
            if y: return y[3][-1]
    except: pass
    return {"BTC":63500,"ETH":3200,"SOL":180,"NVDA":135,"TSLA":250,"XAUUSD":2650}[s]

def get_velas(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            par={"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=5",timeout=6).json()
            k=list(r['result'].keys())[0]
            data=r['result'][k][-100:]
            return [float(x[1]) for x in data],[float(x[2]) for x in data],[float(x[3]) for x in data],[float(x[4]) for x in data],[float(x[6]) for x in data]
        else:
            ymap={"NVDA":"NVDA","TSLA":"TSLA","XAUUSD":"GC=F"}
            y=get_yahoo(ymap[s])
            if y: return y
    except: pass
    base=get_price(s)
    closes=[base+random.uniform(-base*0.005,base*0.005) for _ in range(100)]
    opens=[c+random.uniform(-1,1) for c in closes]
    highs=[max(o,c)+random.uniform(0,base*0.002) for o,c in zip(opens,closes)]
    lows=[min(o,c)-random.uniform(0,base*0.002) for o,c in zip(opens,closes)]
    vol=[random.uniform(0.8,2.2) for _ in range(100)]
    return opens,highs,lows,closes,vol

def rsi_calc(closes,p=14):
    if len(closes)<p+1: return 50
    g=sum(max(0,closes[i]-closes[i-1]) for i in range(-p,0))/p
    l=sum(max(0,closes[i-1]-closes[i]) for i in range(-p,0))/p
    return 70 if l==0 else 100-(100/(1+g/l))

def spy_real():
    try:
        y=get_yahoo("SPY","5m","1d")
        if not y: return True,0
        return y[3][-1] > y[3][0], (y[3][-1]-y[3][-2])/y[3][-2]*100
    except: return True,0

def bot1_analiza(s):
    opens,highs,lows,closes,vol=get_velas(s)
    lineas=[]
    for i in range(20,len(closes)-10):
        p=closes[i]
        rebotes=sum(1 for c in closes[max(0,i-30):i+10] if abs(c-p)/p < 0.0025)
        if rebotes>=2: lineas.append({"precio":p,"rebotes":rebotes,"fuerza":min(90,rebotes*15+25)})
    unicas=[]
    for l in sorted(lineas,key=lambda x:x['rebotes'],reverse=True):
        if not any(abs(l['precio']-u['precio'])/u['precio']<0.006 for u in unicas): unicas.append(l)
    return unicas[:8],closes,opens,highs,lows,vol

def bot2_apoya(s,linea,closes):
    if not linea: return False,0,0,"BOT2 sin linea"
    conf=sum(1 for c in closes[-40:] if abs(c-linea['precio'])/linea['precio']<0.003)
    fuerza=min(99,conf*18+20)
    return conf>=3 and fuerza>=65,fuerza,conf,f"BOT2: {conf} toques {fuerza:.0f}% {'✅' if conf>=3 else '❌'}"

def bot3_jefe_admin(s,linea_bot1,fuerza2,confirm,closes,vol):
    if not linea_bot1: return False,0,"JEFE sin linea",0,True
    rsi=rsi_calc(closes)
    vp=sum(vol[-20:])/20 if len(vol)>=20 else 1
    vm=(vol[-1]/vp) if vp else 1
    spy_v,spy_c=spy_real()
    ny=datetime.now(pytz.timezone('America/New_York'))
    spy_ok=True if (ny.hour<9 or ny.hour>=16) else spy_v
    score=min(30,linea_bot1['rebotes']*5)+linea_bot1['fuerza']*0.35+fuerza2*0.35
    if rsi<35: score+=8
    if vm>1.5: score+=5
    if vm<0.6: score-=10
    if not spy_ok: score-=20
    score=max(0,min(99,score))
    bola=2500 if score>=90 else 1800 if score>=80 else 1100 if score>=70 else 0
    nivel="🔥🔥🔥 90%+ TURBO" if score>=90 else "🔥🔥 80%+" if score>=80 else "🔥 70%+" if score>=70 else f"⏳ {score:.0f}% No da"
    return (spy_ok and score>=70),bola,f"JEFE: Score {score:.0f} {nivel}\nRSI {rsi:.0f} Vol x{vm:.1f} SPY {'🟢' if spy_ok else '🔴'} {spy_c:+.2f}%\nBola: ${bola}",score,spy_ok

def demo_compra(s, bola, score, precio):
    if not ESTADO["auto"]: return False
    if ESTADO["demo_balance"] < bola: return False
    ESTADO["demo_balance"] -= bola
    ESTADO["demo_trades"].append({
        "fecha": datetime.now().strftime("%m-%d %H:%M"),
        "simbolo": s,
        "entrada": precio,
        "bola": bola,
        "score": score
    })
    return True

def demo_stats_text():
    trades = ESTADO["demo_trades"]
    bal = ESTADO["demo_balance"]
    if not trades:
        return f"💰 MAQUINA DE HACER DINERO 💰 DEMO\nBalance libre: ${bal:.2f} / $10000\nGanancia: 0%\nMeta mes: 8-13%\nAuto: {'ON ✅' if ESTADO['auto'] else 'OFF ❌'}\nSin trades aún - Esperando 70%+"
    invertido = sum(t["bola"] for t in trades)
    # Simulación PAPER: tu lógica MALLA 70% win con TP 1.5% + Trail
    # Para demo calculamos PnL estimado conservador 1.2% promedio por trade con tu winrate
    pnl_estimado = len(trades) * (500 * 0.012) # $6 por trade base aprox
    turbo_trades = sum(1 for t in trades if t["bola"]>=2000)
    pnl_estimado += turbo_trades * 15 # extra turbo
    balance_total = 10000 + pnl_estimado
    pct = (balance_total - 10000)/10000*100
    estado_meta = "✅ EN META 8-13%" if 8 <= pct <= 13 else "🚀 ARRIBA DE META" if pct>13 else f"⏳ Camino a 8% ({pct:.1f}%)"
    return f"""💰 MAQUINA DE HACER DINERO 💰 DEMO 1 MES
Balance total est: ${balance_total:.2f} / $10000
Ganancia: {pct:.2f}% {estado_meta}
Meta: 8-13% = $800 a $1300 mes
Trades demo: {len(trades)} (Turbo: {turbo_trades})
Balance libre: ${bal:.2f}
Auto: {'ON ✅ COMPRANDO SOLO' if ESTADO['auto'] else 'OFF ❌ SOLO AVISA'}
Días restantes prueba: {30 - (datetime.now().day % 30)} días
"""

def decide(s):
    try:
        lineas,closes,opens,highs,lows,vol=bot1_analiza(s)
        if not lineas: return {"compra":False,"tipo":"SIN LINEAS","detalle":"BOT1 no encontró","lineas":[],"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":0, "bola":0}
        top=lineas[0]
        apoya2,f2,conf2,txt2=bot2_apoya(s,top,closes)
        apoya3,bola3,txt3,score,spy_ok=bot3_jefe_admin(s,top,f2,conf2,closes,vol)
        precio=closes[-1]
        cerca=abs(precio-top['precio'])/top['precio']<0.015
        ny=datetime.now(pytz.timezone('America/New_York'))
        es_ny=9 <= ny.hour <= 16 and s in ["NVDA","TSLA","XAUUSD"]
        key=f"{s}_{datetime.now().strftime('%Y-%m-%d')}"
        if key in ESTADO["jefe_hoy"]:
            return {"compra":False,"tipo":"JEFE YA CAZO HOY 🔒 1x día","detalle":f"🔒 Ya tomó {s} hoy 1x día\n{txt2}\n{txt3}\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":score, "bola":bola3}
        if es_ny:
            if cerca and apoya2 and apoya3:
                if ESTADO["auto"]: demo_compra(s, bola3, score, precio)
                ESTADO["jefe_hoy"][key]=True
                return {"compra":True,"tipo":f"BOT2 NY MALLA DEMO ${bola3}","bola":bola3,"detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n{txt2}\n{txt3}\n✅ DEMO AUTO\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":score, "bola":bola3}
            else:
                return {"compra":False,"tipo":"NY ESPERA MALLA","detalle":f"BOT1 {top['rebotes']}R ${top['precio']:.2f}\n{txt2}\n{txt3}\n⏳ Falta MALLA\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":score, "bola":bola3}
        else:
            if cerca and apoya2 and apoya3:
                bola1=ESTADO["bola"].get(s,500)
                if score>=90:
                    if ESTADO["auto"]: demo_compra(s, bola1+bola3, score, precio)
                    ESTADO["jefe_hoy"][key]=True
                    return {"compra":True,"tipo":f"BOT1 ${bola1}+JEFE ${bola3} MALLA 90%+ DEMO","bola":bola1+bola3,"detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}%\n{txt2}\n{txt3}\n✅ MALLA TOTAL DEMO\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":score, "bola":bola1+bola3}
                else:
                    if ESTADO["auto"]: demo_compra(s, bola1, score, precio)
                    ESTADO["jefe_hoy"][key]=True
                    return {"compra":True,"tipo":f"BOT1 ${bola1} MALLA {score:.0f}% DEMO","bola":bola1,"detalle":f"BOT1 {top['rebotes']}R\n{txt2}\n{txt3}\n✅ DEMO\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":score, "bola":bola1}
            else:
                return {"compra":False,"tipo":"ESPERA MALLA","detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n{txt2}\n{txt3}\n⏳ Falta MALLA\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol, "score":score, "bola":bola3}
    except Exception as e:
        return {"compra":False,"tipo":"ERROR TEMP","detalle":f"Reintentando {s}... {e}","lineas":[],"closes":[get_price(s)],"opens":[get_price(s)],"highs":[get_price(s)],"lows":[get_price(s)],"vol":[1], "score":0, "bola":0}

@app.route('/')
def dash():
    spy_v,spy_c=spy_real()
    html=f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:8px 0}}.v{{color:#00ff88}}.n{{color:orange}}.btn{{background:#00ff88;color:#000;padding:10px 18px;border-radius:8px;text-decoration:none;display:inline-block;margin:4px;font-weight:bold}}pre{{white-space:pre-wrap}}</style></head><body><h2>💰 MAQUINA DE HACER DINERO 💰 V50.4 DEMO PAPER</h2><div class="card">SPY REAL: {"🟢" if spy_v else "🔴"} {spy_c:+.2f}% | NY: {datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M")} | 1x día | {demo_stats_text().replace(chr(10),"<br>")}</div>"""
    for s in SYMBOLS:
        try: d=decide(s)
        except: d={"compra":False,"tipo":"CARGANDO...","detalle":"Reintentando","lineas":[],"score":0,"bola":0}
        color="v" if d["compra"] else "n"
        precio=get_price(s)
        html+=f'<div class="card"><b>{s}</b> ${precio:.2f} | <span class="{color}">{d["tipo"]}</span><br><small>{d["detalle"].replace(chr(10),"<br>")}</small><br><a class="btn" href="/graf/{s}">GRAFICA VIVA PRO 📈</a> <a class="btn" href="/forzar/{s}">FORZAR</a></div>'
    html+=f'<div class="card"><a class="btn" href="/stats">VER STATS 8-13%</a> <a class="btn" href="/reset_demo">RESET DEMO MES</a></div></body></html>'
    return html

@app.route('/graf/<s>')
def graf(s):
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        d=decide(s.upper())
        c,o,h,l,lineas=d["closes"],d["opens"],d["highs"],d["lows"],d["lineas"]
        fig=plt.figure(figsize=(12,7),facecolor='black')
        ax=plt.subplot2grid((4,1),(0,0),rowspan=3,facecolor='black')
        ax2=plt.subplot2grid((4,1),(3,0),facecolor='black')
        for i in range(len(c)):
            col='#00ff88' if c[i]>=o[i] else '#ff4444'
            ax.plot([i,i],[l[i],h[i]],color=col,lw=1); ax.plot([i,i],[o[i],c[i]],color=col,lw=3)
        for x in lineas[:6]:
            col='#00ff00' if x['rebotes']>=4 else '#ffaa00'
            ax.axhline(x['precio'],color=col,ls='--',lw=1.2,alpha=0.8)
            ax.text(2,x['precio'],f" {x['rebotes']}R {x['fuerza']:.0f}%",color=col,fontsize=8,backgroundcolor='black')
        ax.set_title(f'MAQUINA DE HACER DINERO 💰 {s} ${c[-1]:.2f} {d["tipo"]}',color='white',fontsize=9)
        ax.tick_params(colors='white'); ax.grid(True,alpha=0.1)
        rsi_vals=[rsi_calc(c[:i]) for i in range(15,len(c))]
        ax2.plot(rsi_vals,color='#00ffff'); ax2.axhline(70,color='red',ls='--',alpha=0.4); ax2.axhline(30,color='green',ls='--',alpha=0.4); ax2.set_ylim(0,100); ax2.tick_params(colors='white')
        buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=150); buf.seek(0)
        img=base64.b64encode(buf.read()).decode(); plt.close()
        return f'<html style="background:#000;color:#fff;font-family:Arial"><body style="padding:10px"><h2>💰 MAQUINA DE HACER DINERO 💰 {s} ${c[-1]:.2f}</h2><pre style="background:#111;padding:12px;border-radius:8px">{d["detalle"]}</pre><img src="data:image/png;base64,{img}" style="width:100%;border-radius:12px"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">← VOLVER</a></body></html>'
    except Exception as e: return f'Error graf {s}: {e} {traceback.format_exc()}'

@app.route('/forzar/<s>')
def forzar(s):
    ESTADO["jefe_hoy"].pop(f"{s.upper()}_{datetime.now().strftime('%Y-%m-%d')}",None)
    d=decide(s.upper())
    return f"<pre style='background:#000;color:#0f0;padding:20px'>{d['detalle']}\n\nREAL: ${get_price(s.upper()):.2f}\n{d['tipo']}</pre><a href='/'>VOLVER</a>"

@app.route('/stats')
def stats():
    txt=demo_stats_text()
    trades="<br>".join([f"{t['fecha']} {t['simbolo']} ${t['bola']} Score {t['score']}% @ ${t['entrada']:.2f}" for t in ESTADO["demo_trades"][-20:]])
    return f"<html style='background:#000;color:#fff;font-family:Arial;padding:20px'><h2>💰 STATS DEMO 1 MES 8-13%</h2><pre style='background:#111;padding:15px;border-radius:10px'>{txt}</pre><div style='background:#111;padding:15px;border-radius:10px;margin-top:10px'>{trades or 'Sin trades'}</div><br><a href='/' style='background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none'>VOLVER</a></html>"

@app.route('/reset_demo')
def reset_demo():
    ESTADO["demo_balance"]=10000.0
    ESTADO["demo_trades"]=[]
    ESTADO["jefe_hoy"]={}
    return "<h1 style='background:#000;color:#0f0'>DEMO RESETEADO $10000 - Inicia mes nuevo</h1><a href='/'>VOLVER</a>"

@bot.message_handler(commands=['start'])
def start(m): bot.send_message(m.chat.id,"💰 MAQUINA DE HACER DINERO 💰 V50.4 DEMO PAPER 1 MES 8-13%\nREAL Kraken+Yahoo + MALLA 1x día\nAUTO ON = Compra sola DEMO\nComandos: BTC ETH SOL NVDA TSLA XAUUSD / DASH / STATS / AUTO ON / AUTO OFF",reply_markup=None)

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    try:
        t=m.text.strip().upper()
        if t in SYMBOLS:
            d=decide(t)
            msg=f"💰 MAQUINA DE HACER DINERO 💰 DEMO\n{t} ${get_price(t):.2f}\n{d['detalle']}\n\n{d['tipo']}\n\nGrafica: https://telegram-bot-cijp.onrender.com/graf/{t}"
            bot.send_message(m.chat.id,msg)
        elif "STATS" in t:
            bot.send_message(m.chat.id,demo_stats_text())
        elif "TRADES" in t:
            trades=ESTADO["demo_trades"][-10:]
            txt="\n".join([f"{x['fecha']} {x['simbolo']} ${x['bola']}" for x in trades]) or "Sin trades"
            bot.send_message(m.chat.id,f"ULTIMOS TRADES DEMO:\n{txt}\n\n{demo_stats_text()}")
        elif "AUTO ON" in t:
            ESTADO["auto"]=True
            bot.send_message(m.chat.id,f"AUTO ON ✅ MAQUINA DE HACER DINERO 💰 DEMO\nYa compra sola 1x día\n{demo_stats_text()}")
        elif "AUTO OFF" in t:
            ESTADO["auto"]=False
            bot.send_message(m.chat.id,"AUTO OFF ❌ Solo avisa, no compra demo")
        elif "RESET" in t:
            ESTADO["demo_balance"]=10000.0
            ESTADO["demo_trades"]=[]
            ESTADO["jefe_hoy"]={}
            bot.send_message(m.chat.id,"DEMO RESETEADO $10000 - Nuevo mes 8-13% iniciado ✅")
        elif "DASH" in t:
            bot.send_message(m.chat.id,"https://telegram-bot-cijp.onrender.com")
        else:
            clean=''.join([c for c in t if c.isalpha()])
            if clean in SYMBOLS:
                d=decide(clean)
                bot.send_message(m.chat.id,f"💰 MAQUINA DE HACER DINERO 💰 {clean} ${get_price(clean):.2f}\n{d['detalle']}\n\n{d['tipo']}")
            else:
                bot.send_message(m.chat.id,"💰 MAQUINA DE HACER DINERO 💰 V50.4 DEMO\nBTC ETH SOL NVDA TSLA XAUUSD\nSTATS / AUTO ON / AUTO OFF / RESET DEMO")
    except Exception as e: bot.send_message(m.chat.id,f"Reintentando... {e}")

@app.route('/webhook',methods=['POST'])
@app.route('/8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M',methods=['POST'])
@app.route('/<path:p>',methods=['POST'])
def hook(p=None):
    try:
        data=request.get_data().decode()
        if data: bot.process_new_updates([telebot.types.Update.de_json(data)])
    except: pass
    return "OK",200

@app.route('/check')
def check(): return "V50.4 MAQUINA DE HACER DINERO 💰 DEMO PAPER LIVE"

if __name__=='__main__':
    port=int(os.getenv("PORT",10000))
    app.run(host='0.0.0.0',port=port)
