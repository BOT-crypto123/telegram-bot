import os,json,requests,threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.5 FIX ANTI-CONFLICT")
BOT=None
for k,v in os.environ.items():
 if "TELE" in k.upper() and "TOKEN" in k.upper():
  BOT=v
if not BOT:
 BOT=os.environ.get("BOT_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k.upper() and "URL" in k.upper():
  URL=v
 if "UPSTASH" in k.upper() and "TOKEN" in k.upper():
  if "REDIS" in k.upper() and v!=BOT:
   TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home():
 return "V39.5 LIVE ANTI-CONFLICT OK"
def load():
 try:
  if not URL or not TOK: return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  res=r.json().get("result")
  if res: return json.loads(res)
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
 except: return 64280,1898,1.02,17.22
def getu(uid,d):
 uid=str(uid)
 if uid not in d["users"]:
  b,e,x,fx=market()
  d["users"][uid]={"efectivo":0.0,"btc":(333.33/fx)/b,"eth":(333.33/fx)/e,"xrp":(333.33/fx)/x,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":b,"eth":e,"xrp":x},"alertas":True,"ultima_alerta":{}}
  save(d)
 u=d["users"][uid]
 if "alertas" not in u: u["alertas"]=True
 if "ultima_alerta" not in u: u["ultima_alerta"]={}
 return u
def texto(u):
 b,e,x,fx=market()
 tot=u["efectivo"]+u["btc"]*b*fx+u["eth"]*e*fx+u["xrp"]*x*fx
 gan=(tot-u["inicial"])/u["inicial"]*100
 al="ON" if u.get("alertas") else "OFF"
 return f"V39.5 {al} SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\nMXN:{fx:.2f} Ef:{u['efectivo']:.2f}\nBTC {b:.0f} ETH {e:.0f} XRP {x:.2f}\nTOTAL:{tot:.2f} ({gan:+.1f}%)"
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
def kb_main(u):
 t="Apagar" if u.get("alertas") else "Prender"
 r=[[InlineKeyboardButton("COMPRAR",callback_data="menu_c"),InlineKeyboardButton("VENDER",callback_data="menu_v")],[InlineKeyboardButton(f"SL -{u['stoploss']:.0f}%",callback_data="menu_sl"),InlineKeyboardButton(f"TP +{u['takeprofit']:.0f}%",callback_data="menu_tp")],[InlineKeyboardButton("GRAFICA 7D",callback_data="grafica"),InlineKeyboardButton("PRO MAX",callback_data="pro")],[InlineKeyboardButton(t,callback_data="toggle_alert")],[InlineKeyboardButton("ACTUALIZAR",callback_data="act")]]
 return InlineKeyboardMarkup(r)
def kb_pro(): return InlineKeyboardMarkup([[InlineKeyboardButton("BTC PRO",callback_data="pro_btc"),InlineKeyboardButton("ETH PRO",callback_data="pro_eth")],[InlineKeyboardButton("XRP PRO",callback_data="pro_xrp")],[InlineKeyboardButton("Volver",callback_data="act")]])
def kb_sl(): return InlineKeyboardMarkup([[InlineKeyboardButton("-5%",callback_data="sl_5"),InlineKeyboardButton("-7%",callback_data="sl_7"),InlineKeyboardButton("-10%",callback_data="sl_10")],[InlineKeyboardButton("Volver",callback_data="act")]])
def kb_tp(): return InlineKeyboardMarkup([[InlineKeyboardButton("+10%",callback_data="tp_10"),InlineKeyboardButton("+15%",callback_data="tp_15"),InlineKeyboardButton("+20%",callback_data="tp_20")],[InlineKeyboardButton("Volver",callback_data="act")]])
def kb_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("XRP $100",callback_data="c_xrp_100"),InlineKeyboardButton("BTC $100",callback_data="c_btc_100")],[InlineKeyboardButton("ETH $100",callback_data="c_eth_100")],[InlineKeyboardButton("Volver",callback_data="act")]])
def kb_v(): return InlineKeyboardMarkup([[InlineKeyboardButton("Vender XRP",callback_data="v_xrp"),InlineKeyboardButton("Vender BTC",callback_data="v_btc")],[InlineKeyboardButton("Vender ETH",callback_data="v_eth")],[InlineKeyboardButton("Volver",callback_data="act")]])
def get_rsi_for(moneda):
 try:
  data=requests.get(f"https://api.exchange.coinbase.com/products/{moneda}/candles?granularity=3600",headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
  data=sorted(data,key=lambda x:x[0])[-168:]; closes=[float(d[4]) for d in data]
  deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]; gains=[max(0,d) for d in deltas]; losses=[max(0,-d) for d in deltas]
  avg_g=sum(gains[:14])/14; avg_l=sum(losses[:14])/14; rsi=[50]*14
  for i in range(14,len(deltas)):
   avg_g=(avg_g*13+gains[i])/14; avg_l=(avg_l*13+losses[i])/14; rs=avg_g/(avg_l if avg_l!=0 else 0.001); rsi.append(100-(100/(1+rs)))
  return rsi[-1],closes[-1]
 except: return 50,0
