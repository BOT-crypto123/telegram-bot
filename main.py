# V54.1 MAQUINA DE HACER DINERO 💰💴💶💵💷💸📊📈 - TITULO CENTRADO LIMPIO
import os, json, requests, random
from flask import Flask, request
from datetime import datetime
import telebot, pytz
TOKEN=os.getenv("BOT_TOKEN","8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot=telebot.TeleBot(TOKEN); app=Flask(__name__)
SYMBOLS=["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]; FILE_STATE="/tmp/estado_demo.json"
FEE_LADO=0.0041; FEE_RT=0.0082
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
    return {"BTC":62800,"ETH":1872,"SOL":74,"NVDA":135,"TSLA":341,"XAUUSD":4437}[s]
def get_velas(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            m={"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/OHLC?pair={m}&interval=5",timeout=6).json()
            k=list(r['result'].keys())[0]; d=r['result'][k][-120:]
            return [float(x[1]) for x in d],[float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d]
    except: pass
    base=get_price(s); c=[base+random.uniform(-3,3) for _ in range(120)]; o=[x+random.uniform(-1,1) for x in c]
    h=[max(a,b)+2 for a,b in zip(o,c)]; l=[min(a,b)-2 for a,b in zip(o,c)]; return o,h,l,c
def rsi_calc(closes,p=14):
    if len(closes)<p+1: return 50
    g=sum(max(0,closes[i]-closes[i-1]) for i in range(-p,0))/p
    l=sum(max(0,closes[i-1]-closes[i]) for i in range(-p,0))/p
    return 70 if l==0 else 100-(100/(1+g/l))
def is_ny():
    tz=pytz.timezone("America/Mexico_City"); n=datetime.now(tz); return 8 <= n.hour < 12
def BOT1_compra(closes):
    lineas=[]
    for i in range(25,len(closes)-10):
        p=closes[i]; rebotes=sum(1 for c in closes[max(0,i-35):i+10] if abs(c-p)/p<0.0025)
        if rebotes>=2: lineas.append({"precio":p,"rebotes":rebotes,"fuerza":min(90,rebotes*15+25)})
    unicas=[]
    for lin in sorted(lineas,key=lambda x:x['rebotes'],reverse=True):
        if not any(abs(lin['precio']-u['precio'])/u['precio']<0.006 for u in unicas): unicas.append(lin)
    lineas=unicas[:6]
    SI=len([l for l in lineas if l['rebotes']>=2])>0
    top=sorted([l for l in lineas if l['rebotes']>=2],key=lambda x:x['rebotes'],reverse=True)[0] if SI else None
    return SI, top, lineas, f"BOT1 COMPRA {'✅ SI' if SI else '❌ NO'} {top['rebotes']}R {top['fuerza']:.0f}%" if SI else "BOT1 COMPRA ❌ NO"
def BOT1_venta(tr, precio, closes):
    bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; max_neto=tr.get("max_neto",neto)
    rompe=abs(precio-tr["linea"])/tr["linea"]>0.015 if "linea" in tr else False
    V=neto>=0.68 or neto<=-4.32 or (max_neto>=0.30 and neto<=max_neto-0.70) or rompe
    mot=f"TP {neto:.2f}%" if neto>=0.68 else f"SL {neto:.2f}%" if neto<=-4.32 else f"TRAIL {max_neto:.2f}->{neto:.2f}%" if (max_neto>=0.30 and neto<=max_neto-0.70) else "RUPTURA" if rompe else "HOLD"
    return V, f"BOT1 VENTA {'✅ VENDE' if V else '❌ HOLD'} {mot}"
def BOT2_compra_NY(closes, top, score):
    ny=is_ny()
    if not ny: return False,0,0,"BOT2 COMPRA ❌ NO - NY 🔴 CERRADO no apoyo a BOT1 ni JEFE"
    if not top: return False,0,0,"BOT2 COMPRA ❌ NO - Sin BOT1"
    conf=sum(1 for c in closes[-50:] if abs(c-top['precio'])/top['precio']<0.003); f2=min(99,conf*18+20); rsi=rsi_calc(closes)
    SI=conf>=3 and f2>=65 and 35<rsi<75 and score>=70
    return SI, conf, f2, f"BOT2 NY 🟢 {'✅ SI APOYA BOT1+JEFE' if SI else '❌ NO'} {conf}tq {f2:.0f}% RSI {rsi:.0f}"
def BOT2_venta(tr, precio, closes):
    bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; max_neto=tr.get("max_neto",neto); rsi=rsi_calc(closes)
    V=neto>=0.68 or neto<=-4.32 or (max_neto>=0.30 and rsi<60) or rsi>72
    mot=f"TP {neto:.2f}%" if neto>=0.68 else f"SL {neto:.2f}%" if neto<=-4.32 else f"RSI TRAIL {rsi:.0f}" if (max_neto>=0.30 and rsi<60) else f"RSI SOBRE {rsi:.0f}" if rsi>72 else "HOLD"
    return V, f"BOT2 VENTA {'✅ VENDE' if V else '❌ HOLD'} {mot}"
def JEFE_compra(top, f2):
    if not top: return False,0,0,"JEFE COMPRA ❌ NO"
    score=min(30,top['rebotes']*5)+top['fuerza']*0.35+f2*0.35
    bola=2500 if score>=90 else 1100 if score>=70 else 0
    ny=is_ny(); ok=ESTADO["demo_balance"] >= bola+bola*FEE_LADO
    SI=score>=70 and bola>0 and ny and ESTADO["auto"] and ok
    return SI, score, bola, f"JEFE COMPRA {'✅ SI' if SI else '❌ NO'} Score {score:.0f}% Bola ${bola} NY {'🟢' if ny else '🔴'}"
def JEFE_venta(tr, precio):
    bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; max_neto=tr.get("max_neto",neto)
    V=neto>=0.68 or neto<=-4.32 or (max_neto>=0.50 and neto<=0.20)
    mot=f"TP ASEG {neto:.2f}%" if neto>=0.68 else f"SL PROT {neto:.2f}%" if neto<=-4.32 else f"ASEGURA {max_neto:.2f}->{neto:.2f}%" if (max_neto>=0.50 and neto<=0.20) else "HOLD"
    return V, f"JEFE VENTA {'✅ VENDE' if V else '❌ HOLD'} {mot}"
def decidir(s):
    opens,highs,lows,closes=get_velas(s); precio=closes[-1]; ventas=[]
    for tr in ESTADO["open_trades"][:]:
        if tr["simbolo"]!=s: continue
        bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100
        tr["max_neto"]=max(tr.get("max_neto",neto),neto)
        v1,t1=BOT1_venta(tr,precio,closes); v2,t2=BOT2_venta(tr,precio,closes); v3,t3=JEFE_venta(tr,precio)
        if sum([v1,v2,v3])>=2:
            gb=tr["bola"]*bruto/100; fee=tr["bola"]*FEE_RT; gn=gb-fee
            ESTADO["demo_balance"]+=tr["bola"]+gn; ESTADO["fees"]+=fee
            ESTADO["open_trades"].remove(tr); save_estado()
            ventas.append(f"💰 VENTA DECISION {sum([v1,v2,v3])}/3 {s}\n {t1}\n {t2}\n {t3}\n BRUTA {bruto:+.2f}% ${gb:+.2f} - COM ${fee:.2f} = NETA {neto:+.2f}% ${gn:+.2f}")
    B1,top,lineas,t1c=BOT1_compra(closes)
    pre=min(30,top['rebotes']*5)+top['fuerza']*0.35+75*0.35 if top else 0
    B2,conf,f2,t2c=BOT2_compra_NY(closes,top,pre)
    J3,score,bola,t3c=JEFE_compra(top,f2 if f2 else 75)
    if top:
        B2,conf,f2,t2c=BOT2_compra_NY(closes,top,score); J3,score,bola,t3c=JEFE_compra(top,f2)
    key=f"{s}_{datetime.now().strftime('%Y-%m-%d')}"; votos=sum([B1,B2,J3])
    det=f"{t1c}\n{t2c}\n{t3c}\n---\nCOMPRA: B1 {'✅' if B1 else '❌'} + B2 NY APOYA {'✅' if B2 else '❌'} + JEFE {'✅' if J3 else '❌'} = {votos}/3 {'💰 COMPRA' if votos==3 else '⏳'}"
    if ventas: det="\n".join(ventas)+"\n\n"+det
    else:
        for tr in ESTADO["open_trades"]:
            if tr["simbolo"]==s:
                v1,t1=BOT1_venta(tr,precio,closes); v2,t2=BOT2_venta(tr,precio,closes); v3,t3=JEFE_venta(tr,precio)
                det+=f"\n---\nVENTA ABIERTA NETA {(precio-tr['entrada_real'])/tr['entrada_real']*100-FEE_RT*100:+.2f}%\n{t1}\n{t2}\n{t3}\nVOTOS {sum([v1,v2,v3])}/3"
    if key in ESTADO["jefe_hoy"]: return {"tipo":"JEFE YA CAZO 1x DIA 🔒","det":det+"\n🔒 Hoy ya cazó","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if not is_ny(): return {"tipo":"NY CERRADO ⏸️ - BOT2 PAUSA COMPRA, VENTAS 2/3","det":det+"\n⏸️ NY cerrado","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if not ESTADO["auto"]: return {"tipo":"AUTO OFF ⛔️","det":det,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if ESTADO["demo_balance"] < bola+bola*FEE_LADO and B1 and B2: return {"tipo":"SALDO INSUFICIENTE 🚫","det":det+f"\n🚫 Necesita ${bola+bola*FEE_LADO:.2f}","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if B1 and B2 and J3:
        fee_e=bola*FEE_LADO; ESTADO["demo_balance"]-=bola+fee_e; ESTADO["fees"]+=fee_e
        ESTADO["open_trades"].append({"simbolo":s,"entrada_real":precio,"entrada":precio*(1+FEE_LADO),"bola":bola,"linea":top['precio'],"max_neto":-10})
        ESTADO["jefe_hoy"][key]=True; save_estado()
        return {"tipo":f"COMPRA 3/3 💰 ${bola}","det":det+f"\n✅ COMPRA 3 BOTS NY INTEGRADOS","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    return {"tipo":f"ESPERA {votos}/3 ⏳","det":det,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}

@app.route('/')
def dash():
    ny=is_ny(); fb=0; fn=0; cards=""; tb=sum(t["bola"] for t in ESTADO["open_trades"])
    for tr in ESTADO["open_trades"]:
        pa=get_price(tr["simbolo"]); br=(pa-tr["entrada_real"])/tr["entrada_real"]*100; gb=tr["bola"]*br/100; fee=tr["bola"]*FEE_RT; ne=br-FEE_RT*100; gn=tr["bola"]*ne/100; fb+=gb; fn+=gn; col="#00ff88" if gn>=0 else "#ff4444"
        v1,_=BOT1_venta(tr,pa,get_velas(tr["simbolo"])[3]); v2,_=BOT2_venta(tr,pa,get_velas(tr["simbolo"])[3]); v3,_=JEFE_venta(tr,pa)
        cards+=f'<div style="background:#001a0a;border:1px solid #00ff88;border-radius:10px;padding:10px;margin:8px 0"><b>{tr["simbolo"]} ${tr["bola"]}</b> BRUTA {br:+.2f}% - COM ${fee:.2f} = <b style="color:{col}">NETA {ne:+.2f}% ${gn:+.2f}</b><br><small>B1 {"✅" if v1 else "❌"} B2 {"✅" if v2 else "❌"} J3 {"✅" if v3 else "❌"} = {sum([v1,v2,v3])}/3</small></div>'
    ca=sum(t["bola"]*FEE_RT for t in ESTADO["open_trades"]); pat=ESTADO["demo_balance"]+tb+fn
    modo=f'🟢 NY ABIERTO - BOT2 APOYA BOT1 Y JEFE' if ny and ESTADO["auto"] else f'🔴 NY CERRADO - VENTAS 2/3'
    # TITULO CENTRADO LIMPIO - SOLO LO QUE MARCASTE EN ROJO
    h=f'''<html><head><meta name="viewport" content="width=device-width"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.titulo{{background:#111;border:3px solid #FFD700;border-radius:16px;padding:22px;margin-bottom:14px;display:flex;justify-content:center;align-items:center;text-align:center}}.titulo h1{{margin:0;font-size:28px;line-height:1.3;text-align:center;color:#fff;font-weight:bold;width:100%}}.header{{background:#111;border:2px solid #00ff88;border-radius:14px;padding:14px;text-align:left}}.card{{background:#111;border:1px solid #222;border-radius:14px;padding:14px;margin:10px 0}}.btn{{background:#00ff88;color:#000;padding:8px 14px;border-radius:8px;text-decoration:none}}</style></head><body>
    <div class="titulo"><h1>💰 V54.1 MAQUINA DE HACER DINERO 💰💴💶💵💷💸📊📈</h1></div>
    <div class="header">{modo}<br>💳 LIQUIDO ${ESTADO["demo_balance"]:.2f} | EN BOLAS ${tb:.2f} | 📊 BRUTA ${fb:+.2f} - COM ${ca:.2f} = NETA REAL ${fn:+.2f}<br>🏦 PATRIMONIO ${pat:.2f} ({pat-10000:+.2f})<br><small>BOT1 ruptura | BOT2 NY RSI apoya BOT1+JEFE | JEFE asegura | COMPRA 3/3 VENTA 2/3</small></div>
    <div style="background:#111;border:2px solid #00ff88;border-radius:14px;padding:14px;margin-top:10px"><b>FLOTANTE NETA {fn:+.2f} ({len(ESTADO["open_trades"])})</b><br>{cards if cards else "Sin posiciones - Esperando 3/3"}</div><br>'''
    for s in SYMBOLS:
        d=decidir(s); h+=f'<div class="card"><b>{s}</b> ${get_price(s):.2f} - {d["tipo"]}<br><small>{d["det"].replace(chr(10),"<br>")}</small><br><br><a class="btn" href="/graf/{s}">GRAFICA 📈</a></div>'
    return h+"</body></html>"

@app.route('/graf/<s>')
def graf(s):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    s=s.upper(); opens,highs,lows,closes=get_velas(s); d=decidir(s)
    fig=plt.figure(figsize=(12,6),facecolor='black'); ax=plt.subplot2grid((4,1),(0,0),rowspan=3,facecolor='black'); ax2=plt.subplot2grid((4,1),(3,0),facecolor='black')
    n=len(closes); st=max(0,n-80)
    for i in range(st,n):
        col='#00ff88' if closes[i]>=opens[i] else '#ff4444'; ax.plot([i,i],[lows[i],highs[i]],color=col,lw=1); ax.plot([i,i],[opens[i],closes[i]],color=col,lw=3)
    for x in d["lineas"]: ax.axhline(x['precio'],color='#00ff00',ls='--',alpha=0.8)
    for tr in ESTADO["open_trades"]:
        if tr["simbolo"]==s: ax.axhline(tr["entrada_real"],color='orange',ls='-',alpha=0.9)
    ax.set_xlim(st,n); ax.set_title(f'{s} V54.1',color='white',fontsize=10); ax.tick_params(colors='white')
    rsi_vals=[rsi_calc(closes[:i+1]) for i in range(15,len(closes))]; ax2.plot(range(len(closes)-len(rsi_vals),len(closes)),rsi_vals,color='#00ffff')
    import io,base64; buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=130); buf.seek(0); img=base64.b64encode(buf.read()).decode(); plt.close('all')
    return f'<html style="background:#000;color:#fff"><body><h2>{s} V54.1 MAQUINA DE HACER DINERO</h2><pre>{d["det"]}</pre><img src="data:image/png;base64,{img}" style="width:100%"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:bold">VOLVER</a></body></html>'

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.strip().upper()
    if "BALANCE" in t or "/BALANCE" in t or "STATS" in t:
        tb=sum(tr["bola"] for tr in ESTADO["open_trades"]); fb=0; fn=0; lines=[]
        ca=sum(tr["bola"]*FEE_RT for tr in ESTADO["open_trades"])
        for tr in ESTADO["open_trades"]:
            pa=get_price(tr["simbolo"]); br=(pa-tr["entrada_real"])/tr["entrada_real"]*100; gb=tr["bola"]*br/100; fee=tr["bola"]*FEE_RT; ne=br-FEE_RT*100; gn=tr["bola"]*ne/100
            fb+=gb; fn+=gn
            v1,_=BOT1_venta(tr,pa,get_velas(tr["simbolo"])[3]); v2,_=BOT2_venta(tr,pa,get_velas(tr["simbolo"])[3]); v3,_=JEFE_venta(tr,pa)
            lines.append(f"🔹 {tr['simbolo']} Bola ${tr['bola']}\n {tr['entrada_real']:.2f}->{pa:.2f}\n BRUTA {br:+.2f}% ${gb:+.2f} - COM ${fee:.2f} = NETA {ne:+.2f}% ${gn:+.2f}\n VOTOS {sum([v1,v2,v3])}/3")
        pat=ESTADO["demo_balance"]+tb+fn
        ny_txt="🟢 NY ABIERTO" if is_ny() else "🔴 NY CERRADO"
        flot_txt="\n\n".join(lines) if lines else "Sin posiciones - Esperando 3/3"
        msg=f'''💰 V54.1 MAQUINA DE HACER DINERO 💰💴💶💵💷💸📊📈
{ny_txt} - VENTAS 2/3
💳 LIQUIDO ${ESTADO["demo_balance"]:.2f}
💼 EN BOLAS ${tb:.2f}
📊 BRUTA ${fb:+.2f} - COM ${ca:.2f} = NETA REAL ${fn:+.2f}
🏦 PATRIMONIO ${pat:.2f} ({pat-10000:+.2f})
💸 FEES ${ESTADO["fees"]:.2f}
BOT1 ruptura | BOT2 NY RSI apoya BOT1+JEFE | JEFE asegura | COMPRA 3/3 VENTA 2/3

FLOTANTE NETA {fn:+.2f} ({len(ESTADO["open_trades"])})
{flot_txt}

https://telegram-bot-cijp.onrender.com/
'''
        bot.send_message(m.chat.id, msg); return
    if t=="DASHBOARD": bot.send_message(m.chat.id,f"💰 V54.1 💰💴💶💵💷💸📊📈\nhttps://telegram-bot-cijp.onrender.com/")
    elif "AUTO" in t:
        if "ON" in t: ESTADO["auto"]=True; save_estado(); bot.send_message(m.chat.id,"✅ AUTO ON V54.1")
        else: ESTADO["auto"]=False; save_estado(); bot.send_message(m.chat.id,"⛔️ AUTO OFF")
    elif t in SYMBOLS: d=decidir(t); bot.send_message(m.chat.id,f"💰 {t} ${get_price(t):.2f}\n{d['det']}\n{d['tipo']}\nhttps://telegram-bot-cijp.onrender.com/graf/{t}")
    else: bot.send_message(m.chat.id,"💰 V54.1 MAQUINA DE HACER DINERO 💰💴💶💵💷💸📊📈\n/balance - Balance completo\nBTC ETH SOL NVDA TSLA XAUUSD")

@app.route('/webhook',methods=['POST'])
@app.route(f'/{TOKEN}',methods=['POST'])
def hook():
    try:
        data=request.get_data().decode()
        if data: bot.process_new_updates([telebot.types.Update.de_json(data)])
    except: pass
    return "OK",200
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))
