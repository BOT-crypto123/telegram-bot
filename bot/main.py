import os,json,requests,threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.2")
BOT=None
for k,v in os.environ.items():
 if "TELE" in k.upper() and "TOKEN" in k.upper(): BOT=v
if not BOT: BOT=os.environ.get("BOT_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home(): return "V39.2 LIVE"
def load():
 try:
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  x=r.json().get("result")
  if x: return json.loads(x)
 except: pass
 return {"users":{}}
def save(d):
 try: requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(d)],timeout=10)
 except: pass
def market():
 try:
  b=float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=8).json()["data"]["amount"])
  e=float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot",timeout=8).json()["data"]["amount"])
  x=float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot",timeout=8).json()["data"]["amount"])
  fx=17.22
  try: fx=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=5).json()["rates"]["MXN"]
  except: pass
  return b,e,x,fx
 except: return 64273,1900,1.03,17.22
def getu(uid,d):
 uid=str(uid)
 if uid not in d["users"]:
  b,e,x,fx=market()
  d["users"][uid]={"ef":0.0,"btc":(333.33/fx)/b,"eth":(333.33/fx)/e,"xrp":(333.33/fx)/x,"ini":1000.0,"sl":7.0,"tp":10.0,"pc":{"btc":b,"eth":e,"xrp":x},"al":True,"ua":{}}
  save(d)
 if "al" not in d["users"][uid]: d["users"][uid]["al"]=True
 if "ua" not in d["users"][uid]: d["users"][uid]["ua"]={}
 return d["users"][uid]
def txt(u):
 b,e,x,fx=market()
 tot=u["ef"]+u["btc"]*b*fx+u["eth"]*e*fx+u["xrp"]*x*fx
 gan=(tot-u["ini"])/u["ini"]*100
 al="ON" if u.get("al") else "OFF"
 return f"V39.2 {al} SL:-{u['sl']:.0f}% TP:+{u['tp']:.0f}%\nMXN:{fx:.2f} Ef:{u['ef']:.2f}\nBTC {b:.0f} ETH {e:.0f} XRP {x:.2f}\nTOTAL:{tot:.2f} ({gan:+.1f}%)"
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
def kbm(u):
 t="Apagar Al" if u.get("al") else "Prender Al"
 return InlineKeyboardMarkup([ [InlineKeyboardButton("COMPRAR",callback_data="c"),InlineKeyboardButton("VENDER",callback_data="v")], [InlineKeyboardButton(f"SL -{u['sl']:.0f}%",callback_data="sl"),InlineKeyboardButton(f"TP +{u['tp']:.0f}%",callback_data="tp")], [InlineKeyboardButton("GRAFICA 7D",callback_data="g"),InlineKeyboardButton("PRO MAX",callback_data="p")], [InlineKeyboardButton(t,callback_data="al")], [InlineKeyboardButton("ACT",callback_data="a")] ])
def kbp(): return InlineKeyboardMarkup([ [InlineKeyboardButton("BTC PRO",callback_data="pb"),InlineKeyboardButton("ETH PRO",callback_data="pe")], [InlineKeyboardButton("XRP PRO",callback_data="px")], [InlineKeyboardButton("Volver",callback_data="a")] ])
def kbsl(): return InlineKeyboardMarkup([ [InlineKeyboardButton("-5%",callback_data="s5"),InlineKeyboardButton("-7%",callback_data="s7"),InlineKeyboardButton("-10%",callback_data="s10")], [InlineKeyboardButton("Volver",callback_data="a")] ])
def kbtp(): return InlineKeyboardMarkup([ [InlineKeyboardButton("+10%",callback_data="t10"),InlineKeyboardButton("+15%",callback_data="t15"),InlineKeyboardButton("+20%",callback_data="t20")], [InlineKeyboardButton("Volver",callback_data="a")] ])
def kbc(): return InlineKeyboardMarkup([ [InlineKeyboardButton("XRP $100",callback_data="cx"),InlineKeyboardButton("BTC $100",callback_data="cb")], [InlineKeyboardButton("ETH $100",callback_data="ce")], [InlineKeyboardButton("Volver",callback_data="a")] ])
def kbv(): return InlineKeyboardMarkup([ [InlineKeyboardButton("V Xrp",callback_data="vx"),InlineKeyboardButton("V Btc",callback_data="vb")], [InlineKeyboardButton("V Eth",callback_data="ve")], [InlineKeyboardButton("Volver",callback_data="a")] ])
def rsi_of(m):
 try:
  url=f"https://api.exchange.coinbase.com/products/{m}/candles?granularity=3600"
  d=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
  d=sorted(d,key=lambda x:x[0])[-168:]
  cl=[float(x[4]) for x in d]
  de=[cl[i]-cl[i-1] for i in range(1,len(cl))]
  ga=[max(0,x) for x in de]
  lo=[max(0,-x) for x in de]
  ag=sum(ga[:14])/14
  al=sum(lo[:14])/14
  r=[50]*14
  for i in range(14,len(de)):
   ag=(ag*13+ga[i])/14
   al=(al*13+lo[i])/14
   rs=ag/(al if al!=0 else 0.001)
   r.append(100-(100/(1+rs)))
  return r[-1],cl[-1]
 except: return 50,0