def crear_grafica_pro(moneda):
 import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
 path="/tmp/pro.png"
 data=requests.get(f"https://api.exchange.coinbase.com/products/{moneda}/candles?granularity=3600",headers={"User-Agent":"Mozilla/5.0"},timeout=15).json()
 data=sorted(data,key=lambda x:x[0])[-168:]; times=[datetime.fromtimestamp(d[0]) for d in data]; closes=[float(d[4]) for d in data]
 ma7=[sum(closes[i-7:i])/7 if i>=7 else closes[i] for i in range(len(closes))]; ma25=[sum(closes[i-25:i])/25 if i>=25 else closes[i] for i in range(len(closes))]
 deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]; gains=[max(0,d) for d in deltas]; losses=[max(0,-d) for d in deltas]
 avg_g=sum(gains[:14])/14; avg_l=sum(losses[:14])/14; rsi=[50]*14
 for i in range(14,len(deltas)):
  avg_g=(avg_g*13+gains[i])/14; avg_l=(avg_l*13+losses[i])/14; rs=avg_g/(avg_l if avg_l!=0 else 0.001); rsi.append(100-(100/(1+rs)))
 plt.style.use("dark_background"); fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,7)); fig.patch.set_facecolor("#0e0e0e"); ax1.set_facecolor("#0e0e0e"); ax2.set_facecolor("#0e0e0e")
 ax1.plot(times,closes,color="#00ff88",linewidth=2,label=moneda); ax1.plot(times,ma7,color="#ffaa00",linewidth=1,label="MA7"); ax1.plot(times,ma25,color="#ff00ff",linewidth=1,label="MA25"); ax1.legend(); ax1.grid(True,alpha=0.2); ax1.set_title(f"{moneda} PRO",color="white")
 ax2.plot(times[-len(rsi):],rsi,color="#00aaff",linewidth=2); ax2.axhline(70,color="red",linestyle="--"); ax2.axhline(30,color="green",linestyle="--"); ax2.set_ylim(0,100); ax2.set_title(f"RSI {rsi[-1]:.1f}",color="white"); ax2.grid(True,alpha=0.2)
 plt.tight_layout(); plt.savefig(path,dpi=150,facecolor="#0e0e0e"); plt.close(); return path,rsi[-1]
