import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime

app=FastAPI()
T=os.getenv('TELEGRAM_TOKEN','')
B='https://api.telegram.org/bot'+T
F='/tmp/b.json'

def L():
 try:
  return json.load(open(F))
 except:
  return {'b':1000,'h':{},'hs':[],'auto':False}

def S(s):
 json.dump(s,open(F,'w'))

async def P(m):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
   return float(r.json()['data']['amount'])
 except:
  return 0

async def candles(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   u='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=3600'
   r=await c.get(u,headers={'User-Agent':'Mozilla'})
   d=r.json()
   if isinstance(d,list):
    d.sort()
    return d[-80:]
   return []
 except:
  return []

def ema(pr,n):
 if len(pr)<n:
  return []
 k=2/(n+1)
 s=sum(pr[:n])/n
 o=[s]
 for x in pr[n:]:
  o.append(x*k+o[-1]*(1-k))
 return o

def rsi(pr):
 if len(pr)<15:
  return 50
 g=0
 ll=0
 for i in range(1,15):
  d=pr[i]-pr[i-1]
  if d>0:
   g+=d
  else:
   ll-=d
 if ll==0:
  return 80
 if g==0:
  return 20
 return 100-100/(1+g/ll)

async def ANALIZA(sym):
 cl=await candles(sym)
 if not cl:
  return None
 cs=[x[4] for x in cl]
 e9=ema(cs,9)
 e21=ema(cs,21)
 if not e9 or not e21:
  return None
 rr=rsi(cs)
 p=cs[-1]
 a=e9[-1]
 b=e21[-1]
 tend='LATERAL'
 if p>a and a>b:
  tend='SUBE'
 if p<a and a<b:
  tend='BAJA'
 senal='NADA'
 if rr<30:
  senal='COMPRA FUERTE'
 elif rr>70:
  senal='VENTA FUERTE'
 elif p>a and rr<42:
  senal='COMPRA'
 elif p<a and rr>62:
  senal='VENTA'
 drop=0
 if len(cs)>=10:
  drop=(cs[-1]/cs[-10]-1)*100
 return {'p':p,'rsi':rr,'tend':tend,'senal':senal,'drop':drop}

async def G(cid,txt,sym):
 async with httpx.AsyncClient(timeout=10) as c:
  host=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
  link='https://'+host+'/dashboard' if host else 'https://example.com'
  kb={'inline_keyboard':[[{'text':'DASHBOARD V928','url':link}], [{'text':'BUY $100','callback_data':'BUY_'+sym},{'text':'SELL','callback_data':'SELL_'+sym}], [{'text':'AUTO ON','callback_data':'AUTO_ON'},{'text':'AUTO OFF','callback_data':'AUTO_OFF'}]]}
  try:
   await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb})
  except:
   pass

async def AUTO_BRAIN(cid):
 s=L()
 for sym in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(sym)
  if not an:
   continue
  if sym in s['h']:
   chg=(an['p']/s['h'][sym]['e']-1)*100
   if chg>=2.5 or chg<=-3 or an['rsi']>=72:
    s['b']+=s['h'][sym]['a']*an['p']*0.998
    del s['h'][sym]
    S(s)
    await G(cid,f'AUTO VENTA {sym} {round(chg,1)}% RSI{int(an["rsi"])}',sym)
    s=L()
  if s.get('auto') and sym not in s['h'] and s['b']>=100:
   if an['rsi']<32:
    pr=an['p']
    amt=(100*0.998)/pr
    s['h'][sym]={'a':amt,'e':pr}
    s['b']-=100
    ft=datetime.now().strftime('%H:%M:%S')
    s['hs'].append({'f':ft,'t':'BUY','m':sym,'pr':pr,'a':amt})
    S(s)
    await G(cid,f'AUTO COMPRA {sym} RSI{int(an["rsi"])} {an["senal"]}',sym)
    s=L()

