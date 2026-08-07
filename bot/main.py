import os,json,requests
import threading,time,asyncio,traceback
from flask import Flask
from datetime import datetime
print("V39.6.4 DEBUG ERROR")
BOT=os.environ.get("BOT_TOKEN")
if not BOT:
 for k,v in os.environ.items():
  if "TELE" in k and "TOKEN" in k:
   BOT=v
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k and "URL" in k:
  URL=v
 if "UPSTASH" in k and "TOKEN" in k:
  if "REDIS" in k and v!=BOT:
   TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home():
 return "V39.6.4 LIVE"
def load():
 try:
  if not URL or not TOK:
   return {"users":{}}
  r=requests.post(URL,headers={
   "Authorization":f"Bearer {TOK}"
  },json=["GET",KEY],timeout=10)
  j=r.json().get("result")
  if j:
   return json.loads(j)
 except Exception as e:
  print(f"load err {e}")
 return {"users":{}}
def save(d):
 try:
  requests.post(URL,headers={
   "Authorization":f"Bearer {TOK}"
  },json=["SET",KEY,json.dumps(d)],timeout=10)
 except Exception as e:
  print(f"save err {e}")
def market():
 try:
  a="https://api.coinbase.com/v2/prices/"
  b=requests.get(a+"BTC-USD/spot",timeout=8).json()
  b=float(b["data"]["amount"])
  e=requests.get(a+"ETH-USD/spot",timeout=8).json()
  e=float(e["data"]["amount"])
  x=requests.get(a+"XRP-USD/spot",timeout=8).json()
  x=float(x["data"]["amount"])
  fx=17.22
  try:
   f=requests.get(
    "https://api.exchangerate-api.com/v4/latest/USD",
    timeout=5).json()
   fx=f["rates"]["MXN"]
  except:
   pass
  return b,e,x,fx
 except Exception as e:
  print(f"market err {e}")
  return 64000,1890,1.02,17.22
def getu(uid,d):
 uid=str(uid)
 if uid not in d["users"]:
  b,e,x,fx=market()
  u={}
  u["efectivo"]=0.0
  u["btc"]=(333.33/fx)/b
  u["eth"]=(333.33/fx)/e
  u["xrp"]=(333.33/fx)/x
  u["inicial"]=1000.0
  u["stoploss"]=7.0
  u["takeprofit"]=10.0
  u["precio_compra"]={}
  u["precio_compra"]["btc"]=b
  u["precio_compra"]["eth"]=e
  u["precio_compra"]["xrp"]=x
  u["alertas"]=True
  u["ultima_alerta"]={}
  d["users"][uid]=u
  save(d)
 u=d["users"][uid]
 if "alertas" not in u:
  u["alertas"]=True
 if "ultima_alerta" not in u:
  u["ultima_alerta"]={}
 return u
def texto(u):
 b,e,x,fx=market()
 tot=u["efectivo"]
 tot+=u["btc"]*b*fx
 tot+=u["eth"]*e*fx
 tot+=u["xrp"]*x*fx
 gan=(tot-u["inicial"])/u["inicial"]*100
 al="ON" if u.get("alertas") else "OFF"
 t=f"V39.6.4 {al} "
 t+=f"SL:-{u['stoploss']:.0f}% "
 t+=f"TP:+{u['takeprofit']:.0f}%\n"
 t+=f"MXN:{fx:.2f} "
 t+=f"Ef:{u['efectivo']:.2f}\n"
 t+=f"BTC {b:.0f} "
 t+=f"ETH {e:.0f} "
 t+=f"XRP {x:.2f}\n"
 t+=f"TOTAL:{tot:.2f} "
 t+=f"({gan:+.1f}%)"
 return t
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
def kb_main(u):
 a="Apagar" if u.get("alertas") else "Prender"
 b1=InlineKeyboardButton("COMPRAR",callback_data="menu_c")
 b2=InlineKeyboardButton("VENDER",callback_data="menu_v")
 b3=InlineKeyboardButton("SL",callback_data="menu_sl")
 b4=InlineKeyboardButton("TP",callback_data="menu_tp")
 b5=InlineKeyboardButton("GRAF",callback_data="grafica")
 b6=InlineKeyboardButton("PRO",callback_data="pro")
 b7=InlineKeyboardButton(a,callback_data="toggle_alert")
 b8=InlineKeyboardButton("ACT",callback_data="act")
 r=[[b1,b2],[b3,b4],[b5,b6],[b7],[b8]]
 return InlineKeyboardMarkup(r)
