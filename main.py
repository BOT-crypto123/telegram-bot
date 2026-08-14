# MAQUINA DE HACER DINERO V50.9.1 FINAL DETALLADA - 3 BOTS COLAB + FEES 0.82% + DETALLE NETO
import os, json, requests, random
from flask import Flask, request
from datetime import datetime
import telebot, pytz

TOKEN = os.getenv("BOT_TOKEN", "8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
SYMBOLS = ["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]
FILE_STATE = "/tmp/estado_demo.json"
FEE_LADO = 0.0041
FEE_RT = 0.0082

def load_estado():
    try:
        if os.path.exists(FILE_STATE):
            with open(FILE_STATE,'r') as f: return json.load(f)
    except: pass
    return {"jefe_hoy":{},"demo_balance":10000.0,"demo_trades":[],"open_trades":[],"auto":True,"fees":0.0}
def save_estado():
    try:
        with open(FILE_STATE,'w') as f: json.dump(ESTADO,f)
    except: pass
ESTADO=load_estado()

def get_price(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            m={"BTC":"XBTUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={m}",timeout=5).json()
            return float(list(r['result'].values())[0]['c'][0])
    except: pass
    return {"BTC":63144,"ETH":1884,"SOL":180,"NVDA":135,"TSLA":341,"XAUUSD":4437}[s]

def get_velas(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            m={"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/OHLC?pair={m}&interval=5",timeout=6).json()
            k=list(r['result'].keys())[0]
            d=r['result'][k][-120:]
            return [float(x[1]) for x in d],[float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d]
    except: pass
    base=get_price(s)
    c=[base+random.uniform(-3,3) for _ in range(120)]
    o=[x+random.uniform(-1,1) for x in c]
    h=[max(a,b)+2 for a,b in zip(o,c)]
    l=[min(a,b)-2 for a,b in zip(o,c)]
    return o,h,l,c

def rsi_calc(closes,p=14):
    if len(closes)<p+1: return 50
    g=sum(max(0,closes[i]-closes[i-1]) for i in range(-p,0))/p
    l=sum(max(0,closes[i-1]-closes[i]) for i in range(-p,0))/p
    return 70 if l==0 else 100-(100/(1+g/l))

def is_ny():
    tz=pytz.timezone("America/Mexico_City")
    n=datetime.now(tz)
    return 8 <= n.hour < 12

def BOT1_lineas(closes):
    lineas=[]
    for i in range(25,len(closes)-10):
        p=closes[i]
        rebotes=sum(1 for c in closes[max(0,i-35):i+10] if abs(c-p)/p<0.0025)
        if rebotes>=2: lineas.append({"precio":p,"rebotes":rebotes,"fuerza":min(90,rebotes*15+25)})
    unicas=[]
    for lin in sorted(lineas,key=lambda x:x['rebotes'],reverse=True):
        if not any(abs(lin['precio']-u['precio'])/u['precio']<0.006 for u in unicas): unicas.append(lin)
    return unicas[:6]

def decidir(s):
    opens,highs,lows,closes=get_velas(s)
    precio=closes[-1]
    ny=is_ny()
    lineas=BOT1_lineas(closes)
    ventas=[]
    for tr in ESTADO["open_trades"][:]:
        if tr["simbolo"]!=s: continue
        bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100
        neto=bruto-FEE_RT*100
        max_neto=tr.get("max_neto",neto)
        if neto>max_neto: max_neto=neto
        tr["max_neto"]=max_neto
        BOT1_VENDE = neto>=0.68 or neto<=-4.32 or (max_neto>=0.30 and neto<=max_neto-0.70)
        BOT2_APOYA_VENTA = neto>=0.68 or neto<=-4.32 or (max_neto>=0.30 and rsi_calc(closes)<60)
        if BOT1_VENDE and BOT2_APOYA_VENTA:
            gan_bruto=tr["bola"]*bruto/100
            fee=tr["bola"]*FEE_RT
            gan_neto=gan_bruto-fee
            ESTADO["demo_balance"]+=tr["bola"]+gan_neto
            ESTADO["fees"]+=fee
            motivo=f"{'TP' if neto>=0.68 else 'SL' if neto<=-4.32 else 'TRAIL'} {neto:.2f}% NETO"
            ESTADO["demo_trades"].append({"f":datetime.now().strftime("%m-%d %H:%M"),"s":s,"bola":tr["bola"],"bruto":bruto,"fee":fee,"gan_bruto":gan_bruto,"pct":neto,"pnl":gan_neto,"mot":motivo})
            ESTADO["open_trades"].remove(tr)
            save_estado()
            ventas.append(f"💰 VENTA 3 BOTS: {s} Bruto {bruto:+.2f}% ${gan_bruto:+.2f} - Fee ${fee:.2f} = NETO {neto:+.2f}% ${gan_neto:+.2f} {motivo}")
    if not lineas:
        return {"tipo":"SIN LINEAS BOT1","det":"BOT1 no ve líneas\n"+"\n".join(ventas),"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":[]}
    pulidas=[l for l in lineas if l['rebotes']>=2]
    if not pulidas:
        return {"tipo":"BOT2 PULIENDO 1R","det":f"BOT2 borró {len(lineas)} de 1R\n"+"\n".join(ventas),"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    top=pulidas[0]
    conf=sum(1 for c in closes[-50:] if abs(c-top['precio'])/top['precio']<0.003)
    f2=min(99,conf*18+20)
    BOT2_APOYA_COMPRA=conf>=3 and f2>=65
    score=min(30,top['rebotes']*5)+top['fuerza']*0.35+f2*0.35
    if s=="XAUUSD" and score<90: score*=0.7
    bola=2500 if score>=90 else 1100 if score>=70 else 0
    key=f"{s}_{datetime.now().strftime('%Y-%m-%d')}"
    det=f"📈 BOT1 {top['rebotes']}R {top['fuerza']:.0f}% ${top['precio']:.2f}\n📊 BOT2 {len(pulidas)} pulidas | {conf} toques {f2:.0f}% {'✅ APOYA' if BOT2_APOYA_COMPRA else '❌'}\n👑 JEFE Puntuación {score:.0f}% Bola ${bola} SL -4.32% TP +0.68% Tarifa NETO 0.82% NY {'🟢' if ny else '🔴'}"
    if ventas: det="\n".join(ventas)+"\n"+det
    if key in ESTADO["jefe_hoy"]:
        return {"tipo":"JEFE YA CAZO 1x DIA 🔒","det":det+"\n🔒 Apoya pero no compra","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if BOT2_APOYA_COMPRA and score>=70:
        fee_e=bola*FEE_LADO
        if ESTADO["auto"] and ESTADO["demo_balance"]>=bola+fee_e:
            ESTADO["demo_balance"]-=bola+fee_e
            ESTADO["fees"]+=fee_e
            ESTADO["open_trades"].append({"simbolo":s,"entrada_real":precio,"entrada":precio*(1+FEE_LADO),"bola":bola,"linea":top['precio'],"max_neto":-10})
            ESTADO["jefe_hoy"][key]=True
            save_estado()
        return {"tipo":f"{'BOT2 NY' if ny else 'BOT1'} COMPRA 3 BOTS ${bola}","det":det+f"\n✅ COMPRA 3 BOTS - fee entrada ${fee_e:.2f} | Total fee al vender ${bola*FEE_RT:.2f}","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    return {"tipo":"ESPERA APOYO 3 BOTS","det":det+"\n⏳ Falta apoyo","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}

@app.route('/')
def dash():
    ny=is_ny()
    h=f'<html><head><meta name="viewport" content="width=device-width"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border:1px solid #222;border-radius:14px;padding:14px;margin:10px 0}}.btn{{background:#00ff88;color:#000;padding:8px 14px;border-radius:8px;text-decoration:none;font-weight:bold}}</style></head><body><h2>💰 MAQUINA V50.9.1 FINAL DETALLADA 💸</h2>💵 SALDO NETO ${ESTADO["demo_balance"]:.2f} | COMISIONES ${ESTADO["fees"]:.2f} | ABIERTO {len(ESTADO["open_trades"])} | NY {"🟢" if ny else "🔴"}<br><small>TP 0.68% NETO SL -4.32% NETO COMISIÓN 0.82% - 3 BOTS COLAB<br>GANANCIA = BRUTO - COMISIÓN</small><br><br>'
    for s in SYMBOLS:
        d=decidir(s)
        h+=f'<div class="card"><b>{s}</b> ${get_price(s):.2f} - {d["tipo"]}<br><small>{d["det"].replace(chr(10),"<br>")}</small><br><br><a class="btn" href="/graf/{s}">GRAFICA VIVA 📈</a></div>'
    return h+"</body></html>"

@app.route('/graf/<s>')
def graf(s):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    s=s.upper(); opens,highs,lows,closes=get_velas(s); d=decidir(s)
    fig=plt.figure(figsize=(12,6),facecolor='black'); ax=plt.subplot2grid((4,1),(0,0),rowspan=3,facecolor='black'); ax2=plt.subplot2grid((4,1),(3,0),facecolor='black')
    n=len(closes); st=max(0,n-80)
    for i in range(st,n):
        col='#00ff88' if closes[i]>=opens[i] else '#ff4444'
        ax.plot([i,i],[lows[i],highs[i]],color=col,lw=1); ax.plot([i,i],[opens[i],closes[i]],color=col,lw=3)
    for x in d["lineas"]: ax.axhline(x['precio'],color='#00ff00',ls='--',alpha=0.8)
    for tr in ESTADO["open_trades"]:
        if tr["simbolo"]==s: ax.axhline(tr["entrada_real"],color='orange',ls='-',alpha=0.9)
    ax.set_xlim(st,n); ax.set_title(f'{s} {d["tipo"]} - BRUTO - FEE = NETO',color='white',fontsize=10); ax.tick_params(colors='white')
    rsi_vals=[rsi_calc(closes[:i+1]) for i in range(15,len(closes))]
    ax2.plot(range(len(closes)-len(rsi_vals),len(closes)),rsi_vals,color='#00ffff')
    import io,base64; buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=130); buf.seek(0); img=base64.b64encode(buf.read()).decode(); plt.close('all')
    return f'<html style="background:#000;color:#fff"><body><h2>{s} MAQUINA FINAL - DETALLE FEES</h2><pre>{d["det"]}</pre><img src="data:image/png;base64,{img}" style="width:100%"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:bold">VOLVER A MAQUINA 💰</a></body></html>'

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.strip().upper()
    if t=="DASHBOARD":
        bot.send_message(m.chat.id,f"💰 DASHBOARD MAQUINA V50.9.1\n💵 SALDO NETO ${ESTADO['demo_balance']:.2f} | COMISIONES ${ESTADO['fees']:.2f} | ABIERTO {len(ESTADO['open_trades'])}\n\nhttps://telegram-bot-cijp.onrender.com/\n\nPica para ver las 6 monedas + gráficas vivas 📈")
    elif "AUTO" in t:
        if "ON" in t: ESTADO["auto"]=True; save_estado(); bot.send_message(m.chat.id,"✅ AUTO ON - 3 BOTS colaborando COMPRAN Y VENDEN")
        else: ESTADO["auto"]=False; save_estado(); bot.send_message(m.chat.id,"⛔️ AUTO OFF - Solo observan, no compran ni venden")
    elif t in SYMBOLS:
        d=decidir(t); bot.send_message(m.chat.id,f"💰 {t} ${get_price(t):.2f} REAL FEES 0.82%\n{d['det']}\n{d['tipo']}\nhttps://telegram-bot-cijp.onrender.com/graf/{t}")
    elif "BALANCE" in t or "STATS" in t or "/BALANCE" in t or "/STATS" in t:
        trs=ESTADO["demo_trades"][-20:]
        lines=[]
        for x in trs:
            bruto=x.get('bruto',0); fee=x.get('fee',0); gan_b=x.get('gan_bruto',0)
            lines.append(f"{x['f']} {x['s']} Bola ${x['bola']}\n Bruto {bruto:+.2f}% ${gan_b:+.2f}\n - Fee ${fee:.2f}\n = NETO {x['pct']:+.2f}% ${x['pnl']:+.2f} {x['mot']}")
        txt="\n\n".join(lines) or "Sin ventas aún"
        prof=ESTADO["demo_balance"]-10000
        total_bruto=sum(x.get('gan_bruto',0) for x in ESTADO["demo_trades"])
        bot.send_message(m.chat.id,f"💰 MAQUINA V50.9.1 DETALLADA 💸\n\nBAL INICIAL: $10000.00\nGANANCIA BRUTA ACUM: ${total_bruto:+.2f}\n- COMISIONES TOTALES: ${ESTADO['fees']:.2f}\n= BAL NETO: ${ESTADO['demo_balance']:.2f} ({prof:+.2f})\nOPEN: {len(ESTADO['open_trades'])} | AUTO: {'ON ✅' if ESTADO['auto'] else 'OFF ⛔️'}\n\nDETALLE ULTIMAS VENTAS:\n{txt}\n\nhttps://telegram-bot-cijp.onrender.com/")
    else:
        bot.send_message(m.chat.id,"💰 MAQUINA V50.9.1 DETALLADA\nBOT1 lineas + BOT2 pule + BOT2 NY + JEFE bola\nLOS 3 COMPRAN Y LOS 3 VENDEN (BOT1 TAMBIEN VENDE)\nFEE 0.82% REAL INCLUIDO\n\nBTC ETH SOL NVDA TSLA XAUUSD\nEscribe STATS o DASHBOARD o /balance")

@app.route('/webhook',methods=['POST'])
@app.route(f'/{TOKEN}',methods=['POST'])
def hook():
    try:
        data=request.get_data().decode()
        if data: bot.process_new_updates([telebot.types.Update.de_json(data)])
    except: pass
    return "OK",200

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))