def chart_pro(m):
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 pa="/tmp/pro.png"
 url=f"https://api.exchange.coinbase.com/products/{m}/candles?granularity=3600"
 d=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=15).json()
 d=sorted(d,key=lambda x:x[0])[-168:]
 tm=[datetime.fromtimestamp(x[0]) for x in d]
 cl=[float(x[4]) for x in d]
 ma7=[sum(cl[i-7:i])/7 if i>=7 else cl[i] for i in range(len(cl))]
 ma25=[sum(cl[i-25:i])/25 if i>=25 else cl[i] for i in range(len(cl))]
 de=[cl[i]-cl[i-1] for i in range(1,len(cl))]
 ga=[max(0,x) for x in de]
 lo=[max(0,-x) for x in de]
 ag=sum(ga[:14])/14
 al=sum(lo[:14])/14
 r=[50]*14
 for i in range(14,len(de)):
  ag=(ag*13+ga[i])/14
  al=(al*13+lo[i])/14
  rs=ag/(al if al!=0 else 0.001)
  r.append(100-(100/(1+rs)))
 plt.style.use("dark_background")
 fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,7),gridspec_kw={"height_ratios":[3,1]})
 fig.patch.set_facecolor("#0e0e0e")
 ax1.set_facecolor("#0e0e0e")
 ax2.set_facecolor("#0e0e0e")
 ax1.plot(tm,cl,color="#00ff88",linewidth=2,label=m)
 ax1.plot(tm,ma7,color="#ffaa00",linewidth=1,label="MA7")
 ax1.plot(tm,ma25,color="#ff00ff",linewidth=1,label="MA25")
 ax1.legend()
 ax1.grid(True,alpha=0.2)
 ax2.plot(tm[-len(r):],r,color="#00aaff",linewidth=2)
 ax2.axhline(70,color="red",linestyle="--")
 ax2.axhline(30,color="green",linestyle="--")
 ax2.set_ylim(0,100)
 ax2.set_title(f"RSI {r[-1]:.1f}",color="white")
 ax2.grid(True,alpha=0.2)
 plt.tight_layout()
 plt.savefig(pa,dpi=150,facecolor="#0e0e0e")
 plt.close()
 plt.style.use("default")
 return pa,r[-1]
def chart7():
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 pa="/tmp/chart.png"
 plt.figure(figsize=(10,5))
 for prod,name,col in [("BTC-USD","BTC","#f7931a"),("ETH-USD","ETH","#627eea"),("XRP-USD","XRP","black")]:
  url=f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=3600"
  d=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=15).json()
  d=sorted(d,key=lambda x:x[0])[-168:]
  tm=[datetime.fromtimestamp(x[0]) for x in d]
  cl=[float(x[4]) for x in d]
  no=[(c/cl[0]*100)-100 for c in cl]
  plt.plot(tm,no,label=f"{name} {no[-1]:+.2f}%",color=col,linewidth=2)
 plt.title("7 Dias %")
 plt.legend()
 plt.grid(True,alpha=0.3)
 plt.tight_layout()
 plt.savefig(pa,dpi=150)
 plt.close()
 return pa
async def aloop(bot):
 print("loop al")
 while True:
  try:
   await asyncio.sleep(300)
   d=load()
   if not d["users"]: continue
   br,_=rsi_of("BTC-USD")
   er,_=rsi_of("ETH-USD")
   xr,_=rsi_of("XRP-USD")
   for uid,u in d["users"].items():
    if not u.get("al"): continue
    for mon,rv in [("BTC",br),("ETH",er),("XRP",xr)]:
     ua=u.get("ua",{}).get(mon,0)
     if time.time()-ua<14400: continue
     if rv<30:
      try:
       await bot.bot.send_message(chat_id=int(uid),text=f"ALERTA COMPRA {mon} RSI {rv:.1f}")
       u["ua"][mon]=time.time()
      except: pass
     elif rv>70:
      try:
       await bot.bot.send_message(chat_id=int(uid),text=f"ALERTA VENTA {mon} RSI {rv:.1f}")
       u["ua"][mon]=time.time()
      except: pass
   save(d)
  except Exception as e:
   print(e)
   await asyncio.sleep(60)
def start_thread():
 loop=asyncio.new_event_loop()
 asyncio.set_event_loop(loop)
 from telegram.ext import Application,CommandHandler,CallbackQueryHandler,ContextTypes
 from telegram import Update
 async def st(update:Update,context:ContextTypes.DEFAULT_TYPE):
  d