def kb_pro():
 b1=InlineKeyboardButton("BTC",callback_data="pro_btc")
 b2=InlineKeyboardButton("ETH",callback_data="pro_eth")
 b3=InlineKeyboardButton("XRP",callback_data="pro_xrp")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2],[b3],[b4]])
def kb_sl():
 b1=InlineKeyboardButton("-5%",callback_data="sl_5")
 b2=InlineKeyboardButton("-7%",callback_data="sl_7")
 b3=InlineKeyboardButton("-10%",callback_data="sl_10")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2,b3],[b4]])
def kb_tp():
 b1=InlineKeyboardButton("+10%",callback_data="tp_10")
 b2=InlineKeyboardButton("+15%",callback_data="tp_15")
 b3=InlineKeyboardButton("+20%",callback_data="tp_20")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2,b3],[b4]])
def kb_c():
 b1=InlineKeyboardButton("XRP100",callback_data="c_xrp_100")
 b2=InlineKeyboardButton("BTC100",callback_data="c_btc_100")
 b3=InlineKeyboardButton("ETH100",callback_data="c_eth_100")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2],[b3],[b4]])
def kb_v():
 b1=InlineKeyboardButton("V-XRP",callback_data="v_xrp")
 b2=InlineKeyboardButton("V-BTC",callback_data="v_btc")
 b3=InlineKeyboardButton("V-ETH",callback_data="v_eth")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2],[b3],[b4]])
def get_rsi_for(moneda):
 try:
  base="https://api.exchange.coinbase.com/products/"
  url=base+moneda+"/candles?granularity=3600"
  data=requests.get(url,headers={
   "User-Agent":"Mozilla/5.0"},timeout=10).json()
  data=sorted(data,key=lambda x:x[0])[-168:]
  closes=[float(d[4]) for d in data]
  deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
  gains=[max(0,d) for d in deltas]
  losses=[max(0,-d) for d in deltas]
  ag=sum(gains[:14])/14
  al=sum(losses[:14])/14
  rsi=[50]*14
  for i in range(14,len(deltas)):
   ag=(ag*13+gains[i])/14
   al=(al*13+losses[i])/14
   rs=ag/(al if al!=0 else 0.001)
   rsi.append(100-(100/(1+rs)))
  return rsi[-1],closes[-1]
 except:
  return 50,0
def crear_grafica_pro(moneda):
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 path="/tmp/pro.png"
 base="https://api.exchange.coinbase.com/products/"
 url=base+moneda+"/candles?granularity=3600"
 data=requests.get(url,headers={
  "User-Agent":"Mozilla/5.0"},timeout=15).json()
 data=sorted(data,key=lambda x:x[0])[-168:]
 times=[datetime.fromtimestamp(d[0]) for d in data]
 closes=[float(d[4]) for d in data]
 ma7=[]
 for i in range(len(closes)):
  if i>=7:
   ma7.append(sum(closes[i-7:i])/7)
  else:
   ma7.append(closes[i])
 ma25=[]
 for i in range(len(closes)):
  if i>=25:
   ma25.append(sum(closes[i-25:i])/25)
  else:
   ma25.append(closes[i])
 deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
 gains=[max(0,d) for d in deltas]
 losses=[max(0,-d) for d in deltas]
 ag=sum(gains[:14])/14
 al=sum(losses[:14])/14
 rsi=[50]*14
 for i in range(14,len(deltas)):
  ag=(ag*13+gains[i])/14
  al=(al*13+losses[i])/14
  rs=ag/(al if al!=0 else 0.001)
  rsi.append(100-(100/(1+rs)))
 plt.style.use("dark_background")
 fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,7))
 ax1.plot(times,closes,color="#00ff88",linewidth=2,label=moneda)
 ax1.plot(times,ma7,color="#ffaa00",linewidth=1,label="MA7")
 ax1.plot(times,ma25,color="#ff00ff",linewidth=1,label="MA25")
 ax1.legend()
 ax1.grid(True,alpha=0.2)
 ax1.set_title(f"{moneda} PRO",color="white")
 rt=times[len(times)-len(rsi):]
 ax2.plot(rt,rsi,color="#00aaff",linewidth=2)
 ax2.axhline(70,color="red",linestyle="--")
 ax2.axhline(30,color="green",linestyle="--")
 ax2.set_ylim(0,100)
 ax2.set_title(f"RSI {rsi[-1]:.1f}",color="white")
 ax2.grid(True,alpha=0.2)
 plt.tight_layout()
 plt.savefig(path,dpi=150,facecolor="#0e0e0e")
 plt.close()
 return path,rsi[-1]
