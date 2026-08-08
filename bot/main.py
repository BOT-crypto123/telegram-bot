import os, requests
from flask import Flask, request
TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app = Flask(__name__)
SEL="BTC"; SL=5.0; TP=10.0; ENTS={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=5).json()
  return float(r["data"]["amount"])
 except: return 0
def msg(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=8)
 except: pass
@app.route("/")
def home(): return f"V48 LIVE {SEL} {price(SEL)} SL:-{SL}% TP:+{TP}%",200
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
   msg(cid,f"SL -{SL}% OK"); return "ok",200
  if t.startswith("TP "):
   try: TP=float(t.replace("TP","").replace("%","").strip())
   except: pass
   msg(cid,f"TP +{TP}% OK"); return "ok",200
  if t in ["BTC","ETH","SOL","XRP"]: SEL=t
  p=price(SEL)
  if "GRAF" in t:
   try:
    import urllib.parse as up
    url=f"https://api.exchange.coinbase.com/products/{SEL}-USD/candles?granularity=300"
    data=requests.get(url,timeout=10,headers={"User-Agent":"bot"}).json()
    pr=[]
    if isinstance(data,list):
     rev=list(reversed(data)); s=len(rev)-80
     if s<0: s=0
     for i in range(s,len(rev)):
      try: pr.append(float(rev[i][4]))
      except: pass
    if len(pr)<5: pr=[p*0.995,p*1.002,p*0.998,p]
    last=pr[-1]; ch=(last/pr[0]-1)*100
    col="#00ff88" if ch>=0 else "#ff4444"
    ds=",".join([str(x) for x in pr])
    cfg="{type:'line',data:{datasets:[{data:["+ds+"],borderColor:'"+col+"',fill:false,pointRadius:0,borderWidth:2}]},options:{legend:{display:false}}}"
    q="https://quickchart.io/chart?bkg=black&width=800&height=400&c="+up.quote(cfg)
    surl="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
    cap=f"{SEL} {round(last,2)} {round(ch,2)}% SL:-{SL}% TP:+{TP}%"
    requests.post(surl,data={"chat_id":cid,"caption":cap,"photo":q},timeout=10)
   except: msg(cid,"Error graf")
  elif "COMPRAR" in t: ENTS[SEL]=p; msg(cid,f"PARTIDA {SEL} {round(p,2)}")
  elif "VENDER" in t:
   if SEL in ENTS: del ENTS[SEL]; msg(cid,f"CERRADA {SEL}")
   else: msg(cid,"Sin partida")
  else: msg(cid,f"{SEL} {round(p,2)} SL:-{SL}% TP:+{TP}%")
  return "ok",200
 except: return "ok",200
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