@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L()
 prices={}
 for k in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(k)
  prices[k]=an['p'] if an else await P(k)
 tot=s['b']
 for k,v in s['h'].items():
  tot+=v['a']*prices.get(k,v['e'])
 pnl=tot-1000
 auto_txt='ON' if s.get('auto') else 'OFF'
 pos=''
 for k,v in s['h'].items():
  pr=prices.get(k,v['e'])
  g=(pr/v['e']-1)*100
  pos+=f'<tr><td>{k}/USDT</td><td>{"LONG" if g>=0 else "SHORT"}</td><td>{round(v["a"],4)}</td><td>${int(v["e"])}</td><td>${int(pr)}</td><td>{round(g,2)}%</td><td>2x</td></tr>'
 if pos=='':
  pos='<tr><td colspan=7 style="text-align:center;opacity:.3;padding:20px">Sin posiciones</td></tr>'
 hist=''
 for h in s.get('hs',[])[-8:][::-1]:
  hist+=f'<tr><td>{h["f"]}</td><td>{h["t"]}</td><td>{h["m"]}/USDT</td><td>${int(h["pr"])}</td><td>{round(h["a"],4)}</td><td>Filled</td></tr>'
 if hist=='':
  hist='<tr><td colspan=6 style="text-align:center;opacity:.3">Sin historial</td></tr>'
 html="""
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#090c13;color:#c9d1d9;font-family:monospace;margin:0}
.header{display:flex;justify-content:space-between;padding:16px;border-bottom:1px solid #21262d}
.logo{color:#2a7fff;font-weight:900;font-size:20px}
.cards{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;padding:12px}
.card{background:#12151e;border:1px solid #1e2532;border-radius:14px;padding:16px}
.card b{font-size:28px;color:white}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:12px;padding:0 12px}
.box{background:#12151e;border:1px solid #1e2532;border-radius:14px;padding:14px}
table{width:100%;border-collapse:collapse}th{color:#6e7681;font-size:10px;padding:8px}td{padding:10px;border-top:1px solid #1b2330;font-size:12px}
.btn{background:#1e252f;color:#58a6ff;padding:8px 14px;border-radius:8px;margin:4px;border:1px solid #2a3446}
.btn.active{background:#2a7fff;color:white}
@media(max-width:900px){.grid{grid-template-columns:1fr}.cards{grid-template-columns:1fr}}
</style></head><body>
"""
 html+=f'<div class="header"><div><span class="logo">V869 WALL ST</span> PRO TERMINAL</div><div>AUTO {auto_txt}</div></div>'
 html+=f'<div class="cards"><div class="card">Saldo<br><b>${int(s["b"])}</b></div><div class="card">Total<br><b>${int(tot)}</b></div><div class="card">PNL<br><b>${int(pnl)}</b></div></div>'
 html+=f'<div class="grid"><div class="box"><b>BTC 40H</b> <span id="prc"></span><canvas id="c" height="200"></canvas><br><button class="btn active" id="BTC" onclick="sM(&quot;BTC&quot;)">BTC</button><button class="btn" id="ETH" onclick="sM(&quot;ETH&quot;)">ETH</button><button class="btn" id="SOL" onclick="sM(&quot;SOL&quot;)">SOL</button><button class="btn" id="XRP" onclick="sM(&quot;XRP&quot;)">XRP</button></div><div class="box"><b style="color:#2a7fff">HISTORY</b><table><tr><th>TIME</th><th>TYPE</th><th>SYMBOL</th><th>PRICE</th><th>AMOUNT</th><th>STATUS</th></tr>{hist}</table></div></div>'
 html+=f'<div style="padding:12px"><div class="box"><b style="color:#2a7fff">POSITIONS</b><table><tr><th>SYMBOL</th><th>SIDE</th><th>SIZE</th><th>ENTRY</th><th>MARK</th><th>PNL</th><th>LEV</th></tr>{pos}</table></div></div>'
 html+='<script>let ch;async function sM(m){document.querySelectorAll(".btn").forEach(x=>x.classList.remove("active"));let el=document.getElementById(m);if(el)el.classList.add("active");let r=await fetch("https://api.exchange.coinbase.com/products/"+m+"-USD/candles?granularity=3600").then(r=>r.json());let cl=r.sort((a,b)=>a[0]-b[0]).slice(-50);let cs=cl.map(x=>x[4]);if(ch)ch.destroy();ch=new Chart(document.getElementById("c"),{type:"line",data:{labels:cs.map((_,i)=>i),datasets:[{data:cs,borderColor:"#2a7fff",backgroundColor:"rgba(42,127,255,0.2)",fill:true,tension:0.35,pointRadius:0}]},options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{grid:{color:"#1e252f"}}}}});document.getElementById("prc").innerText="$"+Math.round(cs[cs.length-1])}sM("BTC");</script></body></html>'
 return HTMLResponse(html)

@app.get('/')
@app.post('/')
@app.get('/webhook')
@app.post('/webhook')
async def webhook(req:Request):
 try:
  q=await req.json()
 except:
  q={}
 if 'callback_query' in q:
  o=q['callback_query']
  cid=o['message']['chat']['id']
  data=o['data']
  s=L()
  if data=='AUTO_ON':
   s['auto']=True
   S(s)
   await G(cid,'AUTO ON V928 BONITO RSI<32','BTC')
   await AUTO_BRAIN(cid)
   return {'ok':1}
  if data=='AUTO_OFF':
   s['auto']=False
   S(s)
   await G(cid,'AUTO OFF','BTC')
   return {'ok':1}
  a1,m=data.split('_')
  pr=await P(m)
  if a1=='BUY' and s['b']>=100:
   s['h'][m]={'a':(100*0.998)/pr,'e':pr}
   s['b']-=100
   S(s)
  elif a1=='SELL' and m in s['h']:
   s['b']+=s['h'][m]['a']*pr*0.998
   del s['h'][m]
   S(s)
  await G(cid,f'{a1} {m} ${int(pr)}','BTC')
  return {'ok':1}
 msg=q.get('message',{})
 cid=msg.get('chat',{}).get('id')
 if not cid:
  return {'ok':1}
 t=(msg.get('text') or '').upper()
 s=L()
 if 'AUTO ON' in t:
  s['auto']=True
  S(s)
  await G(cid,'AUTO ON V928 BONITO RSI<32','BTC')
  await AUTO_BRAIN(cid)
  return {'ok':1}
 if 'AUTO OFF' in t:
  s['auto']=False
  S(s)
  await G(cid,'AUTO OFF','BTC')
  return {'ok':1}
 if t in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(t)
  txt=f"{t} ${int(an['p'])} RSI{int(an['rsi'])} {an['senal']}" if an else f"{t} cargando"
  await G(cid,txt,t)
  return {'ok':1}
 await G(cid,f'V928 Saldo ${int(s["b"])}','BTC')
 return {'ok':1}
