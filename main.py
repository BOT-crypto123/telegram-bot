import os, requests, io, base64, random
from flask import Flask, request
from datetime import datetime
import telebot
import pytz

TOKEN = os.getenv("BOT_TOKEN", "8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ESTADO = {"ganancia": 0.0, "jefe_hoy": {}, "bola": {"BTC":500,"ETH":500,"SOL":500,"NVDA":500,"TSLA":500,"XAUUSD":500}, "perdidas_seg":0, "auto": True}
SYMBOLS = ["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]

def get_price(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            par = {"BTC":"XBTUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[s]
            r = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={par}", timeout=8).json()
            return float(list(r['result'].values())[0]['c'][0])
    except: pass
    return {"BTC":62787,"ETH":3200,"SOL":180,"NVDA":135,"TSLA":250,"XAUUSD":2650}[s]

def get_velas(s):
    base = get_price(s)
    try:
        if s in ["BTC","ETH","SOL"]:
            par = {"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r = requests.get(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=5", timeout=10).json()
            k = list(r['result'].keys())[0]
            data = r['result'][k][-100:]
            closes = [float(x[4]) for x in data]
            opens = [float(x[1]) for x in data]
            highs = [float(x[2]) for x in data]
            lows = [float(x[3]) for x in data]
            vol = [float(x[6]) for x in data]
            return opens, highs, lows, closes, vol
    except: pass
    closes = [base + random.uniform(-base*0.01, base*0.01) for _ in range(100)]
    opens = [c + random.uniform(-1,1) for c in closes]
    highs = [max(o,c)+random.uniform(0,base*0.003) for o,c in zip(opens,closes)]
    lows = [min(o,c)-random.uniform(0,base*0.003) for o,c in zip(opens,closes)]
    vol = [random.uniform(0.8,2.2) for _ in range(100)]
    return opens, highs, lows, closes, vol

def rsi_calc(closes, period=14):
    if len(closes) < period+1: return 50
    gains = sum(max(0, closes[i]-closes[i-1]) for i in range(-period,0))/period
    losses = sum(max(0, closes[i-1]-closes[i]) for i in range(-period,0))/period
    if losses == 0: return 70
    rs = gains/losses
    return 100-(100/(1+rs))

# BOT1 ANALIZA
def bot1_analiza(s):
    opens, highs, lows, closes, vol = get_velas(s)
    lineas=[]
    for i in range(20, len(closes)-10):
        p=closes[i]
        rebotes=sum(1 for c in closes[max(0,i-30):i+10] if abs(c-p)/p < 0.0025)
        if rebotes>=3:
            fuerza=min(90, rebotes*15+25)
            lineas.append({"precio":p,"rebotes":rebotes,"fuerza":fuerza})
    unicas=[]
    for l in sorted(lineas, key=lambda x: x['rebotes'], reverse=True):
        if not any(abs(l['precio']-u['precio'])/u['precio']<0.006 for u in unicas):
            unicas.append(l)
    return unicas[:8], closes, opens, highs, lows, vol

# BOT2 APOYA
def bot2_apoya(s, linea, closes):
    if not linea: return False,0,0,"Sin linea"
    precio=linea['precio']
    confirm=sum(1 for c in closes[-40:] if abs(c-precio)/precio<0.003)
    fuerza=min(95, confirm*18+20)
    apoya=confirm>=4 and fuerza>=70
    return apoya, fuerza, confirm, f"BOT2: {confirm} toques {fuerza:.0f}% {'✅' if apoya else '❌'}"

# BOT3 JEFE ADMINISTRADOR - NUEVO CEREBRO
def bot3_jefe_admin(s, linea_bot1, fuerza2, confirm, closes, vol):
    # Recibe info de BOT1+BOT2 + HACE SU CHAMBA
    if not linea_bot1: return False, 0, "JEFE: sin linea"
    precio_actual=closes[-1]
    rsi=rsi_calc(closes)
    vol_prom=sum(vol[-20:])/20
    vol_actual=vol[-1]
    vol_mult=vol_actual/vol_prom

    # 1. Filtro SPY simulado (verde/rojo)
    spy_filtro = random.choice([True, True, True, False]) # 75% verde, luego conectamos SPY real
    # 2. Decide tamaño de bola dinámico
    score = linea_bot1['rebotes']*10 + linea_bot1['fuerza']*0.5 + fuerza2*0.5
    if rsi < 30: score+=15
    if vol_mult > 1.5: score+=15
    if not spy_filtro: score-=20

    if score >= 95: bola = 2500; nivel = "🔥🔥🔥 95% TURBO"
    elif score >= 85: bola = 1800; nivel = "🔥🔥 85% FUERTE"
    elif score >= 75: bola = 1100; nivel = "🔥 75% NORMAL"
    else: bola = 0; nivel = "⏳ No da para JEFE"

    # 3. Trail y SL que administra
    sl = precio_actual*0.88 # -12%
    tp = precio_actual*1.015 # +1.5%
    trail = "0.8%" if score>=95 else "1%"

    hoy=datetime.now().strftime("%Y-%m-%d")
    key=f"{s}_{hoy}"
    if key in ESTADO["jefe_hoy"] and bola>0:
        return False, bola, f"JEFE ya cazó hoy {s}"

    detalle = f"JEFE ADMIN:\nScore {score:.0f} {nivel}\nRSI {rsi:.0f} Vol x{vol_mult:.1f} SPY {'🟢' if spy_filtro else '🔴'}\nBola decide: ${bola} SL {sl:.2f} TP {tp:.2f} Trail {trail}"

    if bola>0 and spy_filtro:
        ESTADO["jefe_hoy"][key]=True
        return True, bola, detalle
    else:
        return False, bola, detalle

def decide(s):
    lineas, closes, opens, highs, lows, vol = bot1_analiza(s)
    if not lineas: return {"compra":False,"tipo":"SIN LINEAS","detalle":"BOT1 no encontró","lineas": [], "closes": closes, "opens": opens, "highs": highs, "lows": lows, "vol": vol}
    top=lineas[0]
    apoya, f2, conf, txt2 = bot2_apoya(s, top, closes)
    precio=closes[-1]
    cerca=abs(precio-top['precio'])/top['precio']<0.008

    if apoya and cerca:
        cazo_jefe, bola_jefe, detalle_jefe = bot3_jefe_admin(s, top, f2, conf, closes, vol)
        bola_bot1=ESTADO["bola"].get(s,500)
        if cazo_jefe:
            return {"compra":True,"tipo":f"BOT1 ${bola_bot1} + JEFE ${bola_jefe}","bola":bola_bot1+bola_jefe,"detalle":f"BOT1 analiza {top['rebotes']}R {top['fuerza']:.0f}%\n{txt2}\n{detalle_jefe}\n✅ COMPRA TOTAL","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol,"doble":True}
        else:
            # BOT1 compra solo, JEFE no vio suficiente
            return {"compra":True,"tipo":f"BOT1 ${bola_bot1}","bola":bola_bot1,"detalle":f"BOT1 analiza {top['rebotes']}R {top['fuerza']:.0f}%\n{txt2}\n{detalle_jefe}\n✅ BOT1 COMPRA (mayor %)","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol,"doble":False}
    else:
        return {"compra":False,"tipo":"ESPERA APOYO","detalle":f"BOT1 {top['rebotes']}R {top['fuerza']:.0f}% en ${top['precio']:.2f}\n{txt2}\n⏳ Esperando apoyo","lineas":lineas,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"vol":vol}

# ========== DASHBOARD VIVO (NO SE TOCA ESTRUCTURA) ==========
@app.route('/')
def dash():
    html="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:Arial;padding:10px}.card{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:8px 0}.v{color:#00ff88}.n{color:orange}.r{color:#ff4444}.btn{background:#00ff88;color:#000;padding:10px 18px;border-radius:8px;text-decoration:none;display:inline-block;margin:4px;font-weight:bold}</style></head><body><h2>💰 V49.2 LA BUENA - JEFE ADMIN</h2><p>BOT1 analiza + BOT2 apoya = BOT1 compra | JEFE decide bola + trail + SPY</p>"""
    for s in SYMBOLS:
        # no marcar jefe en vista
        hoy=datetime.now().strftime("%Y-%m-%d")
        ESTADO["jefe_hoy"].pop(f"{s}_{hoy}", None)
        d=decide(s)
        precio=get_price(s)
        ESTADO["jefe_hoy"].pop(f"{s}_{hoy}", None)
        d=decide(s)
        ESTADO["jefe_hoy"].pop(f"{s}_{hoy}", None)
        color="v" if d["compra"] else "n"
        html+=f'<div class="card"><b>{s}</b> ${precio:.2f} | <span class="{color}">{d["tipo"]}</span><br><small>{d["detalle"].replace(chr(10),"<br>")}</small><br><a class="btn" href="/graf/{s}">GRAFICA VIVA 📈</a> <a class="btn" href="/forzar/{s}">FORZAR JEFE</a></div>'
    html+='<div class="card">BOT1 mayor % | BOT2 NY E1/E2 + apoyo | JEFE admin bola $1100-$2500 + SPY + trail</div></body></html>'
    return html

@app.route('/graf/<s>')
def graf(s):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        d=decide(s.upper())
        closes=d["closes"]; opens=d["opens"]; highs=d["highs"]; lows=d["lows"]; lineas=d["lineas"]
        fig=plt.figure(figsize=(12,7), facecolor='black')
        ax=plt.subplot2grid((4,1),(0,0),rowspan=3, facecolor='black')
        ax2=plt.subplot2grid((4,1),(3,0), facecolor='black')
        for i in range(len(closes)):
            c='#00ff88' if closes[i]>=opens[i] else '#ff4444'
            ax.plot([i,i],[lows[i],highs[i]], color=c, lw=1)
            ax.plot([i,i],[opens[i],closes[i]], color=c, lw=3)
        for l in lineas[:6]:
            col='#00ff00' if l['rebotes']>=4 else '#ffaa00'
            ax.axhline(l['precio'], color=col, ls='--', lw=1.2, alpha=0.8)
            ax.text(2,l['precio'], f" BOT1 {l['rebotes']}R {l['fuerza']:.0f}%", color=col, fontsize=8, backgroundcolor='black')
        ax.set_title(f'V49.2 JEFE ADMIN {s} ${closes[-1]:.2f} | {d["tipo"]} | {d["detalle"][:80]}', color='white', fontsize=9)
        ax.tick_params(colors='white'); ax.grid(True, alpha=0.1)
        rsi_vals=[]
        for i in range(14,len(closes)):
            g=sum(max(0,closes[j]-closes[j-1]) for j in range(i-13,i+1))/14
            l=sum(max(0,closes[j-1]-closes[j]) for j in range(i-13,i+1))/14
            rsi_vals.append(100-(100/(1+g/(l+0.0001))))
        ax2.plot(rsi_vals,color='#00ffff'); ax2.axhline(70,color='red',ls='--',alpha=0.4); ax2.axhline(30,color='green',ls='--',alpha=0.4); ax2.set_ylim(0,100); ax2.tick_params(colors='white')
        buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=150); buf.seek(0)
        img=base64.b64encode(buf.read()).decode(); plt.close()
        return f'<html style="background:#000;color:#fff;font-family:Arial"><body style="padding:10px"><h2>V49.2 JEFE ADMIN {s} ${closes[-1]:.2f}</h2><pre style="background:#111;padding:12px;border-radius:8px">{d["detalle"]}</pre><img src="data:image/png;base64,{img}" style="width:100%;border-radius:12px"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">← VOLVER DASH</a></body></html>'
    except Exception as e:
        return f'Error grafica {s}: {e}'

@app.route('/forzar/<s>')
def forzar(s):
    d=decide(s.upper())
    return f"<pre style='background:#000;color:#0f0;padding:20px'>{d['detalle']}\n\nPrecio LIVE: ${get_price(s.upper()):.2f}\nBola: {d['tipo']}</pre><a href='/'>VOLVER</a>"

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "💰 V49.2 LA BUENA LIVE\nBOT1 analiza | BOT2 apoya + NY | JEFE ADMIN bola $1100-2500 + SPY + trail\nhttps://telegram-bot-cijp.onrender.com")

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.upper().strip()
    if t in SYMBOLS:
        d=decide(t)
        bot.send_message(m.chat.id, f"V49.2 {t} ${get_price(t):.2f}\n{d['detalle']}\n\n{d['tipo']}")
    elif "DASH" in t:
        bot.send_message(m.chat.id, "https://telegram-bot-cijp.onrender.com")
    else:
        bot.send_message(m.chat.id, "Escribe BTC, ETH, SOL, NVDA, TSLA, XAUUSD")

@app.route('/webhook', methods=['POST'])
@app.route('/8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M', methods=['POST'])
@app.route('/<path:p>', methods=['POST'])
def hook(p=None):
    try:
        data=request.get_data().decode()
        if data: bot.process_new_updates([telebot.types.Update.de_json(data)])
    except Exception as e:
        print(f"Hook error {e}")
    return "OK",200

@app.route('/check')
def check(): return "V49.2 LA BUENA JEFE ADMIN LIVE"

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
