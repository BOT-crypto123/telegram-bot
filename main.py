import os, json, requests, threading, time
from flask import Flask, request, jsonify
app = Flask(__name__)
FILE="bot_data.json"
data={"b":5000.0,"pos":[],"gan_total":0.0,"gan_hoy":0.0,"trades_hoy":0,"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"alert_users":[],"auto_buy":True,"scoring":{"BTC":5,"ETH":4,"SOL":4,"XRP":3,"AVAX":3,"LINK":3,"DOGE":3,"ADA":3}}
CACHE={"prices":{},"ts":0}
def load():
    if os.path.exists(FILE):
        try:
            j=json.load(open(FILE))
            for k in data:
                if k in j: data[k]=j[k]
        except: pass
def save(): json.dump(data,open(FILE,'w'),indent=2)
load()

def P(sym):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}USDT",timeout=3).json()
        return float(r['price'])
    except: return 0
def K(sym,lim=80):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit={lim}",timeout=5).json()
        return r
    except: return []
def EMA(closes,p=20):
    if not closes: return 0
    if len(closes)<p: return closes[-1]
    ema=closes[0]; k=2/(p+1)
    for c in closes[1:]: ema=c*k+ema*(1-k)
    return ema
def RSI(closes,p=14):
    if len(closes)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 100
    return 100-(100/(1+g/l))
def AN(sym):
    kl=K(sym)
    if not kl: return 50,P(sym),0,0
    closes=[float(x[4]) for x in kl]
    rsi=RSI(closes); ema20=EMA(closes,20); price=closes[-1]
    btc_t=0
    try:
        bk=K("BTC",3)
        if len(bk)>=2: btc_t=((float(bk[-1][4])-float(bk[-2][4]))/float(bk[-2][4]))*100
    except: pass
    return rsi,price,ema20,btc_t
def totals():
    val=0
    for p in data['pos']:
        pr=P(p['sym'])
        if p.get('precio_entry',0)>0: p['gan']=((pr-p['precio_entry'])/p['precio_entry'])*100
        val+=p['monto']*(1+p.get('gan',0)/100)
    return data['b']+val,val
def tg(uid,txt):
    try:
        TOKEN=os.getenv("TELEGRAM_TOKEN","")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":uid,"text":txt},timeout=5)
    except: pass

@app.route('/api/prices')
def api_prices():
    if time.time()-CACHE["ts"]<15 and CACHE["prices"]: return jsonify(CACHE["prices"])
    out={}
    for sym in data["coins"]:
        rsi,price,ema20,btc_t=AN(sym)
        filt = price>ema20 and btc_t>-1.5
        action="COMPRAR" if rsi<32 and filt and data.get('auto_buy',True) else "VENDER" if rsi>74 else "SOSTENER"
        out[sym]={"price":price,"rsi":round(rsi,1),"ema20":round(ema20,2),"btc_t":round(btc_t,2),"action":action,"filt":filt,"score":data["scoring"].get(sym,3)}
    CACHE["prices"]=out; CACHE["ts"]=time.time()
    return jsonify(out)

@app.route('/api/status')
def api_status():
    return jsonify({"auto_buy": data.get('auto_buy', True)})

@app.route('/toggle_auto')
def toggle_auto():
    data['auto_buy']=not data.get('auto_buy',True)
    save()
    return "<script>location='/dashboard'</script>"

