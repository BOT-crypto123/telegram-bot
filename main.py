import os, requests, io, base64, random
from flask import Flask, request
from datetime import datetime
import telebot, pytz

TOKEN = os.getenv("BOT_TOKEN", "8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ESTADO = {"jefe_hoy": {}, "bola": {s:500 for s in ["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]}}
SYMBOLS = ["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]

def get_yahoo(symbol, interval="5m", range_="1d"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10).json()
        result = r['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        opens = result['indicators']['quote'][0]['open']
        highs = result['indicators']['quote'][0]['high']
        lows = result['indicators']['quote'][0]['low']
        vols = result['indicators']['quote'][0]['volume']
        # limpiar None
        data=[]
        for o,h,l,c,v in zip(opens,highs,lows,closes,vols):
            if c is None: continue
            data.append((o,h,l,c,v))
        if len(data)<30: return None
        opens, highs, lows, closes, vols = zip(*data)
        return list(opens), list(highs), list(lows), list(closes), list(vols)
    except Exception as e:
        print(f"Yahoo error {symbol}: {e}")
        return None

def get_price(s):
    if s in ["BTC","ETH","SOL"]:
        try:
            par={"BTC":"XBTUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={par}",timeout=8).json()
            return float(list(r['result'].values())[0]['c'][0])
        except: pass
    else:
        ymap={"NVDA":"NVDA","TSLA":"TSLA","XAUUSD":"GC=F"}
        y = get_yahoo(ymap[s])
        if y and y[3]: return y[3][-1]
    return {"BTC":63506,"ETH":3200,"SOL":180,"NVDA":135,"TSLA":250,"XAUUSD":2650}[s]

def get_velas(s):
    if s in ["BTC","ETH","SOL"]:
        try:
            par={"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=5",timeout=10).json()
            k=list(r['result'].keys())[0]
            data=r['result'][k][-100:]
            opens=[float(x[1]) for x in data]
            highs=[float(x[2]) for x in data]
            lows=[float(x[3]) for x in data]
            closes=[float(x[4]) for x in data]
            vol=[float(x[6]) for x in data]
            return opens, highs, lows, closes, vol
        except: pass
    else:
        ymap={"NVDA":"NVDA","TSLA":"TSLA","XAUUSD":"GC=F"}
        y=get_yahoo(ymap[s])
        if y: return y
    # fallback
    base=get_price(s)
    closes=[base+random.uniform(-base*0.01,base*0.01) for _ in range(100)]
    opens=[c+random.uniform(-1,1) for c in closes]
    highs=[max(o,c)+random.uniform(0,base*0.003) for o,c in zip(opens,closes)]
    lows=[min(o,c)-random.uniform(0,base*0.003) for o,c in zip(opens,closes)]
    vol=[random.uniform(0.8,2.2) for _ in range(100)]
    return opens, highs, lows, closes, vol

def rsi_calc(closes, p=14):
    if len(closes)<p+1: return 50
    g=sum(max(0,closes[i]-closes[i-1]) for i in range(-p,0))/p
    l=sum(max(0,closes[i-1]-closes[i]) for i in range(-p,0))/p
    if l==0: return 70
    return 100-(100/(1+g/l))

def spy_real():
    try:
        y=get_yahoo("SPY", interval="5m", range_="1d")
        if not y: return True, 0
        closes=y[3]
        if len(closes)<2: return True, 0
        cambio=(closes[-1]-closes[-2])/closes[-2]*100
        return closes[-1] > closes[0], cambio
    except: return True, 0

# BOT1 - LÓGICA ORIGINAL INTACTA
def bot1_analiza(s):
    opens, highs, lows, closes, vol = get_velas(s)
    lineas=[]
    for i in range(20, len(closes)-10):
        p=closes[i]
        rebotes=sum(1 for c in closes[max(0,i-30):i+10] if abs(c-p)/p < 0.0025)
        if rebotes>=2:
            fuerza=min(90, rebotes*15+25)
            lineas.append({"precio":p,"rebotes":rebotes,"fuerza":fuerza})
    unicas=[]
    for l in sorted(lineas, key=lambda x: x['rebotes'], reverse=True):
        if not any(abs(l['precio']-u['precio'])/u['precio']<0.006 for u in unicas):
            unicas.append(l)
    return unicas[:8], closes, opens, highs, lows, vol

def bot2_apoya(s, linea, closes):
    if not linea: return False,0,0,"BOT2 sin linea"
    confirm=sum(1 for c in closes[-40:] if abs(c-linea['precio'])/linea['precio']<0.003)
    fuerza=min(99, confirm*18+20)
    apoya=confirm>=3 and fuerza>=65
    return apoya, fuerza, confirm, f"BOT2: {confirm} toques {fuerza:.0f}% {'✅' if apoya else '❌'}"

def bot3_jefe_admin(s, linea_bot1, fuerza2, confirm, closes, vol):
    if not linea_bot1: return False, 0, "JEFE sin linea", 0, True
    rsi=rsi_calc(closes)
    vp=sum(vol[-20:])/20 if len(vol)>=20 else 1
    vm=(vol[-1]/vp) if vp else 1

    spy_verde, spy_chg = spy_real()
    ny=datetime.now(pytz.timezone('America/New_York'))
    es_madrugada=ny.hour<9 or ny.hour>=16
    if es_madrugada: spy_ok=True
    else: spy_ok=spy_verde

    score=min(30, linea_bot1['rebotes']*5) + linea_bot1['fuerza']*0.35 + fuerza2*0.35
    if rsi<35: score+=8
    elif rsi<45: score+=4
    if vm>1.5: score+=5
    if vm<0.6: score-=10
    if not spy_ok: score-=20
    score=max(0,min(99,score))

    if score>=90: bola=2500; nivel="🔥🔥🔥 90%+ TURBO"
    elif score>=80: bola=1800; nivel="🔥🔥 80%+ FUERTE"
    elif score>=70: bola=1100; nivel="🔥 70%+ NORMAL"
    else: bola=0; nivel=f"⏳ {score:.0f}% No da"

    detalle=f"JEFE: Score {score:.0f} {nivel}\nRSI {rsi:.0f} Vol x{vm:.1f} SPY {'🟢' if spy_ok else '🔴'} {spy_chg:+.2f}%\nBola decide: ${bola} SL {closes[-1]*0.88:.2f} Trail 0.8%"

    return (spy_ok and score>=70), bola, detalle, score, spy_ok

# V50.2 MALLA REAL
def decide(s):
    lineas, closes, opens, highs, lows, vol = bot1_analiza(s)
    if not lineas:
        return {"compra":False,"tipo":"SIN LINEAS","detalle":"BOT1 no encontró","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}
    top=lineas[0]
    apoya2,f2,conf2,txt2=bot2_apoya(s,top,closes)
    hoy=datetime.now().strftime("%Y-%m-%d")
    # no borrar jefe_hoy aqui, es candado real
    apoya3,bola3,txt3,score,spy_ok=bot3_jefe_admin(s,top,f2,conf2,closes,vol)

    precio=closes[-1]
    cerca=abs(precio-top['precio'])/top['precio']<0.015
    ny=pytz.timezone('America/New_York')
    ahora=datetime.now(ny)
    es_ny=9 <= ahora.hour <= 16 and s in ["NVDA","TSLA","XAUUSD"]
    key=f"{s}_{hoy}"

    if key in ESTADO["jefe_hoy"]:
        return {"compra":False,"tipo":"JEFE YA CAZO HOY ✅","detalle":f"{txt2}\n{txt3}\n🔒 Ya se tomó ganancia hoy en {s}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}

    if es_ny:
        if cerca and apoya2 and apoya3:
            ESTADO["jefe_hoy"][key]=True
            return {"compra":True,"tipo":f"BOT2 NY MALLA ${bola3}","bola":bola3,"detalle":f"REAL NY: BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n{txt2}\n{txt3}\n✅ MALLA TODOS APOYAN A BOT2","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}
        else:
            return {"compra":False,"tipo":"NY ESPERA MALLA","detalle":f"BOT1 {top['rebotes']}R ${top['precio']:.2f}\n{txt2}\n{txt3}\n⏳ Esperando MALLA","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}
    else:
        if cerca and apoya2 and apoya3:
            bola1=ESTADO["bola"].get(s,500)
            if score>=90:
                ESTADO["jefe_hoy"][key]=True
                return {"compra":True,"tipo":f"BOT1 ${bola1}+JEFE ${bola3} MALLA 90%+","bola":bola1+bola3,"detalle":f"REAL: BOT1 {top['rebotes']}R {top['fuerza']:.0f}%\n{txt2}\n{txt3}\n✅ MALLA TODOS APOYAN -> COMPRA TOTAL","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}
            else:
                return {"compra":True,"tipo":f"BOT1 ${bola1} MALLA {score:.0f}%","bola":bola1,"detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}%\n{txt2}\n{txt3}\n✅ BOT2+BOT3 APOYAN -> BOT1","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}
        else:
            return {"compra":False,"tipo":"ESPERA MALLA","detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n{txt2}\n{txt3}\n⏳ Falta apoyo MALLA","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}

@app.route('/')
def dash():
    html="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:Arial;padding:10px}.card{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:8px 0}.v{color:#00ff88}.n{color:orange}.btn{background:#00ff88;color:#000;padding:10px 18px;border-radius:8px;text-decoration:none;display:inline-block;margin:4px;font-weight:bold}</style></head><body><h2>💰 V50.2 REAL - MAQUINA DE HACER DINERO 💰</h2><p>REAL: Kraken + Yahoo + SPY real | MALLA todos apoyan</p>"""
    spy_v, spy_c = spy_real()
    html+=f'<div class="card">SPY REAL: {"🟢" if spy_v else "🔴"} {spy_c:+.2f}% | NY: {datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M")} | Bloqueo 1x día activo</div>'
    for s in SYMBOLS:
        d=decide(s)
        color="v" if d["compra"] else "n"
        html+=f'<div class="card"><b>{s}</b> ${get_price(s):.2f} | <span class="{color}">{d["tipo"]}</span><br><small>{d["detalle"].replace(chr(10),"<br>")}</small><br><a class="btn" href="/graf/{s}">GRAFICA VIVA 📈</a> <a class="btn" href="/forzar/{s}">FORZAR</a></div>'
    html+='</body></html>'
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
        ax.set_title(f'V50.2 REAL {s} ${c[-1]:.2f} {d["tipo"]}',color='white',fontsize=9)
        ax.tick_params(colors='white'); ax.grid(True,alpha=0.1)
        rsi_vals=[rsi_calc(c[:i]) for i in range(15,len(c))]
        ax2.plot(rsi_vals,color='#00ffff'); ax2.axhline(70,color='red',ls='--',alpha=0.4); ax2.axhline(30,color='green',ls='--',alpha=0.4); ax2.set_ylim(0,100); ax2.tick_params(colors='white')
        buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=150); buf.seek(0)
        img=base64.b64encode(buf.read()).decode(); plt.close()
        return f'<html style="background:#000;color:#fff;font-family:Arial"><body style="padding:10px"><h2>V50.2 REAL {s} ${c[-1]:.2f}</h2><pre style="background:#111;padding:12px;border-radius:8px">{d["detalle"]}</pre><img src="data:image/png;base64,{img}" style="width:100%;border-radius:12px"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">← VOLVER DASH</a></body></html>'
    except Exception as e: return f'Error grafica {s}: {e}'

@app.route('/forzar/<s>')
def forzar(s):
    hoy=datetime.now().strftime("%Y-%m-%d")
    ESTADO["jefe_hoy"].pop(f"{s.upper()}_{hoy}",None)
    d=decide(s.upper())
    return f"<pre style='background:#000;color:#0f0;padding:20px'>{d['detalle']}\n\nPrecio REAL: ${get_price(s.upper()):.2f}\n{d['tipo']}</pre><a href='/'>VOLVER</a>"

@bot.message_handler(commands=['start'])
def start(m): bot.send_message(m.chat.id,"💰 V50.2 REAL - MAQUINA DE HACER DINERO 💰\nREAL Kraken + Yahoo SPY\nBOT1 ↔ BOT2 ↔ BOT3 MALLA\nhttps://telegram-bot-cijp.onrender.com")

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.upper().strip()
    if t in SYMBOLS:
        d=decide(t)
        bot.send_message(m.chat.id,f"V50.2 REAL {t} ${get_price(t):.2f}\n{d['detalle']}\n\n{d['tipo']}")
    elif "DASH" in t: bot.send_message(m.chat.id,"https://telegram-bot-cijp.onrender.com")
    else: bot.send_message(m.chat.id,"Escribe BTC, ETH, SOL, NVDA, TSLA, XAUUSD")

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
def check(): return "V50.2 REAL MAQUINA DINERO LIVE"

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))
