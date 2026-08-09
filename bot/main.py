import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
app=FastAPI()
T=os.getenv("TELEGRAM_TOKEN","")
B=f"https://api.telegram.org/bot{T}"
F="/tmp/b.json"
D=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','')}/dashboard"
def L():
 try:
  return json.load(open(F))
 except:
  return{"b":1000,"h":{}}
def S(s):
 json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:
   r=await c.get(f"https://api.coinbase.com/v2/prices/{m}-USD/spot")
   return float(r.json()["data"]["amount"])
 except:
  return 65000
async def G(cid,t,mon):
 async with httpx.AsyncClient() as c:
  kb={"inline_keyboard":[[{"text":"GRAF","callback_data":"GRAF_"+mon}],[{"text":"BUY","callback_data":"BUY_"+mon},{"text":"SELL","callback_data":"SELL_"+mon}]]}
  await c.post(B+"/sendMessage",json={"chat_id":cid,"text":t,"reply_markup":kb})
@app.get("/")
def home():
 return{"v":"V892 SOLO GRAF"}
@app.get("/dashboard",response_class=HTMLResponse)
async def dash():
 s=L()
 b=s["b"]
 h=s["h"]
 tot=b
 rows=""
 if len(h)==0:
  rows="<tr><td colspan=4 style='text-align:center;color:#666;padding:20px'>No pos</td></tr>"
 else:
  for k in h:
   v=h[k]
   amt=v["a"]
   ent=v["e"]
   pr=await P(k)
   val=amt*pr
   tot=tot+val
   pnl=(pr/ent-1)*100
   col="#00d395" if pnl>=0 else "#ff4d4d"
   rows=rows+f"<tr><td><b>{k}</b></td><td>{amt:.4f}</td><td style='color:{col}'>{pnl:.1f}%</td><td>${val:.0f}</td></tr>"
 pnl=tot-1000
 pnlcol="#00d395" if pnl>=0 else "#ff4d4d"
 html=""
 html=html+"<html><head><meta name=viewport content='width=device-width'><style>"
 html=html+"body{background:#0b0e11;color:#fff;font-family:monospace;padding:12px;margin:0}"
 html=html+".top{display:flex;gap:8px;margin:12px 0}.card{background:#151a21;border:1px solid #222a35;border-radius:12px;padding:12px;flex:1}"
 html=html+".big{font-size:18px;font-weight:bold}.lbl{color:#8b949e;font-size:11px}"
 html=html+"table{width:100%;border-collapse:collapse}th{color:#8b949e;font-size:11px;text-align:left;padding:8px;border-bottom:1px solid #222}td{padding:10px 8px;border-bottom:1px solid #151a21}"
 html=html+"</style></head><body>"
 html=html+f"<h3>V892 WALL ST PRO</h3>"
 html=html+f"<div class=top><div class=card><div class=lbl>SALDO</div><div class=big>${b:.2f}</div></div><div class=card><div class=lbl>TOTAL</div><div class=big style='color:#00d395'>${tot:.2f}</div></div><div class=card><div class=lbl>PNL</div><div class=big style='color:{pnlcol}'>${pnl:.2f}</div></div></div>"
 html=html+f"<div class=card><table><tr><th>MON</th><th>QTY</th><th>PNL%</th><th>VAL</th></tr>{rows}</table></div>"
 html=html+"</body></html>"
 return HTMLResponse(html)
@app.post("/webhook")
@app.post("/")
async def wh(r:Request):
 d=await r.json()
 if "callback_query" in d:
  q=d["callback_query"]
  cid=q["message"]["chat"]["id"]
  dat=q["data"]
  parts=dat.split("_")
  a=parts[0]
  m=parts[1]
  s=L()
  if a=="GRAF":
   b=s["b"]
   hh=s["h"]
   tot=b
   txt="WALL ST PRO\n"
   txt=txt+f"SALDO ${b:.2f}\n"
   if len(hh)==0:
    txt=txt+"No pos\n"
   else:
    for k in hh:
     v=hh[k]
     pr=await P(k)
     tot=tot+v["a"]*pr
     pnl=(pr/v["e"]-1)*100
     txt=txt+f"{k} {pnl:.1f}% ${v['a']*pr:.0f}\n"
   pnl=tot-1000
   txt=txt+f"TOTAL ${tot:.2f} PNL ${pnl:.2f}"
   await G(cid,txt,m)
   return{"ok":True}
  p=await P(m)
  if a=="BUY":
   s["h"][m]={"a":100/p,"e":p}
   s["b"]=s["b"]-100
   S(s)
   await G(cid,f"BUY {m} {p:.0f}",m)
  else:
   hh=s["h"]
   if m in hh:
    s["b"]=s["b"]+100
    del s["h"][m]
    S(s)
    await G(cid,f"SELL {m}",m)
  return{"ok":True}
 x=d.get("message",{})
 cid=x.get("chat",{}).get("id")
 if not cid:
  return{"ok":True}
 t=(x.get("text")or"").upper()
 if t in["BTC","ETH","SOL","XRP"]:
  p=await P(t)
  await G(cid,f"{t} ${p:.0f}",t)
 else:
  await G(cid,"V892 WALL ST", "BTC")
 return{"ok":True}
