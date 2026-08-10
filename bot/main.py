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
 except:return 65000
async def G(i,t,m):
 async with httpx.AsyncClient() as c:
  d='https://'+os.getenv('RENDER_EXTERNAL_HOSTNAME','')+'/dashboard'
  k={'inline_keyboard':[[{'text':'DASHBOARD','url':d}],[{'text':'BUY','callback_data':'BUY_'+m},{'text':'SELL','callback_data':'SELL_'+m}]]}
  await c.post(B+'/sendMessage',json={'chat_id':i,'text':t,'reply_markup':k})
@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L();h=s['h'];hs=s.get('hs',[])[-20:];b=s['b'];tot=b;rows='';hrows=''
 for k2,v in h.items():
  try:pr=await P(k2);g=(pr/v['e']-1)*100;val=v['a']*pr;tot+=val
  except:g=0;pr=v['e'];val=v['a']*pr
  co='#00e676' if g>=0 else '#ff5252'
  rows+=f'<tr><td>{k2}</td><td>{v["a"]:.4f}</td><td>${v["e"]:.0f}</td><td>${pr:.0f}</td><td style=color:{co}>{g:+.1f}%</td><td>${val:.0f}</td></tr>'
 if not rows:rows='<tr><td colspan=6 style=text-align:center;opacity:.4>Sin posiciones</td></tr>'
 for hh in hs[::-1][:5]:
  hrows+=f'<tr><td>{hh["f"]}</td><td>{hh["t"]}</td><td>{hh["m"]}</td><td>${hh["pr"]:.0f}</td><td>{hh.get("g",0):+.1f}%</td></tr>'
 if not hrows:hrows='<tr><td colspan=5 style=text-align:center;opacity:.4>Sin historial</td></tr>'
 c1='#00e676' if tot>=1000 else '#ff5252'
 au='ON' if s.get('auto') else 'OFF'
 a=f"""
<html><head><meta name=viewport content='width=device-width,initial-scale=1'><script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#0a0e14;color:#c9d1d9;font-family:monospace;padding:12px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;margin-bottom:10px}}
th{{color:#8b949e;font-size:10px}} td{{padding:6px;border-bottom:1px solid #21262d;font-size:12px}}
.b{{background:#21262d;border:1px solid #30363d;color:#58a6ff;padding:5px 10px;border-radius:6px;margin-right:5px}}
</style></head><body>
<h2 style=color:#58a6ff>V912 FIX DEFINITIVO</h2>
<div style=display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px>
<div class=card>Saldo<br><b>${b:.0f}</b></div>
<div class=card>Total<br><b>${tot:.0f}</b></div>
<div class=card>PNL<br><b style=color:{c1}>${tot-1000:+.0f}</b></div>
<div class=card>Auto<br><b>{au}</b></div></div>
<div class=card><button class=b id=BTC onclick=sM('BTC')>BTC</button><button class=b id=ETH onclick=sM('ETH')>ETH</button><button class=b id=SOL onclick=sM('SOL')>SOL</button><button class=b id=XRP onclick=sM('XRP')>XRP</button><canvas id=c height=90></canvas></div>
<div class=card><table style=width:100%><tr><th>MON</th><th>CANT</th><th>ENT</th><th>ACT</th><th>PNL</th><th>VAL</th></tr>{rows}</table></div>
<div class=card><table style=width:100%><tr><th>FECHA</th><th>TIPO</th><th>MON</th><th>PRECIO</th><th>GAN</th></tr>{hrows}</table></div>
"""
 b2="""
<script>
let ch;
async function sM(m){
 document.querySelectorAll('.b').forEach(x=>x.style.background='#21262d');
 document.getElementById(m).style.background='#1f6feb';
 let d=await fetch('https://api.exchange.coinbase.com/products/'+m+'-USD/candles?granularity=3600').then(r=>r.json());
 let p=d.sort().slice(-30).map(x=>x[4]);
 if(ch) ch.destroy();
 ch=new Chart(document.getElementById('c'),{type:'line',data:{labels:p.map((_,i)=>i),datasets:[{data:p,borderColor:'#58a6ff',fill:true,tension:0.4,pointRadius:0}]},options:{plugins:{legend:{display:false}},scales:{x:{display:false}}}});
}
sM('BTC');
</script></body></html>
"""
 return HTMLResponse(a+b2)
@app.post('/webhook')
@app.post('/')
async def w(req:Request):
 q=await req.json()
 if 'callback_query' in q:
  o=q['callback_query'];i=o['message']['chat']['id'];a1,m=o['data'].split('_');s=L();pr=await P(m)
  if a1=='BUY':
   amt=(100*0.998)/pr
   if m in s['h']:
    old=s['h'][m];tot=old['a']+amt;avg=(old['a']*old['e']+amt*pr)/tot
    s['h'][m]={'a':tot,'e':avg}
   else:s['h'][m]={'a':amt,'e':pr}
   s['b']-=100;ft=datetime.now().strftime('%H:%M');s['hs'].append({'f':ft,'t':'COMPRA','m':m,'pr':pr,'g':0});S(s)
  else:
   if m in s['h']:
    val=s['h'][m]['a']*pr*0.998;g=(pr/s['h'][m]['e']-1)*100
    s['b']+=val;del s['h'][m];ft=datetime.now().strftime('%H:%M');s['hs'].append({'f':ft,'t':'VENTA','m':m,'pr':pr,'g':g});S(s)
  await G(i,a1+' '+m+' $'+str(int(pr)),m);return{'ok':1}
 msg=q.get('message',{});cid=msg.get('chat',{}).get('id')
 if not cid:return{'ok':1}
 t=(msg.get('text')or'').upper();s=L()
 if t=='AUTO ON':s['auto']=True;S(s);await G(cid,'AUTO ON -2% +2%','BTC');return{'ok':1}
 if t=='AUTO OFF':s['auto']=False;S(s);await G(cid,'AUTO OFF','BTC');return{'ok':1}
 if t in['BTC','ETH','SOL','XRP']:await G(cid,t+' $'+str(int(await P(t))),'BTC')
 else:await G(cid,'V912 FIX Saldo '+str(int(s['b']))+' - BTC ETH SOL XRP | AUTO ON/OFF','BTC')
 return{'ok':1}
@app.get('/')
def home():return{'V912 FIX':'/dashboard'}