def crear_grafica_7d():
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 path="/tmp/chart.png"
 plt.figure(figsize=(10,5))
 lista=[("BTC-USD","BTC","#f7931a"),
        ("ETH-USD","ETH","#627eea"),
        ("XRP-USD","XRP","black")]
 for prod,name,col in lista:
  base="https://api.exchange.coinbase.com/products/"
  url=base+prod+"/candles?granularity=3600"
  data=requests.get(url,headers={
   "User-Agent":"Mozilla/5.0"},timeout=15).json()
  data=sorted(data,key=lambda x:x[0])[-168:]
  times=[datetime.fromtimestamp(d[0]) for d in data]
  closes=[float(d[4]) for d in data]
  norm=[(c/closes[0]*100)-100 for c in closes]
  plt.plot(times,norm,label=f"{name} {norm[-1]:+.2f}%",
           color=col,linewidth=2)
 plt.title("7 Dias %")
 plt.legend()
 plt.grid(True,alpha=0.3)
 plt.tight_layout()
 plt.savefig(path,dpi=150)
 plt.close()
 return path
async def alert_loop(app_bot):
 print("Loop V39.6.4 SLTP")
 await asyncio.sleep(15)
 while True:
  try:
   data=load()
   if not data["users"]:
    await asyncio.sleep(60)
    continue
   br,_=get_rsi_for("BTC-USD")
   er,_=get_rsi_for("ETH-USD")
   xr,_=get_rsi_for("XRP-USD")
   b,e,x,fx=market()
   print(f"RSI B{br:.1f} E{er:.1f} X{xr:.1f}")
   for uid,u in data["users"].items():
    try:
     if not u.get("alertas",True):
      continue
     if "ultima_alerta" not in u:
      u["ultima_alerta"]={}
     tot=u["efectivo"]
     tot+=u["btc"]*b*fx
     tot+=u["eth"]*e*fx
     tot+=u["xrp"]*x*fx
     gan=0
     if u["inicial"]!=0:
      gan=(tot-u["inicial"])/u["inicial"]*100
     if gan <= -u["stoploss"]:
      last=u["ultima_alerta"].get("SL",0)
      if time.time()-last>14400:
       msg="STOP LOSS %.1f%% %.2f" % (gan,tot)
       await app_bot.bot.send_message(
        chat_id=int(uid),text=msg)
       u["ultima_alerta"]["SL"]=time.time()
     if gan >= u["takeprofit"]:
      last=u["ultima_alerta"].get("TP",0)
      if time.time()-last>14400:
       msg="TAKE PROFIT %.1f%% %.2f" % (gan,tot)
       await app_bot.bot.send_message(
        chat_id=int(uid),text=msg)
       u["ultima_alerta"]["TP"]=time.time()
     for mon,rv in [("BTC",br),("ETH",er),("XRP",xr)]:
      last=u["ultima_alerta"].get(mon,0)
      if time.time()-last<14400:
       continue
      if rv<30:
       m="COMPRA %s RSI %.1f" % (mon,rv)
       await app_bot.bot.send_message(
        chat_id=int(uid),text=m)
       u["ultima_alerta"][mon]=time.time()
      elif rv>70:
       m="VENTA %s RSI %.1f" % (mon,rv)
       await app_bot.bot.send_message(
        chat_id=int(uid),text=m)
       u["ultima_alerta"][mon]=time.time()
     data["users"][uid]=u
    except Exception as e:
     print(f"Err u {e}")
     traceback.print_exc()
   save(data)
   await asyncio.sleep(300)
  except Exception as e:
   print(f"Err loop {e}")
   traceback.print_exc()
   await asyncio.sleep(60)
