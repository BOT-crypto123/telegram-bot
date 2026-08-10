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
 except:return{'b':1000,'h':{},'hs':[],'auto':False}
def S(s):json.dump(s,open(F,'w'))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
   return float(r.json()['data']['amount'])
 except:return 0
async def candles(sym):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get('https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=3600',headers={'User-Agent':'M'})
   d=r.json(); return sorted(d)[-60:] if isinstance(d,list) else []
 except:return []
def ema(pr,n):
 if len(pr)<n:return []
 k=2/(n+1);m=sum(pr[:n])/n;o=[m]
 for x in pr[n:]:o.append(x*k+o[-1]*(1-k))
 return o
def rsi(pr):
 if len(pr)<15:return 50
 g=l=0
 for i in range(1,15):
  d=pr[i]-pr[i-1]; g+=d if d>0 else 0; l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
async def ANALIZA(sym):
 cl=await candles(sym)
 if not cl:return None
 cs=[c[4] for c in cl]; e9=ema(cs,9); e21=ema(cs,21); rr=rsi(cs)
 if not e9 or not e21:return None
 p=cs[-1]; a=e9[-1]; b=e21[-1]
 tend='SUBE' if p>a and a>b else 'BAJA' if p<a and a<b else 'LATERAL'
 senal='NADA'; conf=50
 if rr<30: senal='COMPRA FUERTE'; conf=92
 elif rr>70: senal='VENTA FUERTE'; conf=91
 elif p>a and a>b and rr<35: senal='COMPRA'; conf=68
 elif p<a and a<b and rr>65: senal='VENTA'; conf=66
 drop=(cs[-1]/cs[-10]-1)*100 if len(cs)>=10 else 0
 return {'p':p,'e9':a,'e21':b,'rsi':rr,'tend':tend,'senal':senal,'conf':conf,'drop':drop,'cs':cs,'cl':cl}
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  d='https://'+os.getenv('RENDER_EXTERNAL_HOSTNAME','')+'/dashboard'
  k={'inline_keyboard':[[{'text':'📊 DASHBOARD PRO','url':d}],[{'text':'BUY $100','callback_data':'BUY_'+m},{'text':'SELL','callback_data':'SELL_'+m}]]}
  await c.post(B+'/sendMessage',json={'chat_id':i,'text':t,'reply_markup':k})