@app.route('/')
@app.route('/dashboard')
def dash():
    total,val=totals()
    pos_html=""
    for p in data['pos']:
        pr=P(p['sym']); col="#00ff88" if p.get('gan',0)>=0 else "#ff4444"
        pos_html+=f"<div style=display:flex;justify-content:space-between;padding:6px;border-bottom:1px solid #222><span>{p['sym']} Entry ${p.get('precio_entry',0):.2f} Ahora ${pr:.2f} <span style=color:{col}>{p.get('gan',0):.2f}%</span> Max ${p.get('max_price',pr):.2f}</span> <a href='/sell/{p['sym']}' style=background:#ff3344;color:#fff;padding:2px 8px;border-radius:6px;text-decoration:none'>VENDER</a></div>"
    if not pos_html: pos_html="Sin posiciones - AUTO OFF = solo compras manuales por botón o Telegram"

    return f"""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}}.top{{display:flex;justify-content:space-between;align-items:center;background:#111;padding:12px;border-radius:16px;border:1px solid #00ff88;margin-bottom:8px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.card{{background:#151515;border:2px solid #ffcc00;border-radius:18px;padding:10px;min-height:110px;cursor:pointer}}.card.buy{{border-color:#00ff88;box-shadow:0 0 10px #00ff8855}}.card.sell{{border-color:#ff4444}}.card.wait{{border-color:#444;opacity:.7}}.score{{float:right;background:#111;border:2px solid #ffcc00;border-radius:12px;padding:6px 12px;font-weight:bold;color:#ffcc00}}.btn{{width:100%;padding:8px;border-radius:8px;border:none;font-weight:bold;margin-top:6px}}.btn.g{{background:#00ff88}}.btn.r{{background:#ff3344;color:#fff}}.pos{{background:#111;border-radius:16px;padding:12px;margin-top:10px;border:1px solid #333}}.skel{{background:#222;height:80px;border-radius:10px;animation:p 1s infinite}}@keyframes p{{0%{{opacity:.5}}50%{{opacity:1}}}}</style></head><body>
<div class=top><div><b style=color:#00ff88>V1002.28 AUTO ON/OFF</b><br><small id=autoTxt>...</small></div><div style=display:flex;gap:8px;align-items:center><a href=/toggle_auto style=text-decoration:none><span id=autoBtn style=padding:8px 16px;border-radius:20px;font-weight:bold;cursor:pointer>...</span></a><span style=background:#ffeb3b;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold>${total:.0f}</span></div></div>
<div style=background:#151515;padding:10px;border-radius:12px;margin-bottom:8px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px><div><small>Saldo</small><br><b>${data['b']:.0f}</b></div><div><small>Total</small><br><b>${total:.0f}</b> <small style=color:#00ff88>+${data['gan_total']:.2f}</small></div><div><small>Hoy</small><br><b>${data['gan_hoy']:.2f}</b> <small>{data['trades_hoy']} trades</small></div></div>
<div class=grid id=g><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div><div class=card><div class=skel></div></div></div>
<div class=pos><b>Posiciones ({len(data['pos'])}/5) - Auto: <span id=autoPos>...</span> | Lógica: RSI&lt;32 + EMA20 + BTC&gt;-1.5%</b><br><br><div id=pos>{pos_html}</div><br><small>/auto on | /auto off | /status en Telegram | Botón arriba para ON/OFF</small></div>
<script>
async function L(){{
 try{{
  let st=await fetch('/api/status').then(r=>r.json());
  let btn=document.getElementById('autoBtn'); let txt=document.getElementById('autoTxt'); let posTxt=document.getElementById('autoPos');
  btn.innerText=st.auto_buy?'🤖 AUTO ON':'⏸️ AUTO OFF';
  btn.style.background=st.auto_buy?'#00ff88':'#ff4444';
  btn.style.color='#000';
  txt.innerText=st.auto_buy?'Comprando solo':'Solo manual';
  posTxt.innerText=st.auto_buy?'ON - Compra solo':'OFF - Solo manual';
  posTxt.style.color=st.auto_buy?'#00ff88':'#ff4444';
  let r=await fetch('/api/prices'); let d=await r.json(); let h='';
  for(let s in d){{
   let cls=d[s].action=='COMPRAR'?'buy':d[s].action=='VENDER'?'sell':'wait';
   let filtTxt=d[s].filt?'✅ Filtros OK':'⏸️ Esperando rebote';
   if(!st.auto_buy) filtTxt='⏸️ AUTO OFF';
   let btnHtml=d[s].action=='COMPRAR'?`<a href=/buy/${{s}}><button class=btn g>COMPRAR $50</button></a>`:`<a href=/chart/${{s}}><button class=btn style=background:#333;color:#fff>VER GRAFICA</button></a>`;
   h+=`<div class=card ${{cls}} onclick="location='/chart/${{s}}'"><b>${{s}} $${{d[s].price.toFixed(2)}}</b><span class=score>${{d[s].score}}/5</span><br><small>RSI ${{d[s].rsi}} | EMA $${{d[s].ema20}}<br>BTC ${{d[s].btc_t}}% | ${{filtTxt}}</small><br><span style=background:#ffcc00;color:#000;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold>${{d[s].action}}</span>${{btnHtml}}</div>`;
  }}
  document.getElementById('g').innerHTML=h;
 }}catch(e){{}}
}}
L(); setInterval(L,25000);
</script></body></html>"""

@app.route('/buy/<sym>')
def buy(sym):
    sym=sym.upper()
    if len(data['pos'])<5 and not any(p['sym']==sym for p in data['pos']):
        rsi,price,ema20,btc_t=AN(sym)
        data['pos'].append({"sym":sym,"monto":50,"gan":0,"precio_entry":price,"max_price":price})
        data['b']-=50; data['trades_hoy']+=1; save()
    return "<script>location='/dashboard'</script>"

