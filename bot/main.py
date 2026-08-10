# V927 - FIX AUTO MALO
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
   url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=3600'
   r=await c.get(url,headers={'User-Agent':'Mozilla'})
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
 elif p<a and a<b:
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
  kb={'inline_keyboard':[[{'text':'DASHBOARD V927','url':link}],[{'text':'BUY $100','callback_data':'BUY_'+sym},{'text':'SELL','callback_data':'SELL_'+sym}],[{'text':'AUTO ON','callback_data':'AUTO_ON'},{'text':'AUTO OFF','callback_data':'AUTO_OFF'}]]}
  try:
   await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb})
  except:
   pass
async def AUTO_BRAIN(cid):
 s=L()
 # SOLO VENDE SI ESTA MUY ALTO
 for sym in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(sym)
  if not an:
   continue
  if sym in s['h']:
   hold=s['h'][sym]
   chg=(an['p']/hold['e']-1)*100
   # Vende solo si gana +2.5% o pierde -3% o RSI muy alto
   if chg>=2.5 or chg<=-3 or an['rsi']>=72:
    val=hold['a']*an['p']*0.998
    s['b']+=val
    del s['h'][sym]
    ft=datetime.now().strftime('%H:%M:%S')
    s['hs'].append({'f':ft,'t':'SELL','m':sym,'pr':an['p'],'a':hold['a'],'g':chg})
    S(s)
    await G(cid,f'AUTO VENTA {sym} {round(chg,1)}% RSI{int(an["rsi"])}',sym)
    s=L()
  # COMPRA SOLO SI RSI < 32 - FIX MALO
  if s.get('auto') and sym not in s['h'] and s['b']>=100:
   if an['rsi']<32 and an['senal']!='VENTA FUERTE':
    pr=an['p']
    amt=(100*0.998)/pr
    s['h'][sym]={'a':amt,'e':pr}
    s['b']-=100
    ft=datetime.now().strftime('%H:%M:%S')
    s['hs'].append({'f':ft,'t':'BUY','m':sym,'pr':pr,'a':amt,'g':0})
    S(s)
    await G(cid,f'AUTO COMPRA {sym} RSI{int(an["rsi"])} {an["senal"]}',sym)
    s=L()

@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L()
 prices={}
 for k in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(k)
  if an:
   prices[k]=an['p']
  else:
   prices[k]=await P(k)
 tot=s['b']
 for k,v in s['h'].items():
  tot+=v['a']*prices.get(k,v['e'])
 pnl=tot-1000
 auto_txt='ON' if s.get('auto') else 'OFF'
 return HTMLResponse(f"<html><body style='background:#0b0e14;color:white;font-family:monospace;padding:20px'><h2>V927 FIX - AUTO {auto_txt}</h2><div>Saldo ${int(s['b'])} Total ${int(tot)} PNL ${int(pnl)}</div><script>window.location.reload()</script></body></html>")

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
   await G(cid,'AUTO ON V927 - Solo RSI<32','BTC')
   await AUTO_BRAIN(cid)
   return {'ok':1}
  if data=='AUTO_OFF':
   s['auto']=False
   S(s)
   await G(cid,'AUTO OFF','BTC')
   return {'ok':1}
  parts=data.split('_')
  a1=parts[0]
  m=parts[1]
  pr=await P(m)
  if a1=='BUY' and s['b']>=100:
   amt=(100*0.998)/pr
   s['h'][m]={'a':amt,'e':pr}
   s['b']-=100
   ft=datetime.now().strftime('%H:%M:%S')
   s['hs'].append({'f':ft,'t':'BUY','m':m,'pr':pr,'a':amt,'g':0})
   S(s)
  elif a1=='SELL' and m in s['h']:
   val=s['h'][m]['a']*pr*0.998
   s['b']+=val
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
  await G(cid,'AUTO ON V927 - Ahora solo compra RSI<32, ya no compra en 68','BTC')
  await AUTO_BRAIN(cid)
  return {'ok':1}
 if 'AUTO OFF' in t:
  s['auto']=False
  S(s)
  await G(cid,'AUTO OFF - Ya no comprara solo','BTC')
  return {'ok':1}
 if t in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(t)
  if an:
   txt=f"{t} ${int(an['p'])} RSI{int(an['rsi'])} {an['tend']} {an['senal']} Drop{round(an['drop'],1)}%"
  else:
   pr=await P(t)
   txt=f"{t} ${int(pr)} cargando RSI..."
  await G(cid,txt,t)
  return {'ok':1}
 if t=='PORTAFOLIO':
  tot=s['b']
  for k2,v in s['h'].items():
   pr=await P(k2)
   tot+=v['a']*pr
  await G(cid,f"V927 Saldo ${int(s['b'])} Total ${int(tot)}",'BTC')
  return {'ok':1}
 await G(cid,f"V927 Saldo ${int(s['b'])} Auto {'ON' if s.get('auto') else 'OFF'} - Escribe BTC",'BTC')
 return {'ok':1}