def start_bot_thread():
 loop=asyncio.new_event_loop()
 asyncio.set_event_loop(loop)
 from telegram.ext import Application
 from telegram.ext import CommandHandler
 from telegram.ext import CallbackQueryHandler
 async def st(update,context):
  d=load()
  u=getu(update.effective_user.id,d)
  save(d)
  await update.message.reply_text(
   texto(u),reply_markup=kb_main(u))
 async def bt(update,context):
  q=update.callback_query
  await q.answer()
  d=load()
  uid=str(q.from_user.id)
  u=getu(uid,d)
  b,e,x,fx=market()
  pr={"btc":b,"eth":e,"xrp":x}
  k=q.data
  if k=="act":
   await q.edit_message_text(
    texto(u),reply_markup=kb_main(u))
   return
  if k=="toggle_alert":
   u["alertas"]=not u.get("alertas",True)
   d["users"][uid]=u
   save(d)
   await q.edit_message_text(
    texto(u),reply_markup=kb_main(u))
   return
  if k=="menu_c":
   await q.edit_message_text(
    "Que compras?",reply_markup=kb_c())
   return
  if k=="menu_v":
   await q.edit_message_text(
    "Que vendes?",reply_markup=kb_v())
   return
  if k=="menu_sl":
   await q.edit_message_text(
    f"SL -{u['stoploss']}%",reply_markup=kb_sl())
   return
  if k=="menu_tp":
   await q.edit_message_text(
    f"TP +{u['takeprofit']}%",reply_markup=kb_tp())
   return
  if k=="pro":
   await q.edit_message_text(
    "PRO MAX:",reply_markup=kb_pro())
   return
  if k.startswith("sl_"):
   u["stoploss"]=float(k.split("_")[1])
   d["users"][uid]=u
   save(d)
   await q.edit_message_text(
    texto(u),reply_markup=kb_main(u))
   return
  if k.startswith("tp_"):
   u["takeprofit"]=float(k.split("_")[1])
   d["users"][uid]=u
   save(d)
   await q.edit_message_text(
    texto(u),reply_markup=kb_main(u))
   return
  if k.startswith("c_"):
   mon=k.split("_")[1]
   if u["efectivo"]<100:
    await q.edit_message_text(
     f"Sin efectivo\n{texto(u)}",
     reply_markup=kb_main(u))
    return
   qty=(100/fx)/pr[mon]
   u[mon]+=qty
   u["efectivo"]-=100
   d["users"][uid]=u
   save(d)
   await q.edit_message_text(
    texto(u),reply_markup=kb_main(u))
   return
  if k.startswith("v_"):
   mon=k.split("_")[1]
   mxn=u[mon]*pr[mon]*fx
   u[mon]=0
   u["efectivo"]+=mxn
   d["users"][uid]=u
   save(d)
   await q.edit_message_text(
    texto(u),reply_markup=kb_main(u))
   return
  if k=="grafica":
   try:
    await q.edit_message_text("Generando 7D...")
    pa=crear_grafica_7d()
    f=open(pa,"rb")
    await q.message.reply_photo(
     photo=f,caption="7D %")
    f.close()
    await q.message.reply_text(
     texto(u),reply_markup=kb_main(u))
   except Exception as e:
    traceback.print_exc()
    await q.edit_message_text(
     f"Error: {e}\n{texto(u)}",
     reply_markup=kb_main(u))
   return
  if k.startswith("pro_"):
   try:
    mon=k.split("_")[1]
    mapa={"btc":"BTC-USD","eth":"ETH-USD","xrp":"XRP-USD"}
    await q.edit_message_text(
     f"Generando {mon.upper()} PRO...")
    pa,rv=crear_grafica_pro(mapa[mon])
    f=open(pa,"rb")
    await q.message.reply_photo(
     photo=f,caption=f"{mon.upper()} RSI {rv:.1f}")
    f.close()
    await q.message.reply_text(
     texto(u),reply_markup=kb_main(u))
   except Exception as e:
    traceback.print_exc()
    await q.edit_message_text(
     f"Error PRO: {e}\n{texto(u)}",
     reply_markup=kb_main(u))
   return
 async def main_async():
  try:
   app_bot=Application.builder().token(BOT).build()
   app_bot.add_handler(CommandHandler("start",st))
   app_bot.add_handler(CallbackQueryHandler(bt))
   try:
    await app_bot.bot.delete_webhook(
     drop_pending_updates=True)
    print("Webhook borrado OK")
   except Exception as e:
    print(f"webhook err {e}")
   await app_bot.initialize()
   await app_bot.start()
   await app_bot.updater.start_polling(
    drop_pending_updates=True)
   print("Bot V39.6.4 OK - LISTO")
   asyncio.create_task(alert_loop(app_bot))
   while True:
    await asyncio.sleep(3600)
  except Exception as e:
   print(f"FATAL BOT ERROR: {e}")
   traceback.print_exc()
   raise e
 while True:
  try:
   loop.run_until_complete(main_async())
  except Exception as e:
   print(f"Crash {e}")
   traceback.print_exc()
   time.sleep(5)
print("Iniciando hilo bot...")
threading.Thread(target=start_bot_thread,daemon=False).start()
print("Hilo lanzado, iniciando Flask...")
try:
 if __name__=="__main__":
  port=int(os.environ.get("PORT",10000))
  print(f"Flask en puerto {port}")
  app.run(host="0.0.0.0",port=port)
except Exception as e:
 print(f"FLASK ERROR: {e}")
 traceback.print_exc()
