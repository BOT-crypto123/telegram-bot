import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
D=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','')}/dashboard"
def L():
 try:return json.load(open(F))
 except:return{"b":1000,"h":{}}
def S(s):json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{m}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:return 65000
async def G(cid,t,mon):
 async with httpx.AsyncClient() as c:
  kb={"inline_keyboard":[[{"text":"📊 GRAF","callback_data":"GRAF_"+mon},{"text":"💻 DASH","url":D}],[{"text":"BUY","callback_data":"BUY_"+mon},{"text":"SELL","callback_data":"SELL_"+mon}]]}
  await c.post(B+"/sendMessage",json={"chat_id":cid,"text":t,"reply_markup":kb})

@app.get("/")
def h():return{"V888":D}
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L();b=s["b"];tot=b;rows=""
 for k,v in s["h"].items():
  p=await P(k)
  tot+=v["a"]*p
  gn=(p/v["e"]-1)*100 if v["e"] else 0
  col="#00d395" if gn>=0 else "#ff4d4d"
  rows+=f"<tr><td>{k}</td><td>{v['a']:.4f}</td><td style='color:{col}'>{gn:.1f}%</td><td>${v['a']*p:.0f}</td></tr>"
 if not rows:rows="<tr><td colspan=4 style='color:#666;text-align:center'>No pos - Compra en Telegram</td></tr>"
 pnl=tot-1000
 html=f"""
 <html><head><meta name=viewport content='width=device-width'><style>
 body{{background:#000;color:#fff;font-family:monospace;padding:12px;margin:0}}
 .top{{display:flex;gap:8px;margin:10px 0}}
 .c{{background:#151a21;border:1px solid #222;border-radius:12px;padding:12px;flex:1}}
 .b{{font-size:18px;font-weight:bold}} .g{{color:#00d395}} .r{{color:#ff4d4d}}
 table{{width:100%;border-collapse:collapse}} td{{padding:8px;border-bottom:1px solid #222}}
 </style></head><body>
 <b>V888 CALLE MURALLA</b>
 <div class=top><div class=c>SALDO<br><div class=b>${b:.2f}</div></div><div class=c>TOTAL<br><div class=b g>${tot:.2f}</div></div><div class=c>PNL<br><div class=b style='color:{"#00d395" if pnl>=0 else "#ff4d4d"}'>${pnl:.2f}</div></div></div>
 <div class=c><table><tr><th>MON</th><th>QTY</th><th>PNL%</th><th>VAL</th></tr>{rows}</table></div>
 </body></html>"""
 return HTMLResponse(html)

@app.post("/webhook")
@app.post("/")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  q=d["callback_query"];cid=q["message"]["chat"]["id"];a,m=q["data"].split("_");s=L()
  if a=="GRAF":
   tot=s["b"];txt=f"📊 CALLE MURALLA\nSALDO ${s['b']:.2f}\
