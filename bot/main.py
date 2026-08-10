import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
T=os.getenv('TELEGRAM_TOKEN','')
B='https://api.telegram.org/bot'+T
F='/tmp/b.json'
def L():
 try:return json.load(open(F))
 except:return{'b':1000,'h':{},'hs':[],'auto':True}
def S(s):json.dump(s,open(F,'w'))
async def P(m):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f'https://api.coinbase.com/v2/prices/{m}-USD/spot')
   return float(r.json()['data']['amount'])
 except:return 0
async def candles(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f'https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=3600',headers={'User-Agent':'Mozilla'})
   d=r.json()
   return sorted(d)[-80:] if isinstance(d,list) else []
 except:return []
def ema(pr,n):
 if len(pr)<n:return []
 k=2/(n+1); mm=sum(pr[:n])/n; o=[mm]
 for x in pr[n:]:o.append(x*k+o[-1]*(1-k))
 return o
def rsi(pr):
 if len(pr)<15:return 50
 g=l=0
 for i in range(1,15):
  d=pr[i]-pr[i-1]
  if d>0:g+=d
  else:l+=-d
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
async def ANALIZA(sym):
 cl=await candles(sym)
 if not cl:return None
 cs=[c[4] for c in cl]
 e9=ema(cs,9); e21=ema(cs,21); rr=rsi(cs)
 if not e9 or not e21:return None
 p=cs[-1]; a=e9[-1]; b=e21[-1]
 tend='SUBE' if p>a and a>b else 'BAJA' if p<a and a<b else 'LATERAL'
 if rr<30:senal='COMPRA FUERTE'
 elif rr>70:senal='VENTA FUERTE'
 elif p>a and a>b and rr<40:senal='COMPRA'
 elif p<a and a<b and rr>60:senal='VENTA'
 else:senal='NADA'
 drop=(cs[-1]/cs[-10]-1)*100 if len(cs)>=10 else 0
 return {'p':p,'e9':a,'e21':b,'rsi':rr,'tend':tend,'senal':senal,'drop':drop,'cs':cs,'cl':cl}
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  host=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
  d=f'https://{host}/dashboard'
  k={'inline_keyboard':[[{'text':'📊 DASHBOARD V869','url':d}],[{'text':'BUY $100','callback_data':f'BUY_{m}'},{'text':'SELL','callback_data':f'SELL_{m}'}],[{'text':'🟢 AUTO ON','callback_data':'AUTO_ON'},{'text':'🔴 AUTO OFF','callback_data':'AUTO_OFF'}]]}
  await c.post(f'{B}/sendMessage',json={'chat_id':i,'text':t,'reply_markup':k})
async def AUTO_BRAIN(cid):
 s=L()
 for sym in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(sym)
  if not an:continue
  if sym in s['h']:
   hold=s['h'][sym]; chg=(an['p']/hold['e']-1)*100
   if chg<=-2 or chg>=2.2 or an['senal']=='VENTA FUERTE':
    val=hold['a']*an['p']*0.998; s['b']+=val; del s['h'][sym]
    s['hs'].append({'f':datetime.now().strftime('%H:%M:%S'),'t':'SELL','m':sym,'pr':an['p'],'a':hold['a'],'g':chg}); S(s)
    await G(cid,f'🤖 AUTO VENTA {sym} {round(chg,1)}% RSI{int(an["rsi"])} Gan ${round(chg,2)}',sym); s=L()
