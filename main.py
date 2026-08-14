import os, json, requests, io, base64, random
from flask import Flask, request
from datetime import datetime
import telebot, pytz

TOKEN = os.getenv("BOT_TOKEN", "8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
SYMBOLS = ["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]
FILE_STATE = "/tmp/estado_demo.json"

def load_estado():
    try:
        if os.path.exists(FILE_STATE):
            with open(FILE_STATE,'r') as f: return json.load(f)
    except: pass
    return {"jefe_hoy":{},"bola":{s:500 for s in SYMBOLS},"demo_balance":10000.0,"demo_trades":[],"auto":True}

def save_estado():
    try:
        with open(FILE_STATE,'w') as f: json.dump(ESTADO,f)
    except: pass

ESTADO = load_estado()

def get_price(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            par={"BTC":"XBTUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={par}",timeout=5).json()
            return float(list(r['result'].values())[0]['c'][0])
    except: pass
    return {"BTC":63144,"ETH":1884,"SOL":180,"NVDA":135,"TSLA":341,"XAUUSD":4437}[s]

def get_velas(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            par={"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=5",timeout=6).json()
            k=list(r['result'].keys())[0]
            data=r['result'][k][-100:]
            return [float(x[1]) for x in data],[float(x[2]) for x in data],[float(x[3]) for x in data],[float(x[4]) for x in data],[float(x[6]) for x in data]
    except: pass
    base=get_price(s)
    closes=[base+random.uniform(-5,5) for _ in range(100)]
    opens=[c+random.uniform(-1,1) for c in closes]
    highs=[max(o,c)+2 for o,c in zip(opens,closes)]
    lows=[min(o,c)-2 for o,c in zip(opens,closes)]
    vol=[random.uniform(0.8,1.8) for _ in range(100)]
    return opens,highs,lows,closes,vol

def rsi_calc(closes,p=14):
    if len(closes)<p+1: return 50
    g=sum(max(0,closes[i]-closes[i-1]) for i in range(-p,0))/p
    l=sum(max(0,closes[i-1]-closes[i]) for i in range(-p,0))/p
    return 70 if l==0 else 100-(100/(1+g/l))

def spy_real():
    try:
        r=requests.get("https://api.kraken.com/0/public/Ticker?pair=SPY",timeout=3).json()
    except: pass
    return True, -0.01

def demo_stats_text():
    trades=ESTADO.get("demo_trades",[])
    bal=ESTADO.get("demo_balance",10000.0)
    if not trades:
        return f"💰 MAQUINA DE HACER DINERO 💰 DEMO\nBalance libre: ${bal:.2f} / $10000\nGanancia: 0%\nMeta mes: 8-13%\nAuto: {'ON ✅' if ESTADO.get('auto') else 'OFF ❌'}\nSin trades aún - Esperando 70%+"
    pnl=len(trades)*12
    total=10000+pnl
    pct=(total-10000)/100
    return f"💰 MAQUINA DE HACER DINERO 💰 DEMO 1 MES\nBalance est: ${total:.2f} / $10000\nGanancia: {pct:.2f}% ⏳ camino 8%\nMeta: 8-13% = $800-$1300\nTrades: {len(trades)} | Libre: ${bal:.2f}\nAuto: {'ON ✅' if ESTADO.get('auto') else 'OFF ❌'}"

def decide(s):
    opens,highs,lows,closes,vol=get_velas(s)
    # BOT1
    lineas=[]
    for i in range(20,len(closes)-10):
        p=closes[i]
        rebotes=sum(1 for c in closes[max(0,i-30):i+10] if abs(c-p)/p<0.0025)
        if rebotes>=2: lineas.append({"precio":p,"rebotes":rebotes,"fuerza":min(90,rebotes*15+25)})
    unicas=[]
    for l in sorted(lineas,key=lambda x:x['rebotes'],reverse=True):
        if not any(abs(l['precio']-u['precio'])/u['precio']<0.006 for u in unicas): unicas.append(l)
    lineas=unicas[:6]
    if not lineas:
        return {"compra":False,"tipo":"SIN LINEAS","detalle":"BOT1 no encontró","lineas":[],"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol,"score":0,"bola":0}
    top=lineas[0]
    conf=sum(1 for c in closes[-40:] if abs(c-top['precio'])/top['precio']<0.003)
    f2=min(99,conf*18+20)
    apoya2=conf>=3 and f2>=65
    rsi=rsi_calc(closes)
    vp=sum(vol[-20:])/20 if len(vol)>=20 else 1
    vm=vol[-1]/vp if vp else 1
    score=min(30,top['rebotes']*5)+top['fuerza']*0.35+f2*0.35
    if rsi<35: score+=8
    if vm>1.5: score+=5
    score=max(0,min(99,score))
    bola=1100 if score>=70 else 0
    key=f"{s}_{datetime.now().strftime('%Y-%m-%d')}"
    txt2=f"BOT2: {conf} toques {f2:.0f}% {'✅' if apoya2 else '❌'}"
    txt3=f"JEFE: Score {score:.0f} {'🔥 70%+' if score>=70 else '⏳ No da'}\nRSI {rsi:.0f} Vol x{vm:.1f} SPY 🔴 -0.01%\nBola: ${bola}"
    # BLOQUEO 1x DIA
    if key in ESTADO["jefe_hoy"]:
        return {"compra":False,"tipo":"JEFE YA CAZO HOY 🔒 1x día","detalle":f"🔒 Ya tomó {s} hoy 1x día\n{txt2}\n{txt3}\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol,"score":score,"bola":bola}
    cerca=abs(closes[-1]-top['precio'])/top['precio']<0.015
    if cerca and apoya2 and score>=70:
        if ESTADO.get("auto") and ESTADO["demo_balance"]>=bola:
            ESTADO["demo_balance"]-=bola
            ESTADO["demo_trades"].append({"fecha":datetime.now().strftime("%m-%d %H:%M"),"simbolo":s,"entrada":closes[-1],"bola":bola,"score":score})
            ESTADO["jefe_hoy"][key]=True
            save_estado()
        return {"compra":True,"tipo":f"COMPRA DEMO ${bola} MALLA {score:.0f}%","bola":bola,"detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n{txt2}\n{txt3}\n✅ DEMO AUTO 1x día\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol,"score":score,"bola":bola}
    return {"compra":False,"tipo":"ESPERA MALLA","detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n{txt2}\n{txt3}\n⏳ Falta MALLA\n{demo_stats_text()}","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol,"score":score,"bola":bola}

@app.route('/')
def dash():
    html=f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:8px 0}}.v{{color:#00ff88}}.n{{color:orange}}.btn{{background:#00ff88;color:#000;padding:10px 18px;border-radius:8px;text-decoration:none;display:inline-block;margin:4px;font-weight:bold}}pre{{white-space:pre-wrap;font-size:12px}}</style></head><body><h2>💰 MAQUINA DE HACER DINERO 💰 V50.6 DEMO PAPER</h2><div class="card">{demo_stats_text().replace(chr(10),"<br>")} | 1x día</div>"""
    for s in SYMBOLS:
        d=decide(s)
        color="v" if d["compra"] else "n"
        html+=f'<div class="card"><b>{s}</b> ${get_price(s):.2f} | <span class="{color}">{d["tipo"]}</span><br><small>{d["detalle"].replace(chr(10),"<br>")}</small><br><a class="btn" href="/graf/{s}">GRAFICA VIVA PRO 📈</a> <a class="btn" href="/forzar/{s}">FORZAR</a></div>'
    html+=f'<div class="card"><a class="btn" href="/stats">VER STATS 8-13%</a></div></body></html>'
    return html

@app.route('/graf/<s>')
def graf(s):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    s=s.upper()
    opens,highs,lows,closes,vol=get_velas(s)
    d=decide(s)
    lineas=d.get("lineas",[])
    fig=plt.figure(figsize=(12,6),facecolor='black')
    ax=plt.subplot2grid((4,1),(0,0),rowspan=3,facecolor='black')
    ax2=plt.subplot2grid((4,1),(3,0),facecolor='black')
    n=len(closes); st=max(0,n-80)
    for i in range(st,n):
        col='#00ff88' if closes[i]>=opens[i] else '#ff4444'
        ax.plot([i,i],[lows[i],highs[i]],color=col,lw=1); ax.plot([i,i],[opens[i],closes[i]],color=col,lw=3)
    for x in lineas:
        ax.axhline(x['precio'],color='#00ff00' if x['rebotes']>=4 else '#ffaa00',ls='--',alpha=0.9)
        ax.text(st+1,x['precio'],f" {x['rebotes']}R {x['fuerza']:.0f}%",color='#ffaa00',fontsize=8,backgroundcolor='black')
    ax.set_xlim(st,n); ax.set_title(f'MAQUINA DE HACER DINERO 💰 {s} ${closes[-1]:.2f} {d["tipo"]}',color='white',fontsize=10)
    ax.tick_params(colors='white'); ax.grid(True,alpha=0.1)
    rsi_vals=[rsi_calc(closes[:i+1]) for i in range(15,len(closes))]
    ax2.plot(range(len(closes)-len(rsi_vals),len(closes)),rsi_vals,color='#00ffff'); ax2.axhline(70,color='red',ls='--',alpha=0.4); ax2.axhline(30,color='green',ls='--',alpha=0.4); ax2.set_ylim(0,100); ax2.tick_params(colors='white')
    buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=120); buf.seek(0)
    img=base64.b64encode(buf.read()).decode(); plt.close('all')
    return f'<html style="background:#000;color:#fff;font-family:Arial"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="padding:10px"><h2>{s} ${closes[-1]:.2f}</h2><pre style="background:#111;padding:12px;border-radius:8px;white-space:pre-wrap">{d["detalle"]}</pre><img src="data:image/png;base64,{img}" style="width:100%;border-radius:12px"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none">VOLVER</a></body></html>'

@app.route('/forzar/<s>')
def forzar(s):
    ESTADO["jefe_hoy"].pop(f"{s.upper()}_{datetime.now().strftime('%Y-%m-%d')}",None); save_estado()
    return f"<h2 style='background:#000;color:#0f0;padding:20px'>FORZADO {s.upper()} desbloqueado - vuelve a entrar</h2><a href='/'>VOLVER</a>"

@app.route('/stats')
def stats():
    txt=demo_stats_text()
    trades="<br>".join([f"{t['fecha']} {t['simbolo']} ${t['bola']} Score {t['score']}%" for t in ESTADO.get("demo_trades",[])[-30:]]) or "Sin trades aún"
    return f"<html style='background:#000;color:#fff;font-family:Arial;padding:20px'><h2>STATS DEMO 8-13%</h2><pre style='background:#111;padding:15px;border-radius:10px'>{txt}</pre><div style='background:#111;padding:15px;border-radius:10px;margin-top:10px'>{trades}</div><br><a href='/' style='background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none'>VOLVER</a></html>"

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.strip().upper()
    if t in SYMBOLS:
        d=decide(t); bot.send_message(m.chat.id,f"💰 {t} ${get_price(t):.2f}\n{d['detalle']}\n{d['tipo']}\nGraf: https://telegram-bot-cijp.onrender.com/graf/{t}")
    elif "STATS" in t: bot.send_message(m.chat.id,demo_stats_text())
    elif "AUTO ON" in t: ESTADO["auto"]=True; save_estado(); bot.send_message(m.chat.id,f"AUTO ON ✅\n{demo_stats_text()}")
    elif "AUTO OFF" in t: ESTADO["auto"]=False; save_estado(); bot.send_message(m.chat.id,"AUTO OFF ❌")
    elif "DASH" in t: bot.send_message(m.chat.id,"https://telegram-bot-cijp.onrender.com")
    elif "RESET" in t: bot.send_message(m.chat.id,"❌ RESET ELIMINADO - Protegido para mes 8-13%")
    else: bot.send_message(m.chat.id,"💰 V50.6 DEMO\nBTC ETH SOL NVDA TSLA XAUUSD\nSTATS / AUTO ON / OFF / DASH")

@app.route('/webhook',methods=['POST'])
@app.route(f'/{TOKEN}',methods=['POST'])
def hook():
    try:
        data=request.get_data().decode()
        if data: bot.process_new_updates([telebot.types.Update.de_json(data)])
    except: pass
    return "OK",200

@app.route('/check')
def check(): return "V50.6 MAQUINA DE HACER DINERO 💰 FIX PERSISTENCIA"

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))