@app.route('/sell/<sym>')
def sell(sym):
    sym=sym.upper()
    for p in data['pos'][:]:
        if p['sym']==sym:
            price=P(sym); gan=((price-p['precio_entry'])/p['precio_entry'])*100 if p.get('precio_entry') else 0
            data['b']+=50*(1+gan/100); data['gan_total']+=50*gan/100; data['gan_hoy']+=50*gan/100; data['pos'].remove(p); save()
    return "<script>location='/dashboard'</script>"

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    return f"""<html><head><meta name=viewport content="width=device-width,initial-scale=1"><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script><style>body{{background:#080808;color:#fff;margin:0}}#c{{width:100%;height:85vh}}.top{{padding:12px;background:#111;display:flex;justify-content:space-between}}</style></head><body><div class=top><b>{sym}/USDT - V28 AUTO</b><a href="/dashboard"><button style=background:#00ff88;padding:8px 16px;border-radius:8px;border:none;font-weight:bold>Volver</button></a></div><div id=c></div><script>fetch("https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1h&limit=150").then(r=>r.json()).then(k=>{{let d=k.map(x=>({{time:x[0]/1000,open:+x[1],high:+x[2],low:+x[3],close:+x[4]}}));let ch=LightweightCharts.createChart(document.getElementById('c'),{{layout:{{background:{{color:'#080808'}},textColor:'#ddd'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}}}}});let cs=ch.addCandlestickSeries();cs.setData(d);ch.timeScale().fitContent();}})</script></body></html>"""

@app.route('/webhook',methods=['POST'])
def wh():
    d=request.json
    if "message" in d:
        chat=d["message"]["chat"]["id"]; txt=d["message"].get("text","").upper().strip()
        if chat not in data["alert_users"]: data["alert_users"].append(chat)
        if txt in data["coins"]:
            if len(data["pos"])<5 and not any(p['sym']==txt for p in data["pos"]):
                rsi,price,ema20,btc_t=AN(txt)
                # compra manual IGNORA auto_buy
                data["pos"].append({"sym":txt,"monto":50,"gan":0,"precio_entry":price,"max_price":price}); data["b"]-=50; data["trades_hoy"]+=1; save()
                tg(chat,f"✅ {txt} MANUAL ${price:.2f} RSI {rsi:.1f}")
        if "/AUTO" in txt:
            if "ON" in txt: data['auto_buy']=True
            elif "OFF" in txt: data['auto_buy']=False
            else: data['auto_buy']=not data.get('auto_buy',True)
            save()
            tg(chat,f"{'✅ AUTO ON - Bot compra solo con 3 filtros' if data['auto_buy'] else '⏸️ AUTO OFF - Solo tú compras manual'}")
        if "/STATUS" in txt or "/ESTADO" in txt:
            total,val=totals()
            tg(chat,f"🤖 V28 STATUS\nAuto: {'ON ✅' if data.get('auto_buy',True) else 'OFF ⏸️'}\nSaldo ${data['b']:.2f} Total ${total:.2f}\nPos {len(data['pos'])}/5\nUsa /auto on / /auto off")
        if "/REPORTE" in txt:
            total,val=totals(); tg(chat,f"📊 V28\nSaldo ${data['b']:.2f} Total ${total:.2f}\nGan ${data['gan_total']:.2f}\nAuto {'ON' if data.get('auto_buy',True) else 'OFF'}")
        if "/START" in txt: tg(chat,"V1002.28 AUTO ON/OFF\nBoton en dashboard + /auto on / /auto off / /status\n/dashboard")
        save()
    return {"ok":True}

def auto_loop():
    time.sleep(5)
    while True:
        try:
            for sym in data["coins"]:
                rsi,price,ema20,btc_t=AN(sym)
                for p in data["pos"]:
                    if p['sym']==sym and price>p.get("max_price",0): p["max_price"]=price
                # AUTO COMPRA SOLO SI ESTA ACTIVADO
                if data.get('auto_buy',True) and rsi<32 and price>ema20 and btc_t>-1.5 and len(data["pos"])<5 and not any(p['sym']==sym for p in data["pos"]):
                    data["pos"].append({"sym":sym,"monto":50,"gan":0,"precio_entry":price,"max_price":price}); data["b"]-=50; data["trades_hoy"]+=1; save()
                    for u in data["alert_users"]: tg(u,f"🤖 AUTO {sym} RSI {rsi:.1f} ${price:.2f}")
                for p in data["pos"][:]:
                    if p['sym']==sym:
                        gan=((price-p["precio_entry"])/p["precio_entry"])*100 if p.get("precio_entry") else 0
                        max_gan=((p.get("max_price",price)-p["precio_entry"])/p["precio_entry"])*100
                        take=3.5 if rsi>60 else 2.5
                        trail=max_gan>4 and gan < max_gan-1
                        if gan>=take or gan<=-2 or rsi>=74 or trail:
                            data["b"]+=50*(1+gan/100); data["gan_total"]+=50*gan/100; data["gan_hoy"]+=50*gan/100; data["pos"].remove(p); save()
                            for u in data["alert_users"]: tg(u,f"💰 VENTA {sym} {gan:.2f}% max {max_gan:.2f}%")
            time.sleep(180)
        except: time.sleep(10)

threading.Thread(target=auto_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)),threaded=True)
