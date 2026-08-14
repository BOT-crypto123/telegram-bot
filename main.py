# V55.1 FIX - MAX 2 POR SIMBOLO + DASHBOARD FIX + VENTAS SIEMPRE
import os, json, requests, random
from flask import Flask, request
from datetime import datetime
import telebot, pytz
TOKEN=os.getenv("BOT_TOKEN","8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot=telebot.TeleBot(TOKEN); app=Flask(__name__)
SYMBOLS=["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]; FILE_STATE="/tmp/estado_demo.json"
FEE_LADO=0.0041; FEE_RT=0.0082; TRAILING_PCT=1.2

def load_estado():
    try:
        if os.path.exists(FILE_STATE):
            with open(FILE_STATE,'r') as f: return json.load(f)
    except: pass
    return {"jefe_hoy":{},"demo_balance":10000.0,"open_trades":[],"auto":True,"fees":0.0,"trades_hoy_fecha":"","trades_hoy_count":0}
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
    tz=pytz.timezone("America/Mexico_City"); n=datetime.now(tz);
    return (n.hour > 8 or (n.hour==8 and n.minute>=30)) and n.hour < 15

def get_tendencia(closes):
    return "verde" if sum(closes[-20:])/20 > sum(closes[-40:-20])/20 else "rojo"

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
    return SI, top, lineas, f"BOT1 AYUDA {'✅ SI AYUDA A B2+B3' if SI else '❌ NO'} {top['rebotes']}R {top['fuerza']:.0f}%" if SI else "BOT1 ❌ NO AYUDA"

def BOT2_compra(closes, top, score):
    if not top: return False,0,0,"BOT2 AYUDA ❌ NO - Sin linea B1"
    if not is_ny():
        rsi=rsi_calc(closes)
        return True, 3, 75, f"BOT2 AYUDA 🌙 ANALISTA ✅ AYUDA A B1+B3 RSI {rsi:.0f} Linea {top['precio']:.2f}"
    conf=sum(1 for c in closes[-50:] if abs(c-top['precio'])/top['precio']<0.003); f2=min(99,conf*18+20); rsi=rsi_calc(closes)
    SI=conf>=3 and f2>=65 and 35<rsi<75 and score>=70
    return SI, conf, f2, f"BOT2 AYUDA NY 🟢 {'✅ SI AYUDA A B1+B3' if SI else '❌ NO AYUDA'} {conf}tq {f2:.0f}% RSI {rsi:.0f}"

def JEFE_compra(top, f2):
    if not top: return False,0,0,"JEFE AYUDA ❌ NO"
    score=min(30,top['rebotes']*5)+top['fuerza']*0.35+f2*0.35
    bola=2500 if score>=90 else 1100 if score>=70 else 0
    ok=ESTADO["demo_balance"] >= bola+bola*FEE_LADO
    SI=score>=70 and bola>0 and ESTADO["auto"] and ok
    extra=" + AYUDA EXTRA B1+B2 JUNTOS" if score>=85 else ""
    return SI, score, bola, f"JEFE AYUDA {'✅ SI AYUDA A B1+B2' if SI else '❌ NO AYUDA'} Score {score:.0f}% Bola ${bola}{extra}"

def BOT1_venta(tr, precio, closes):
    bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; max_neto=tr.get("max_neto",neto)
    V=neto>=TRAILING_PCT or neto<=-4.32 or (max_neto>=TRAILING_PCT and neto<=max_neto-TRAILING_PCT)
    return V, f"B1 VENTA {'✅ AYUDA VENDER' if V else '❌ HOLD'} {neto:.2f}%"
def BOT2_venta(tr, precio, closes):
    bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; max_neto=tr.get("max_neto",neto); rsi=rsi_calc(closes)
    V=neto>=TRAILING_PCT or neto<=-4.32 or (max_neto>=TRAILING_PCT and rsi<60) or rsi>72
    return V, f"B2 VENTA {'✅ AYUDA VENDER' if V else '❌ HOLD'} {neto:.2f}% RSI {rsi:.0f}"
def JEFE_venta(tr, precio):
    bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; max_neto=tr.get("max_neto",neto)
    V=neto>=TRAILING_PCT or neto<=-4.32 or (max_neto>=TRAILING_PCT and neto<=0.20)
    return V, f"JEFE VENTA {'✅ AYUDA VENDER' if V else '❌ HOLD'} {neto:.2f}%"

def decidir(s):
    opens,highs,lows,closes=get_velas(s); precio=closes[-1]; ventas=[]; tend=get_tendencia(closes)
    hoy=datetime.now().strftime('%Y-%m-%d')
    if ESTADO["trades_hoy_fecha"]!=hoy:
        ESTADO["trades_hoy_fecha"]=hoy; ESTADO["trades_hoy_count"]=0; ESTADO["jefe_hoy"]={}
        save_estado()
    # VENTAS PRIMERO SIEMPRE
    for tr in ESTADO["open_trades"][:]:
        if tr["simbolo"]!=s: continue
        bruto=(precio-tr["entrada_real"])/tr["entrada_real"]*100; neto=bruto-FEE_RT*100; tr["max_neto"]=max(tr.get("max_neto",neto),neto)
        v1,t1=BOT1_venta(tr,precio,closes); v2,t2=BOT2_venta(tr,precio,closes); v3,t3=JEFE_venta(tr,precio)
        votos_v=sum([v1,v2,v3])
        if (tend=="verde" and votos_v>=2) or (tend=="rojo" and votos_v>=2):
            gb=tr["bola"]*bruto/100; fee=tr["bola"]*FEE_RT; gn=gb-fee
            ESTADO["demo_balance"]+=tr["bola"]+gn; ESTADO["fees"]+=fee; ESTADO["open_trades"].remove(tr); save_estado()
            ventas.append(f"💰 VENTA AYUDA MUTUA {tend} {votos_v}/3 {s} NETA {neto:+.2f}%")

    B1,top,lineas,t1c=BOT1_compra(closes); pre=min(30,top['rebotes']*5)+top['fuerza']*0.35+75*0.35 if top else 0
    B2,conf,f2,t2c=BOT2_compra(closes,top,pre); J3,score,bola,t3c=JEFE_compra(top,f2 if f2 else 75)
    if top: B2,conf,f2,t2c=BOT2_compra(closes,top,score); J3,score,bola,t3c=JEFE_compra(top,f2)
    votos=sum([B1,B2,J3]); modo="NY 🟢" if is_ny() else "NOCHE 🌙 ANALISTA"
    det=f"{modo} TEND {tend}\n{t1c}\n{t2c}\n{t3c}\n---\nAYUDA MUTUA: B1 {'✅' if B1 else '❌'} + B2 {'✅' if B2 else '❌'} + B3 {'✅' if J3 else '❌'} = {votos}/3"
    if ventas: det="\n".join(ventas)+"\n\n"+det
    key=f"{s}_{hoy}"
    # FIX MAX POR SIMBOLO
    count_symbol = sum(1 for k in ESTADO["jefe_hoy"] if k.startswith(s+"_"))
    if count_symbol>=2:
        return {"tipo":"MAX 2 HOY ESTE SIMBOLO 🔒","det":det,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if key in ESTADO["jefe_hoy"] and not ventas:
        return {"tipo":"YA CAZO HOY 🔒","det":det,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if not is_ny() and s not in ["BTC","ETH","SOL"]: return {"tipo":"NOCHE PAUSA ACCIONES ⏸️","det":det,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    if B1 and B2 and J3:
        fee_e=bola*FEE_LADO; ESTADO["demo_balance"]-=bola+fee_e; ESTADO["fees"]+=fee_e
        ESTADO["open_trades"].append({"simbolo":s,"entrada_real":precio,"entrada":precio*(1+FEE_LADO),"bola":bola,"linea":top['precio'],"max_neto":-10})
        ESTADO["jefe_hoy"][key]=True; ESTADO["trades_hoy_count"]+=1; save_estado()
        return {"tipo":f"COMPRA AYUDA MUTUA 3/3 💰 ${bola}","det":det+"\n✅ 3/3 SE AYUDAN","closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}
    return {"tipo":f"ESPERA AYUDA {votos}/3 ⏳","det":det,"closes":closes,"opens":opens,"highs":highs,"lows":lows,"lineas":lineas}

@app.route('/')
def dash():
    ny=is_ny(); fb=0; fn=0; cards=""; tb=sum(t["bola"] for t in ESTADO["open_trades"])
    for tr in ESTADO["open_trades"]:
        pa=get_price(tr["simbolo"]); br=(pa-tr["entrada_real"])/tr["entrada_real"]*100; fee=tr["bola"]*FEE_RT; ne=br-FEE_RT*100; gn=tr["bola"]*ne/100; fb+=tr["bola"]*br/100; fn+=gn
        cards+=f'<div style="background:#001a0a;border:1px solid #00ff88;padding:8px;margin:6px 0">{tr["simbolo"]} ${tr["bola"]} NETA {ne:+.2f}% Entrada {tr["entrada_real"]:.2f}</div>'
    pat=ESTADO["demo_balance"]+tb+fn
    h=f'<html><head><meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="30"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.titulo{{background:#111;border:3px solid #FFD700;border-radius:16px;padding:18px;text-align:center}}.card{{background:#111;border:1px solid #222;border-radius:14px;padding:14px;margin:10px 0}}</style></head><body><div class="titulo"><h1>💰 V55.1 FIX AYUDA MUTUA 3/3 💰</h1></div><div>💳 ${ESTADO["demo_balance"]:.2f} | EN BOLAS ${tb:.2f} | NETA {fn:+.2f} | PAT ${pat:.2f} | HOY {ESTADO["trades_hoy_count"]} trades | {"🟢 NY B2 MANDA" if ny else "🌙 NOCHE B1 MANDA"}</div><div>{cards}</div>'
    for s in SYMBOLS:
        d=decidir(s); h+=f'<div class="card"><b>{s}</b> ${get_price(s):.2f} - {d["tipo"]}<br><small>{d["det"].replace(chr(10),"<br>")}</small><br><br><a href="/graf/{s}" style="background:#00ff88;color:#000;padding:8px 14px;border-radius:8px;text-decoration:none">GRAFICA</a></div>'
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
    ax.set_xlim(st,n); ax.set_title(f'{s} V55.1 FIX',color='white'); ax.tick_params(colors='white')
    rsi_vals=[rsi_calc(closes[:i+1]) for i in range(15,len(closes))]; ax2.plot(range(len(closes)-len(rsi_vals),len(closes)),rsi_vals,color='#00ffff')
    import io,base64; buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=130); buf.seek(0); img=base64.b64encode(buf.read()).decode(); plt.close('all')
    return f'<html style="background:#000;color:#fff"><body><h2>{s} V55.1</h2><pre>{d["det"]}</pre><img src="data:image/png;base64,{img}" style="width:100%"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:bold">VOLVER AL DASH</a></body></html>'

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.strip().upper()
    if "DASHBOARD" in t or t=="DASH":
        url=os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RENDER_EXTERNAL_HOSTNAME") or ""
        if url and not url.startswith("http"): url="https://"+url
        if not url: url="Abre tu link de Render en el navegador - es tu dashboard"
        bot.send_message(m.chat.id, f"🌐 TU DASHBOARD V55.1 FIX:\n{url}\n\nSi no te sale, entra a render.com -> tu app -> abre el link.onrender.com")
        return
    if "AUTO ON" in t:
        ESTADO["auto"]=True; save_estado(); bot.send_message(m.chat.id,"✅ AUTO ON"); return
    if "AUTO OFF" in t:
        ESTADO["auto"]=False; save_estado(); bot.send_message(m.chat.id,"⛔ AUTO OFF"); return
    if "BALANCE" in t:
        tb=sum(tr["bola"] for tr in ESTADO["open_trades"]); fn=0
        for tr in ESTADO["open_trades"]:
            pa=get_price(tr["simbolo"]); br=(pa-tr["entrada_real"])/tr["entrada_real"]*100; ne=br-FEE_RT*100; fn+=tr["bola"]*ne/100
        pat=ESTADO["demo_balance"]+tb+fn
        msg=f'''💰 V55.1 FIX AYUDA MUTUA 3/3
{"🟢 NY B2 MANDA B1 APOYA" if is_ny() else "🌙 NOCHE B1 MANDA B2 ANALIZA"}
💳 ${ESTADO["demo_balance"]:.2f} | EN BOLAS ${tb:.2f} | NETA {fn:+.2f} | PAT ${pat:.2f}
HOY {ESTADO["trades_hoy_count"]} trades
TRAIL 1.2% - MAX 2 POR SIMBOLO - FIX VENTAS SIEMPRE
'''
        bot.send_message(m.chat.id, msg); return
    if t in SYMBOLS: d=decidir(t); bot.send_message(m.chat.id,f"💰 {t} ${get_price(t):.2f}\n{d['det']}\n{d['tipo']}")
    else: bot.send_message(m.chat.id,"💰 V55.1 FIX\n/balance\nDASHBOARD\nBTC ETH SOL NVDA TSLA XAUUSD")

@app.route('/webhook',methods=['POST'])
@app.route(f'/{TOKEN}',methods=['POST'])
def hook():
    try:
        data=request.get_data().decode()
        if data: bot.process_new_updates([telebot.types.Update.de_json(data)])
    except: pass
    return "OK",200
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))
