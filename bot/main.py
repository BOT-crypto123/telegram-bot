import os, requests
from flask import Flask, request
TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app = Flask(__name__)
SEL="BTC"; SL=5.0; TP=10.0; ENTS={}; LAST={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def send(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except: pass
@app.route("/")
def home():
 p=price(SEL)
 return "V48 LIVE "+SEL+" "+str(round(p,2)),200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL,SL,TP
 try:
  d=request.get_json(force=True,silent=True)
  if not d or "message" not in d: return "ok",200
  cid=d["message"]["chat"]["id"]
  t=d["message"].get("text","").upper().strip()
  if t.startswith("SL "):
   try: SL=float(t.replace("SL","").replace("%","").strip())
   except: pass
   send(cid,"SL -"+str(SL)+"% OK"); return "ok",200
  if t.startswith("TP "):
   try: TP=float(t.replace("TP","").replace("%","").strip())
   except: pass
   send(cid,"TP +"+str(TP)+"% OK"); return "ok",200
  if t in ["BTC","ETH","SOL","XRP"]: SEL=t
  p=price(SEL)
  if p==0: p=LAST.get(SEL,0)
  else: LAST[SEL]=p
  if "GRAF" in t:
   try:
    import urllib.parse as up
    url="https://api.exchange.coinbase.com/products/"+SEL+"-USD/candles?granularity=300"
    data=requests.get(url,timeout=10,headers={"User-Agent":"Mozilla"}).json()
    pr=[]
    if isinstance(data,list):
     rev=list(reversed(data))
     s=max(0,len(rev)-80)
     for i in range(s,len(rev)):
      try: pr.append(float(rev[i][4]))
      except: pass
    if len(pr)<5: pr=[p*0.992,p*0.997,p*1.003,p*0.998,p]
    ch=(pr[-1]/pr[0]-1)*100 if pr[0]!=0 else 0
    col="#00ff88" if ch>=0 else "#ff4444"
    ds=",".join([str(x) for x in pr])
    cfg="{type:'line',data:{datasets:[{data:["+ds+"],borderColor:'"+col+"',fill:false,pointRadius:0,borderWidth:2}]},options:{legend:{display:false}}}"
    q="https://quickchart.io/chart?bkg=black&width=800&height=400&c="+up.quote(cfg)
    surl="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
    cap=SEL+" "+str(round(pr[-1],2))+" "+str(round(ch,2))+"% SL:-"+str(SL)+"% TP:+"+str(TP)+"%"
    requests.post(surl,data={"chat_id":cid,"caption":cap,"photo":q},timeout=12)
   except: send(cid,"Error graf")
  elif "COMPRAR" in t: ENTS[SEL]=p; send(cid,"ABIERTA "+SEL+" "+str(round(p,2)))
  elif "VENDER" in t:
   if SEL in ENTS: del ENTS[SEL]; send(cid,"CERRADA "+SEL)
   else: send(cid,"Sin partida")
  elif "PRO" in t:
   if not ENTS: send(cid,"Sin partidas")
   else:
    txt=""
    for k,v in ENTS.items():
     pp=price(k); pnl=(pp/v-1)*100 if v!=0 else 0
     txt+=k+" "+str(round(pnl,2))+"% "
    send(cid,txt)
  else: send(cid,SEL+" "+str(round(p,2))+" SL:-"+str(SL)+"% TP:+"+str(TP)+"%")
  return "ok",200
 except: return "ok",200
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
