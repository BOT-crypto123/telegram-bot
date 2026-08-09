import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app=FastAPI()
TOKEN=os.getenv("TELEGRAM_TOKEN","")
BASE=f"https://api.telegram.org/bot{TOKEN}"
FILE="/tmp/b.json"
CAP=os.getenv("RENDER_EXTERNAL_HOSTNAME","")
DASH=f"https://{CAP}/dashboard"

def load():
 try:return json.load(open(FILE))
 except:return{"bal":1000.0,"holds":{},"hist":[]}
def save(s):json.dump(s,open(FILE,"w"))

async def price(sym):
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:return 65000.0

async def candles():
 try:
  async with httpx.AsyncClient(timeout=10) as c:
   r=await c.get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600")
   d=sorted(r.json())[-40:]
   return [x[4] for x in d]
 except:return [65000,65200,65100,65300,65250]

async def send(cid,txt,mon="BTC",buy=False):
 async with httpx.AsyncClient(timeout=10) as c:
  # GRAF YA NO ES URL, ES CALLBACK
  if buy:
   kb={"inline_keyboard":[[{"text":"📊 GRAF","callback_data":"GRAF_"+mon},{"text":"💻 DASHBOARD","url":DASH}],[{"text":"✅ COMPRAR","callback_data":"BUY_"+mon},{"text":"❌ VENDER","callback_data":"SELL_"+mon}]]}
  else:
   kb={"inline_keyboard":[[{"text":"📊 GRAF","callback_data":"GRAF_"+mon},{"text":"💻 DASHBOARD","url":DASH}]]}
  await c.post(BASE+"/sendMessage",json={"chat_id":cid,"text":txt,"reply_markup":kb})

@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=load()
 bal=s.get('bal',1000.0)
 holds=s.get('holds',{})
 hist=s.get('hist',[])
 pr=await candles()
 rows="";tot=bal
 for k,v in holds.items():
  p=await price(k)
  amt=v.get('a',0);ent=v.get('e',0);val=amt*p;tot+=val
  gn=(p/ent-1)*100 if ent else 0
  col="#00d395" if gn>=0 else "#ff4d4d"
  rows+=f"<tr><td><b>{k}</b></td><td>{amt:.5f}</td><td>${ent:.2f}</td><td>${p:.2f}</td><td style='color:{col};font-weight:bold'>{gn:.2f}%</td><td>${val:.2f}</td></tr>"
 if rows=="":rows="<tr><td colspan=6 style='text-align:center;color:#666'>Sin posiciones</td></tr>"
 hrows=""
 for x in hist[-15:][::-1]:
  co="#00d395" if x.get('t')=="VENTA" else "#ffb020"
  hrows+=f"<tr><td>{x.get('f','')}</td><td style='color:{co}'>{x.get('t','')}</td><td>{x.get('m','')}</td><td>${x.get('p',0):.2f}</td></tr>"
 if hrows=="":hrows="<tr><td colspan=4 style='text-align:center;color:#666'>Sin trades</td></tr>"
 pnl=tot-1000.0
 pnl_col="#00d395" if pnl>=0 else "#ff4d4d"
 labels=",".join([str(i) for i in range(len(pr))])
 data=",".join([str(x) for x in pr])
 html=f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><script src='https://cdn.jsdelivr.net/npm/chart.js'></script><style>body{{background:#0b0e11;color:#e6e6e6;font-family:Inter,monospace;padding:14px;margin:0}}.top{{display:flex;gap:10px;margin-bottom:12px}}.card{{background:#151a21;border:1px solid #222a35;border-radius:14px;padding:14px;flex:1;box-shadow:0 4px 20px rgba(0,0,0,0.3)}}.big{{font-size:22px;font-weight:800}}.label{{color:#8b949e;font-size:11px;letter-spacing:1px}}table{{width:100%;border-collapse:collapse}}th{{color:#8b949e;font-size:11px;text-align:left;padding:8px;border-bottom:1px solid #222a35}}td{{padding:10px 8px;border-bottom:1px solid #151a21;font-size:13px}}.chartbox{{height:180px}}</style></head><body><h2 style='color:#fff;letter-spacing:2px'>V886 WALL ST PRO</h2><div class='top'><div class='card'><div class='label'>SALDO</div><div class='big'>${bal:.2f}</div></div><div class='card'><div class='label'>TOTAL</div><div class='big' style='color:#00d395'>${tot:.2f}</div></div><div class='card'><div class='label'>PNL</div><div class='big' style='color:{pnl_col}'>${pnl:.2f}</div></div></div><div class='card' style='margin-bottom:12px'><div class='label'>BTC/USD 40H</div><div class='chartbox'><canvas id='c'></canvas></div></div><div class='card' style='margin-bottom:12px'><div class='label'>POSICIONES ABIERTAS</div><table><tr><th>MON</th><th>CANT</th><th>ENT</th><th>ACT</th><th>PNL%</th><th>VAL</th></tr>{rows}</table></div><div class='card'><div class='label'>HISTORIAL</div><table><tr><th>FECHA</th><th>TIPO</th><th>MON</th><th>PRECIO</th></tr>{hrows}</table></div><script>new Chart(document.getElementById('c'),{{type:'line',data:{{labels:[{labels}],datasets:[{{data:[{data}],borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,0.15)',fill:true,tension:0.4,pointRadius:0,borderWidth:2}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{display:false}},y:{{display:true,grid:{{color:'#1a2332'}}}}}}}}}})</script></body></html>"
 return HTMLResponse(html)

@app.post("/webhook")
@app.post("/")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  cq=d["callback_query"];cid=cq["message"]["chat"]["id"];act,mon=cq["data"].split("_")
  s=load()
  if act=="GRAF":
   # ESTO ES LO QUE VERAS AL DARLE A GRAF
   tot=s['bal']
   for k,v in s['holds'].items():
    p=await price(k)
    tot+=v['a']*p
   pnl=tot-1000
   txt=f"📊 V886 WALL ST PRO\n\n💰 SALDO: ${s['bal']:.2f}\n💼 TOTAL: ${tot:.2f}\n📈 PNL: ${pnl:.2f}\n\n"
   txt+="--- POSICIONES ---\n"
   if not s['holds']:txt+="Sin posiciones\n"
   for k,v in s['holds'].items():
    p=await price(k)
    gn=(p/v['e']-1)*100 if v['e'] else 0
    e="🟢" if gn>=0 else "🔴"
    txt+=f"{e} {k} {gn:.2f}% VAL ${v['a']*p:.0f}\n"
   txt+=f"\n💻 Dashboard completo: {DASH}"
   await send(cid,txt,mon,True)
   return{"ok":True}
  p=await price(mon)
  if act=="BUY":
   if s['bal']>=100:
    s['holds'][mon]={'a':100/p,'e':p};s['bal']-=100
    s['hist'].append({'f':datetime.now().strftime("%d/%m %H:%M"),'t':"COMPRA",'m':mon,'p':p});save(s)
    await send(cid,f"✅ COMPRADO {mon} @ ${p:.2f}",mon,True)
  else:
   if mon in s['holds']:
    s['bal']+=s['holds'][mon]['a']*p
    s['hist'].append({'f':datetime.now().strftime("%d/%m %H:%M"),'t':"VENTA",'m':mon,'p':p})
    del s['holds'][mon];save(s)
    await send(cid,f"💰 VENDIDO {mon}",mon,True)
  return{"ok":True}
 m=d.get("message",{});cid=m.get("chat",{}).get("id")
 if not cid:return{"ok":True}
 txt