def crear_grafica_7d():
 import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
 path="/tmp/chart.png"; plt.figure(figsize=(10,5))
 for prod,name,col in [("BTC-USD","BTC","#f7931a"),("ETH-USD","ETH","#627eea"),("XRP-USD","XRP","black")]:
  data=requests.get(f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=3600",headers={"User-Agent":"Mozilla/5.0"},timeout=15).json()
  data=sorted(data,key=lambda x:x[0])[-168:]; times=[datetime.fromtimestamp(d[0]) for d in data]; closes=[float(d[4]) for d in data]; norm=[(c/closes[0]*100)-100 for c in closes]
  plt.plot(times,norm,label=f"{name} {norm[-1]:+.2f}%",color=col,linewidth=2)
 plt.title("7 Dias %"); plt.legend(); plt.grid(True,alpha=0.3); plt.tight_layout(); plt.savefig(path,dpi=150); plt.close(); return path
async def alert_loop(app_bot):
 print("Loop V39.5 15s"); await asyncio.sleep(15)
 while True:
  try:
   data=load()
   if not data["users"]: await asyncio.sleep(60); continue
   br,_=get_rsi_for("BTC-USD"); er,_=get_rsi_for("ETH-USD"); xr,_=get_rsi_for("XRP-USD")
   print(f"RSI B{br:.1f} E{er:.1f} X{xr:.1f}")
   for uid,u in data["users"].items():
    try:
     if not u.get("alertas",True): continue
     if "ultima_alerta" not in u: u["ultima_alerta"]={}
     for mon,rv in [("BTC",br),("ETH",er),("XRP",xr)]:
      if time.time()-u["ultima_alerta"].get(mon,0) < 14400: continue
      if rv < 30:
       await app_bot.bot.send_message(chat_id=int(uid),text=f"ALERTA COMPRA {mon} RSI {rv:.1f} SOBREVENDIDO"); u["ultima_alerta"][mon]=time.time()
      elif rv > 70:
       await app_bot.bot.send_message(chat_id=int(uid),text=f"ALERTA VENTA {mon} RSI {rv:.1f} SOBRECOMPRADO"); u["ultima_alerta"][mon]=time.time()
     data["users"][uid]=u
    except Exception as e: print(f"Err u {e}")
   save(data); await asyncio.sleep(300)
  except Exception as e:
   print(f"Err loop {e}"); await asyncio.sleep(60)
def start_bot_thread():
 loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
 from telegram.ext import Application,CommandHandler,CallbackQueryHandler
 from telegram import Update
 async def st(update,context):
  d=load(); u=getu(update.effective_user.id,d); save(d)
  await update.message.reply_text(texto(u),reply_markup=kb_main(u))
 async def bt(update,context):
  q=update.callback_query; await q.answer(); d=load(); uid=str(q.from_user.id); u=getu(uid,d); b,e,x,fx=market(); pr={"btc":b,"eth":e,"xrp":x}; k=q.data
  if k=="act": await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
  if k=="toggle_alert": u["alertas"]=not u.get("alertas",True); d["users"][uid]=u; save(d); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
  if k=="menu_c": await q.edit_message_text("Que compras?",reply_markup=kb_c()); return
  if k=="menu_v": await q.edit_message_text("Que vendes?",reply_markup=kb_v()); return
  if k=="menu_sl": await q.edit_message_text(f"SL -{u['stoploss']}%",reply_markup=kb_sl()); return
  if k=="menu_tp": await q.edit_message_text(f"TP +{u['takeprofit']}%",reply_markup=kb_tp()); return
  if k=="pro": await q.edit_message_text("PRO MAX:",reply_markup=kb_pro()); return
  if k.startswith("sl_"): u["stoploss"]=float(k.split("_")[1]); d["users"][uid]=u; save(d); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
  if k.startswith("tp_"): u["takeprofit"]=float(k.split("_")[1]); d["users"][uid]=u; save(d); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
  if k.startswith("c_"):
   mon=k.split("_")[1]
   if u["efectivo"]<100: await q.edit_message_text(f"Sin efectivo\n{texto(u)}",reply_markup=kb_main(u)); return
   qty=(100/fx)/pr[mon]; u[mon]+=qty; u["efectivo"]-=100; d["users"][uid]=u; save(d); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
  if k.startswith("v_"): mon=k.split("_")[1]; mxn=u[mon]*pr[mon]*fx; u[mon]=0; u["efectivo"]+=mxn; d["users"][uid]=u; save(d); await q.edit_message_text(texto(u),reply_markup=kb_main(u)); return
  if k=="grafica":
   try:
    await q.edit_message_text("Generando 7D..."); pa=crear_grafica_7d(); f=open(pa,"rb"); await q.message.reply_photo(photo=f,caption="7D %"); f.close(); await q.message.reply_text(texto(u),reply_markup=kb_main(u))
   except Exception as e: await q.edit_message_text(f"Error: {e}\n{texto(u)}",reply_markup=kb_main(u))
   return
  if k.startswith("pro_"):
   try:
    mon=k.split("_")[1]; mapa={"btc":"BTC-USD","eth":"ETH-USD","xrp":"XRP-USD"}; await q.edit_message_text(f"Generando {mon.upper()} PRO..."); pa,rv=crear_grafica_pro(mapa[mon]); f=open(pa,"rb"); await q.message.reply_photo(photo=f,caption=f"{mon.upper()} RSI {rv:.1f}"); f.close(); await q.message.reply_text(texto(u),reply_markup=kb_main(u))
   except Exception as e: await q.edit_message_text(f"Error PRO: {e}\n{texto(u)}",reply_markup=kb_main(u))
   return
 async def main_async():
  app_bot=Application.builder().token(BOT).build()
  app_bot.add_handler(CommandHandler("start",st))
  app_bot.add_handler(CallbackQueryHandler(bt))
  # FIX ANTI-CONFLICT
  try:
   await app_bot.bot.delete_webhook(drop_pending_updates=True)
   print("Webhook borrado OK")
  except: pass
  await app_bot.initialize()
  await app_bot.start()
  # drop_pending_updates evita el Conflict
  await app_bot.updater.start_polling(drop_pending_updates=True)
  print("Bot V39.5 OK - Anti-Conflict")
  asyncio.create_task(alert_loop(app_bot))
  while True: await asyncio.sleep(3600)
 while True:
  try: loop.run_until_complete(main_async())
  except Exception as e:
   print(f"Crash {e}"); import traceback; traceback.print_exc(); time.sleep(5)
threading.Thread(target=start_bot_thread,daemon=True).start()
if __name__=="__main__":
 port=int(os.environ.get("PORT",10000))
 app.run(host="0.0.0.0",port=port)
