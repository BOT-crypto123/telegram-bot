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
 elif p>a and a>b and rr<42:senal='COMPRA'
 elif p<a and a<b and rr>62:senal='VENTA'
 else:senal='NADA'
 drop=(cs[-1]/cs[-10]-1)*100 if len(cs)>=10 else 0
 return {'p':p,'e9':a,'e21':b,'rsi':rr,'tend':tend,'senal':senal,'drop':drop,'cs':cs}
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
   # VENTA SOLO si es necesario
   if chg<=-2 or chg>=2.2 or an['senal']=='VENTA FUERTE':
    val=hold['a']*an['p']*0.998; s['b']+=val; del s['h'][sym]
    s['hs'].append({'f':datetime.now().strftime('%H:%M:%S'),'t':'SELL','m':sym,'pr':an['p'],'a':hold['a'],'g':chg}); S(s)
    await G(cid,f'🤖 AUTO VENTA {sym} {round(chg,1)}% RSI{int(an["rsi"])}',sym); s=L()
  # COMPRA SOLO si hay señal buena
  if s.get('auto') and sym not in s['h'] and s['b']>=100:
   debe_comprar = an['rsi']<35 or an['drop']<=-1.2
   if debe_comprar:
    pr=an['p']; amt=(100*0.998)/pr
    s['h'][sym]={'a':amt,'e':pr}; s['b']-=100
    s['hs'].append({'f':datetime.now().strftime('%H:%M:%S'),'t':'BUY','m':sym,'pr':pr,'a':amt,'g':0}); S(s)
    await G(cid,f'🤖 AUTO COMPRA {sym} RSI{int(an["rsi"])} {an["senal"]} Drop{round(an["drop"],1)}%',sym); s=L()

@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L(); tot=s['b']; prices={}
 for k2 in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(k2); prices[k2]=an['p'] if an else await P(k2)
 for k2,v in s['h'].items(): tot+=v['a']*prices.get(k2,v['e'])
 pnl=tot-1000; pnlp=(pnl/10)
 pos_rows=''
 for k2,v in s['h'].items():
  pr=prices.get(k2,v['e']); g=(pr/v['e']-1)*100; col='#00e676' if g>=0 else '#ff5252'
  pos_rows+=f"<tr onclick=\"sM('{k2}')\" style='cursor:pointer'><td>{k2}/USDT</td><td><span class='pill long'>{'LONG' if g>=0 else 'SHORT'}</span></td><td>{round(v['a'],5)}</td><td>${int(v['e'])}</td><td>${round(pr,2)}</td><td style='color:{col}'>{round(g,2)}%</td><td><span class='lev'>2x</span></td></tr>"
 if not pos_rows: pos_rows="<tr><td colspan=7 style='text-align:center;opacity:.4;padding:20px'>Sin posiciones</td></tr>"
 hist_rows=''
 for h in s.get('hs',[])[-8:][::-1]:
  cls='buy' if 'BUY' in h['t'] else 'sell'
  hist_rows+=f"<tr><td>{h['f']}</td><td><span class='pill {cls}'>{h['t']}</span></td><td>{h['m']}/USDT</td><td>${int(h['pr'])}</td><td>{round(h['a'],4)}</td><td><span class='pill {cls}'>Filled</span></td></tr>"
 if not hist_rows: hist_rows="<tr><td colspan=6 style='text-align:center;opacity:.4'>Sin historial</td></tr>"
 btc_an=await ANALIZA('BTC'); init_cs=btc_an['cs'][-40:] if btc_an else []
 html=f"""
<html><head><meta name=viewport content='width=device-width,initial-scale=1'><script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#0b0e14;color:#c9d1d9;font-family:monospace;margin:0}}.header{{display:flex;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #21262d}}.logo{{color:#2a7fff;font-weight:900;letter-spacing:2px}}.tag{{background:#13233a;color:#2a7fff;padding:4px 10px;border-radius:12px;font-size:10px;margin-left:8px}}
.cards{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;padding:12px}}.card{{background:#161a23;border:1px solid #21262d;border-radius:14px;padding:16px}}.card b{{font-size:28px;color:white}}
.grid{{display:grid;grid-template-columns:2fr 1fr;gap:12px;padding:0 12px}} @media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.chartbox{{background:#161a23;border:1px solid #21262d;border-radius:14px;padding:14px;margin-bottom:12px}} table{{width:100%;border-collapse:collapse}} th{{color:#8b949e;font-size:10px;padding:8px;text-align:left}} td{{padding:10px 8px;border-top:1px solid #21262d
