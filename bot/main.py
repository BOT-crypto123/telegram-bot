import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv('TELEGRAM_TOKEN','')
B='https://api.telegram.org/bot'+T
F='/tmp/b.json'
def L():
 try: return json.load(open(F))
 except: return {'b':1000,'h':{},'auto':False}
def S(s): json.dump(s,open(F,'w'))
async def P(m):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get('https://api.coinbase.com/v2/prices/'+m+'-USD/spot')
   return float(r.json()['data']['amount'])
 except: return 0
async def G(cid,txt):
 async with httpx.AsyncClient(timeout=10) as c:
  h=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
  link='https://'+h+'/dashboard' if h else 'https://example.com'
  kb={'inline_keyboard':[[{'text':'DASHBOARD','url':link}]]}
  try: await c.post(B+'/sendMessage',json={'chat_id':cid,'text':txt,'reply_markup':kb})
  except: pass

@app.get('/dashboard',response_class=HTMLResponse)
async def dash():
 s=L()
 btc=await P('BTC')
 eth=await P('ETH')
 sol=await P('SOL')
 xrp=await P('XRP')
 html=f"""
<html><head><meta name=viewport content=width=device-width,initial-scale=1>
<script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<style>
body{{background:#090c13;color:white;font-family:monospace;padding:12px}}
.card{{background:#12151e;border:1px solid #1e2532;border-radius:12px;padding:14px;margin:6px;display:inline-block;width:22%}}
</style></head><body>
<h2 style=color:#2a7fff>V928 BONITO 4 MONEDAS</h2>
<div>
<div class=card>Saldo<br><b>${int(s['b'])}</b></div>
<div class=card>BTC ${int(btc)}</div>
<div class=card>ETH ${int(eth)}</div>
<div class=card>SOL ${int(sol)}</div>
<div class=card>XRP ${int(xrp)}</div>
</div>
<canvas id=c></canvas><br>
<button onclick=sM('BTC')>BTC</button>
<button onclick=sM('ETH')>ETH</button>
<button onclick=sM('SOL')>SOL</button>
<button onclick=sM('XRP')>XRP</button>
<script>
let ch;
async function sM(m){{
let r=await fetch('https://api.exchange.coinbase.com/products/'+m+'-USD/candles?granularity=3600').then(r=>r.json());
let cs=r.sort((a,b)=>a[0]-b[0]).slice(-40).map(x=>x[4]);
if(ch)ch.destroy();
ch=new Chart(document.getElementById('c'),{{type:'line',data:{{labels:cs.map((_,i)=>i),datasets:[{{data:cs,borderColor:'#2a7fff'}}]}}}});
}}
sM('BTC');
</script>
</body></html>
"""
 return HTMLResponse(html)

@app.get('/')
@app.post('/')
@app.get('/webhook')
@app.post('/webhook')
async def wh(req:Request):
 try: q=await req.json()
 except: q={{}}
 msg=q.get('message',{{}});cid=msg.get('chat',{{}}).get('id')
 if not cid: return {{'ok':1}}
 t=(msg.get('text') or '').upper();s=L()
 if 'AUTO ON' in t:
  s['auto']=True;S(s);await G(cid,'AUTO ON');return {{'ok':1}}
 if 'AUTO OFF' in t:
  s['auto']=False;S(s);await G(cid,'AUTO OFF');return {{'ok':1}}
 await G(cid,f"Saldo ${int(s['b'])} 4 monedas OK");return {{'ok':1}}