async def AUTO_BRAIN(cid):
 s=L()
 for sym in ['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(sym)
  if not an:continue
  if sym in s['h']:
   hold=s['h'][sym]; chg=(an['p']/hold['e']-1)*100
   if chg<=-2 or chg>=2.2 or an['senal']=='VENTA FUERTE':
    val=hold['a']*an['p']*0.998; s['b']+=val; del s['h'][sym]
    ft=datetime.now().strftime('%H:%M'); s['hs'].append({'f':ft,'t':'AUTO VENTA','m':sym,'pr':an['p'],'g':chg});S(s)
    await G(cid,f"🤖 AUTO VENTA {sym} {chg:+.1f}% RSI {int(an['rsi'])} {an['senal']}",sym); s=L()
  if s.get('auto') and sym not in s['h'] and s['b']>=100:
   if an['senal']=='COMPRA FUERTE' or an['drop']<=-1.0 or (an['senal']=='COMPRA' and an['rsi']<35):
    pr=an['p']; amt=(100*0.998)/pr
    if sym in s['h']:old=s['h'][sym];tot=old['a']+amt;avg=(old['a']*old['e']+amt*pr)/tot;s['h'][sym]={'a':tot,'e':avg}
    else:s['h'][sym]={'a':amt,'e':pr}
    s['b']-=100; ft=datetime.now().strftime('%H:%M'); s['hs'].append({'f':ft,'t':'AUTO COMPRA','m':sym,'pr':pr,'g':0});S(s)
    await G(cid,f"🤖 AUTO COMPRA {sym} RSI {int(an['rsi'])} {an['senal']} Drop {an['drop']:+.1f}%",sym); s=L()

@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L(); b=s['b']; import json as js
 holdings=js.dumps(s['h'])
 hs=s.get('hs',[])[-20:]; tot=b; rows=''; hrows=''
 for k2,v in s['h'].items():
  an=await ANALIZA(k2)
  try:pr=an['p'] if an else await P(k2); g=(pr/v['e']-1)*100; val=v['a']*pr; tot+=val
  except:g=0;pr=v['e'];val=v['a']*pr
  co='#00e676' if g>=0 else '#ff5252'; rr=int(an['rsi']) if an else 50
  rows+=f'<tr><td>{k2} RSI{rr}</td><td>{v["a"]:.4f}</td><td>${v["e"]:.0f}</td><td>${pr:.0f}</td><td style=color:{co}>{g:+.1f}%</td><td>${val:.0f}</td></tr>'
 if not rows:rows='<tr><td colspan=6 style=text-align:center;opacity:.4>Sin posiciones - Pon AUTO ON</td></tr>'
 for hh in hs[::-1][:8]:
  hrows+=f'<tr><td>{hh["f"]}</td><td>{hh["t"]}</td><td>{hh["m"]}</td><td>${hh["pr"]:.0f}</td><td>{hh.get("g",0):+.1f}%</td></tr>'
 if not hrows:hrows='<tr><td colspan=5 style=text-align:center;opacity:.4>Sin historial</td></tr>'
 c1='#00e676' if tot>=1000 else '#ff5252'; au='🟢 AUTO ON' if s.get('auto') else '🔴 AUTO OFF'
 html=f"""
<html><head><meta name=viewport content='width=device-width,initial-scale=1'><script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#0a0e14;color:#c9d1d9;font-family:monospace;padding:12px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;margin-bottom:10px}}
th{{color:#8b949e;font-size:10px}} td{{padding:6px;border-bottom:1px solid #21262d;font-size:12px}}
.b{{background:#21262d;border:1px solid #30363d;color:#58a6ff;padding:6px 12px;border-radius:6px;margin:3px;cursor:pointer}}
.b.active{{background:#1f6feb;color:white}}
#info{{font-size:11px;color:#8b949e;margin:6px 0}}
</style></head><body>
<h2 style=color:#58a6ff>V916 WALL ST PRO GRAF</h2>
<div style=display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px>
<div class=card>Saldo<br><b>${b:.0f}</b></div><div class=card>Total<br><b>${tot:.0f}</b></div><div class=card>PNL<br><b style=color:{c1}>${tot-1000:+.0f}</b></div><div class=card>{au}<br><span style=font-size:10px>RSI+EMA+TP/SL+DROP</span></div></div>
<div class=card>
<div><button class=b id=BTC onclick=sM('BTC')>BTC</button><button class=b id=ETH onclick=sM('ETH')>ETH</button><button class=b id=SOL onclick=sM('SOL')>SOL</button><button class=b id=XRP onclick=sM('XRP')>XRP</button></div>
<div id=info>Cargando...</div>
<canvas id=c height=130></canvas>
<div style=font-size:10px;margin-top:6px><span style=color:#00bfff>— EMA9</span> <span style=color:#ffcc00>— EMA21</span> <span style=color:#ffcc00>--- Entrada</span> <span style=color:#00e676>▲ Vela verde</span> <span style=color:#ff5252>▼ Vela roja</span></div>
</div>
<div class=card><table style=width:100%><tr><th>MON RSI</th><th>CANT</th><th>ENT</th><th>ACT</th><th>PNL</th><th>VAL</th></tr>{rows}</table></div>
<div class=card><table style=width:100%><tr><th>FECHA</th><th>TIPO</th><th>MON</th><th>PRECIO</th><th>GAN</th></tr>{hrows}</table></div>
<script>
let ch; let holdings={holdings};
async function sM(m){{
 document.querySelectorAll('.b').forEach(x=>x.classList.remove('active'));
 document.getElementById(m).classList.add('active');
 let r=await fetch('https://api.exchange.coinbase.com/products/'+m+'-USD/candles?granularity=3600').then(r=>r.json());
 let cl=r.sort((a,b)=>a[0]-b[0]).slice(-50);
 let closes=cl.map(x=>x[4]);
 let e9=ema(closes,9); let e21=ema(closes,21);
 let rsiVal=rsi(closes);
 let last=closes[closes.length-1];
 let trend = (last>e9[e9.length-1] && e9[e9.length-1]>e21[e21.length-1])? 'SUBE' : (last<e9[e9.length-1] && e9[e9.length-1]<e21[e21.length-1])? 'BAJA' : 'LATERAL';
 let senal = rsiVal<30? 'COMPRA FUERTE' : rsiVal>70? 'VENTA FUERTE' : trend=='SUBE' && rsiVal<35? 'COMPRA' : trend=='BAJA' && rsiVal>65? 'VENTA' : 'NADA';
 document.getElementById('info').innerHTML = m+' $'+Math.round(last)+' | RSI '+Math.round(rsiVal)+' | '+trend+' | '+senal+' | E9 '+Math.round(e9[e9.length-1])+' E21 '+Math.round(e21[e21.length-1]);
 if(ch) ch.destroy();
 let entry = holdings[m]? holdings[m].e : null;
 let entryLine = entry? Array(closes.length).fill(entry) : [];
 ch=new Chart(document.getElementById('c'),{{
  type:'line',
  data:{{
   labels:closes.map((_,i)=>i),
   datasets:[
    {{data:closes,borderColor:'#c9d1d9',backgroundColor:'rgba(201,209,217,0.05)',fill:true,tension:0.1,pointRadius:0,borderWidth:1.5}},
    {{data:pad(e9,closes.length),borderColor:'#00bfff',tension:0.4,pointRadius:0,borderWidth:2}},
    {{data:pad(e21,closes.length),borderColor:'#ffcc00',tension:0.4,pointRadius:0,borderWidth:2}},
    {{data:entryLine,borderColor:'#ffcc00',borderDash:[6,4],pointRadius:0,borderWidth:1.5}}
   ]
  }},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{x:{{display:false}},y:{{grid:{{color:'#21262d'}}}}}}}
 }});
}}
function ema(pr,n){{ if(pr.length<n) return []; let k=2/(n+1); let m=pr.slice(0,n).reduce((a,b)=>a+b,0)/n; let o=[m]; for(let i=n;i<pr.length;i++) o.push(pr[i]*k+o[o.length-1]*(1-k)); return o; }}
function rsi(pr){{ if(pr.length<15) return 50; let g=0,l=0; for(let i=1;i<15;i++){{ let d=pr[i]-pr[i-1]; if(d>0) g+=d; else l+=-d; }} return l==0?88:g==0?12:100-100/(1+g/l); }}
function pad(arr,total){{ let p=Array(total-arr.length).fill(null); return p.concat(arr); }}
sM('BTC');
</script></body></html>
"""
 return HTMLResponse(html)

@app.post('/webhook')
@app.post('/')
async def w(req:Request):
 q=await req.json()
 if 'callback_query' in q:
  o=q['callback_query'];i=o['message']['chat']['id'];a1,m=o['data'].split('_');s=L();pr=await P(m)
  if not pr:
   an=await ANALIZA(m); pr=an['p'] if an else 0
  if a1=='BUY' and s['b']>=100:
   amt=(100*0.998)/pr
   if m in s['h']:old=s['h'][m];tot=old['a']+amt;avg=(old['a']*old['e']+amt*pr)/tot;s['h'][m]={'a':tot,'e':avg}
   else:s['h'][m]={'a':amt,'e':pr}
   s['b']-=100;ft=datetime.now().strftime('%H:%M');s['hs'].append({'f':ft,'t':'COMPRA','m':m,'pr':pr,'g':0});S(s)
  elif a1=='SELL' and m in s['h']:
   val=s['h'][m]['a']*pr*0.998;g=(pr/s['h'][m]['e']-1)*100;s['b']+=val;del s['h'][m];ft=datetime.now().strftime('%H:%M');s['hs'].append({'f':ft,'t':'VENTA','m':m,'pr':pr,'g':g});S(s)
  await G(i,f'{a1} {m} ${pr:.0f}',m);await AUTO_BRAIN(i);return{'ok':1}
 msg=q.get('message',{});cid=msg.get('chat',{}).get('id')
 if not cid:return{'ok':1}
 t=(msg.get('text')or'').upper();s=L()
 if 'AUTO ON' in t:s['auto']=True;S(s);await G(cid,'🟢 AUTO ON\nRSI<30 COMPRA FUERTE | RSI>70 VENTA FUERTE\nEMA9/21 | Caida -1% | TP +2.2% SL -2%','BTC');await AUTO_BRAIN(cid);return{'ok':1}
 if 'AUTO OFF' in t:s['auto']=False;S(s);await G(cid,'🔴 AUTO OFF - Solo alertas 🔔 OPORTUNIDAD','BTC');return{'ok':1}
 if t=='PORTAFOLIO':
  tot=s['b'];txt='📊 PORTAFOLIO V916 GRAF\n'
  for kk,vv in s['h'].items():
   an=await ANALIZA(kk);pr=an['p'] if an else await P(kk);val=vv['a']*pr;tot+=val;g=(pr/vv['e']-1)*100;txt+=f"{kk} RSI{int(an['rsi']) if an else 50} {g:+.1f}% ${val:.0f}\n"
  txt+=f"\nSaldo ${s['b']:.0f} Total ${tot:.0f} PNL ${tot-1000:+.0f}"
  await G(cid,txt,'BTC');await AUTO_BRAIN(cid);return{'ok':1}
 if t in['BTC','ETH','SOL','XRP']:
  an=await ANALIZA(t);await G(cid,f"{t} ${an['p']:.0f} RSI {int(an['rsi'])} {an['tend']} {an['senal']} {an['conf']}% E9 {an['e9']:.0f} E21 {an['e21']:.0f} Drop {an['drop']:+.1f}%",'BTC');await AUTO_BRAIN(cid);return{'ok':1}
 await G(cid,f"V916 PRO Saldo ${int(s['b'])} | GRAF + EMA + RSI | AUTO ON/OFF",'BTC');await AUTO_BRAIN(cid);return{'ok':1}
@app.get('/')
def home():return{'V916 GRAF PRO':'/dashboard'}
