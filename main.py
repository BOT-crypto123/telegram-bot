import os,json,requests,random
from flask import Flask,request,redirect
from datetime import datetime
import telebot,pytz

TOKEN=os.getenv("BOT_TOKEN","8805451290:AAfie2WdkcQYM7MrG79BzD1Es_xVrHtXJ5M")
bot=telebot.TeleBot(TOKEN)
app=Flask(__name__)
SYM=["BTC","ETH","SOL","NVDA","TSLA","XAUUSD"]
FILE="/tmp/estado_demo.json"
FL=0.0041
FR=0.0082

def load():
    try:
        if os.path.exists(FILE):
            with open(FILE,'r') as f:
                e=json.load(f)
                e.setdefault("trail",0.1)
                e.setdefault("max_ab",4)
                e.setdefault("fees",0)
                return e
    except: pass
    return {"bal":10000,"tr":[],"auto":True,"fees":0,"trail":0.1,"max_ab":4,"jh":{},"f":""}

def save():
    try:
        with open(FILE,'w') as f:
            json.dump(E,f)
    except: pass

E=load()

def price(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            m={"BTC":"XBTUSD","ETH":"ETHUSD","SOL":"SOLUSD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={m}",timeout=5).json()
            return float(list(r['result'].values())[0]['c'][0])
    except: pass
    return {"BTC":62800,"ETH":1872,"SOL":74,"NVDA":135,"TSLA":341,"XAUUSD":4437}[s]

def velas(s):
    try:
        if s in ["BTC","ETH","SOL"]:
            m={"BTC":"XBT/USD","ETH":"ETH/USD","SOL":"SOL/USD"}[s]
            r=requests.get(f"https://api.kraken.com/0/public/OHLC?pair={m}&interval=5",timeout=6).json()
            k=list(r['result'].keys())[0]
            d=r['result'][k][-120:]
            return [float(x[1]) for x in d],[float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d]
    except: pass
    b=price(s)
    c=[b+random.uniform(-3,3) for _ in range(120)]
    o=[x+random.uniform(-1,1) for x in c]
    h=[max(a,b)+2 for a,b in zip(o,c)]
    l=[min(a,b)-2 for a,b in zip(o,c)]
    return o,h,l,c

def decidir(s):
    o,h,l,c=velas(s)
    pr=c[-1]
    hoy=datetime.now().strftime('%Y-%m-%d')
    if E["f"]!=hoy:
        E["f"]=hoy
        E["jh"]={}
        save()
    tr=E["trail"]
    mx=E["max_ab"]
    for t in E["tr"][:]:
        if t["s"]!=s: continue
        br=(pr-t["e"])/t["e"]*100
        ne=br-FR*100
        t["mx"]=max(t.get("mx",ne),ne)
        if ne>=tr or ne<=-4.32 or (t["mx"]>=tr and ne<=t["mx"]-tr):
            gn=t["b"]*br/100-t["b"]*FR
            E["bal"]+=t["b"]+gn
            E["fees"]+=t["b"]*FR
            E["tr"].remove(t)
            save()
    if len(E["tr"])>=mx:
        return f"MAX {mx} {len(E['tr'])}/{mx}","Esperando",c
    sc=random.randint(68,88)
    bola=1100
    if sc>=65 and E["bal"]>=bola+bola*FL and E["auto"]:
        E["bal"]-=bola+bola*FL
        E["fees"]+=bola*FL
        E["tr"].append({"s":s,"e":pr,"b":bola,"mx":-10})
        save()
        return f"COMPRA {bola}",f"SI {sc}% TRAIL {tr}%",c
    return f"ESPERA {sc}%",f"TRAIL {tr}%",c

@app.route('/set_max/<int:n>')
def sm(n):
    E["max_ab"]=max(1,min(10,n))
    save()
    return redirect('/')

@app.route('/add_max/<int:d>')
def am(d):
    E["max_ab"]=max(1,min(10,E["max_ab"]+d))
    save()
    return redirect('/')

@app.route('/set_trail/<float:v>')
def st(v):
    E["trail"]=round(max(0.1,min(3.0,v)),2)
    save()
    return redirect('/')

@app.route('/add_trail/<float:d>')
def at(d):
    E["trail"]=round(max(0.1,min(3.0,E["trail"]+d)),2)
    save()
    return redirect('/')

@app.route('/buy/<s>/<int:b>')
def buy(s,b):
    s=s.upper()
    if len(E["tr"])>=E["max_ab"]:
        return redirect('/')
    if E["bal"]<b+b*FL:
        return redirect('/')
    E["bal"]-=b+b*FL
    E["fees"]+=b*FL
    E["tr"].append({"s":s,"e":price(s),"b":b,"mx":-10})
    save()
    return redirect('/')

@app.route('/sell/<int:i>')
def sell(i):
    try:
        if 0<=i<len(E["tr"]):
            t=E["tr"][i]
            pa=price(t["s"])
            br=(pa-t["e"])/t["e"]*100
            gn=t["b"]*br/100-t["b"]*FR
            E["bal"]+=t["b"]+gn
            E["fees"]+=t["b"]*FR
            E["tr"].pop(i)
            save()
    except: pass
    return redirect('/')

@app.route('/sell_s/<s>')
def sells(s):
    s=s.upper()
    for t in E["tr"][:]:
        if t["s"]==s:
            pa=price(s)
            br=(pa-t["e"])/t["e"]*100
            gn=t["b"]*br/100-t["b"]*FR
            E["bal"]+=t["b"]+gn
            E["fees"]+=t["b"]*FR
            E["tr"].remove(t)
    save()
    return redirect('/')

@app.route('/')
def dash():
    tb=sum(t["b"] for t in E["tr"])
    fn=0; fb=0; fr=0
    cards=""
    for idx,t in enumerate(E["tr"]):
        pa=price(t["s"])
        br=(pa-t["e"])/t["e"]*100
        ne=br-FR*100
        gn_bruto=t["b"]*br/100
        gn_neto=t["b"]*ne/100
        fee=t["b"]*FR
        fb+=gn_bruto
        fr+=fee
        fn+=gn_neto
        col="#f44" if ne<0 else "#0f8"
        cards+=f'<div style="background:#001a0a;border:1px solid {col};padding:8px;margin:6px 0;border-radius:8px"><b>{t["s"]}</b> ${t["b"]} E:{t["e"]:.2f} -> A:{pa:.2f}<br><span style="color:{col}">Bruto {br:+.2f}% | Neto RETAIL {ne:+.2f}%</span><br><small>Bruto ${gn_bruto:+.2f} - Fee ${fee:.2f} = <b>RETAIL ${gn_neto:+.2f}</b></small> <a href="/sell/{idx}" style="background:#f44;color:#fff;padding:4px 10px;border-radius:6px;float:right;text-decoration:none">X</a></div>'
    pat=E["bal"]+tb+fn
    tr=E["trail"]
    mx=E["max_ab"]
    ab=len(E["tr"])
    def bm(n):
        a=mx==n
        bg="#0f8" if a else "#222"
        co="#000" if a else "#fff"
        return f'<a href="/set_max/{n}" style="background:{bg};color:{co};padding:6px 10px;border-radius:6px;margin:2px;text-decoration:none">{n}</a>'
    def bt(v):
        a=abs(tr-v)<0.01
        bg="gold" if a else "#222"
        co="#000" if a else "#fff"
        return f'<a href="/set_trail/{v}" style="background:{bg};color:{co};padding:6px 8px;border-radius:6px;margin:2px;text-decoration:none">{v}%</a>'
    h=f'''<html><head><meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="15"><style>body{{background:#000;color:#fff;font-family:Arial;padding:8px}}.b{{background:#111;border:2px solid #0f8;border-radius:12px;padding:10px;margin:8px 0}}</style></head><body>
    <div style="background:#111;border:3px solid gold;border-radius:14px;padding:12px;text-align:center"><h2 style="margin:0">V58 TRAIL {tr}% MAX {mx}</h2><small>{ab}/{mx} | RETAIL desde 0,1% = $1.10 limpio</small></div>
    <div class=b><b>MAX {ab}/{mx}</b> <a href="/add_max/-1" style="background:#444;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">-</a> {bm(1)} {bm(2)} {bm(3)} {bm(4)} {bm(5)} {bm(6)} <a href="/add_max/1" style="background:#444;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">+</a></div>
    <div class=b><b>TRAIL {tr}%</b> <a href="/add_trail/-0.1" style="background:#444;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">-</a> {bt(0.1)} {bt(0.2)} {bt(0.3)} {bt(0.4)} {bt(0.6)} {bt(0.8)} {bt(1.0)} <a href="/add_trail/0.1" style="background:#444;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">+</a><br><small>0.1% = $1.10 retail limpio con fees</small></div>
    <div class=b style="border-color:gold">EFECTIVO ${E["bal"]:.0f} | EN BOLAS ${tb:.0f}<br>FLOT BRUTO ${fb:+.2f} - FEES ${fr:.2f} = <b style="color:{'#0f8' if fn>=0 else '#f44'}">FLOT RETAIL ${fn:+.2f}</b><br>PAT ${pat:.0f} | UTIL TOTAL {pat-10000:+.2f} | FEES PAGADOS ${E["fees"]:.2f}</div>
    <div>{cards}</div>'''
    for s in SYM:
        ty,de,cl=decidir(s)
        h+=f'<div class=b><b>{s}</b> {ty}<br><small>{de}</small><br><a href="/buy/{s}/1100" style="background:#0f8;color:#000;padding:6px 8px;border-radius:6px;text-decoration:none;margin:2px;display:inline-block">COMPRAR 1100</a><a href="/sell_s/{s}" style="background:#f44;color:#fff;padding:6px 8px;border-radius:6px;text-decoration:none;margin:2px;display:inline-block">VENDER {s}</a></div>'
    return h+'</body></html>'

@bot.message_handler(func=lambda m: True)
def allm(m):
    txt=m.text.upper().strip()
    if "RESET" in txt:
        E.update({"bal":10000,"tr":[],"fees":0,"jh":{},"f":""})
        save()
        bot.send_message(m.chat.id,f"RESET OK\nTRAIL {E['trail']}% MAX {E['max_ab']}\n$10000")
        return
    if "DASHBOARD" in txt or "DASH" in txt:
        bot.send_message(m.chat.id,f"https://telegram-bot-cijp.onrender.com\nTRAIL {E['trail']}% MAX {E['max_ab']} | {len(E['tr'])}/{E['max_ab']}")
        return
    if "AUTO ON" in txt:
        E["auto"]=True
        save()
        bot.send_message(m.chat.id,"AUTO ON")
        return
    if "AUTO OFF" in txt:
        E["auto"]=False
        save()
        bot.send_message(m.chat.id,"AUTO OFF")
        return
    if "/BALANCE" in txt or "BALANCE" in txt:
        tb=sum(t["b"] for t in E["tr"])
        fn=sum(t["b"]*((price(t["s"])-t["e"])/t["e"]*100-FR*100)/100 for t in E["tr"])
        pat=E["bal"]+tb+fn
        bot.send_message(m.chat.id,f"EF ${E['bal']:.0f} PAT ${pat:.0f} UTIL {pat-10000:+.2f}\nFLOT RETAIL ${fn:+.2f}\nTRAIL {E['trail']}%")
        return
    if txt in SYM:
        ty,de,cl=decidir(txt)
        bot.send_message(m.chat.id,f"{txt} ${price(txt):.1f}\n{ty}\n{de}")
        return
    bot.send_message(m.chat.id,f"BTC ETH SOL NVDA TSLA XAUUSD\nAUTO ON/OFF DASHBOARD /balance RESET\nTRAIL {E['trail']}% MAX {E['max_ab']}")

@app.route('/webhook',methods=['POST'])
@app.route(f'/{TOKEN}',methods=['POST'])
def hook():
    try:
        d=request.get_data().decode()
        if d:
            bot.process_new_updates([telebot.types.Update.de_json(d)])
    except: pass
    return "OK",200

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv("PORT",10000)))
