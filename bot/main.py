import os,requests,threading,time,re,io,json
from flask import Flask,request
TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot89.json'
CONFIG={'AUTO':False,'LAST_CID':0}
def load():
 try:
  if os.path.exists(FILE):
   with open(FILE,'r') as f:
    d=json.load(f)
    ENTS.update(d.get('ENTS',{}))
    CONFIG.update(d.get('CONFIG',{}))
 except: pass
def save():
 try:
  with open(FILE,'w') as f: json.dump({'ENTS':ENTS,'CONFIG':CONFIG},f)
 except: pass
load()
def price(s):
 try:
  r=requests.get('https://api.coinbase.com/v2/prices/'+s+'-USD/spot',timeout=8).json()
  return float(r['data']['amount'])
 except: return 0
def get_candles(sym,gran=60,n=50):
 try:
  url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity='+str(gran)
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=10).json()
  return sorted(r)[-n:]
 except: return []
def send_text(cid,txt):
 try:
  url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
  kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO'],['AUTO ON','AUTO OFF']],'resize_keyboard':True}
  requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
 except: pass
def checker():
 while True:
  try:
   time.sleep(60)
   for sym in list(ENTS.keys()):
    p=price(sym)
    if p.__lt__(1): continue
    v=ENTS.get(sym)
    if not v: continue
    entry=v.get('entry');pnl=(p/entry-1)*100;cid=v.get('chat')
    if CONFIG.get('AUTO'):
     if pnl.__le__(-2.0): del ENTS[sym];save();send_text(cid,'V89 SL '+sym+' '+str(round(pnl,2))+'%')
     elif pnl.__ge__(2.2): del ENTS[sym];save();send_text(cid,'V89 TP '+sym+' '+str(round(pnl,2))+'%')
  except: time.sleep(10)
threading.Thread(target=checker,daemon=True).start()
@app.route('/')
def home(): return 'V90 OK',200
@app.route('/webhook',methods=['POST'])
def wh():
 global SEL
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d: return 'ok',200
 msg=d.get('message');cid=msg.get('chat').get('id')
 t=msg.get('text','').upper().strip()
 CONFIG['LAST_CID']=cid;save()
 if 'AUTO ON' in t: CONFIG['AUTO']=True;save();send_text(cid,'V90 AUTO ON');return 'ok',200
 if 'AUTO OFF' in t: CONFIG['AUTO']=False;save();send_text(cid,'V90 AUTO OFF');return 'ok',200
 for s in ['BTC','ETH','SOL','XRP']:
  if s in t: SEL=s
 p=price(SEL)
 if p==0 and SEL in ENTS: p=ENTS.get(SEL).get('entry')
 if 'GRAF' in t:
  from PIL import Image,ImageDraw
  from datetime import datetime
  candles=get_candles(SEL,60,50);W=900;H=520
  img=Image.new('RGB',(W,H),'#0b0e14');dr=ImageDraw.Draw(img)
  mn=mx=p
  if candles:
   lows=[c[1] for c in candles];highs=[c[2] for c in candles]
   mn=min(min(lows),p)*0.9995;mx=max(max(highs),p)*1.0005
  def yf(v): return H-70-(v-mn)/(mx-mn)*(H-110) if mx!=mn else H//2
  def xf(i): return 20+i*(W-40)//50
  if candles:
   for i,c in enumerate(candles):
    x=xf(i);col='#00ff88' if c[4].__ge__(c[3]) else '#ff4444'
    dr.line([x+3,yf(c[1]),x+3,yf(c[2])],fill=col,width=1)
    dr.rectangle([x,yf(max(c[3],c[4])),x+6,yf(min(c[3],c[4]))],fill=col)
  hora=datetime.now().strftime('%I:%M %p')
  txt=SEL+' '+str(round(p,2))+' | '+hora
  if SEL in ENTS:
   entry=ENTS.get(SEL).get('entry');pnl=(p/entry-1)*100
   sym_p='+' if pnl.__ge__(0) else ''
   txt+=' | '+sym_p+str(round(pnl,2))+'%'
   # linea de entrada
   ye=yf(entry);dr.line([0,ye,W,ye],fill='#ffcc00',width=1)
   dr.text((W-150,ye-12),'ENT '+str(round(entry,2)),fill='#ffcc00')
  dr.text((10,10),txt,fill='white')
  bio=io.BytesIO();bio.name='g.png';img.save(bio,'PNG');bio.seek(0)
  requests.post('https://api.telegram.org/bot'+TOKEN+'/sendPhoto',data={'chat_id':cid,'caption':txt},files={'photo':bio},timeout=20)
  return 'ok',200
 if 'COMPRAR' in t:
  nums=re.findall(r'[\d\.]+',t);m=float(nums[0]) if nums else 100.0
  ENTS[SEL]={'entry':p,'chat':cid,'usd':m};save()
  send_text(cid,'COMPRADA '+SEL+' '+str(round(p,2)));return 'ok',200
 if 'VENDER' in t:
  if SEL in ENTS:
   entry=ENTS.get(SEL).get('entry');pnl=(p/entry-1)*100
   del ENTS[SEL];save()
   send_text(cid,'CERRADA '+SEL+' '+str(round(pnl,2))+'%')
  else: send_text(cid,'Sin partida '+SEL)
  return 'ok',200
 if 'PRO' in t:
  if not ENTS: send_text(cid,'Sin partidas')
  else:
   out=''
   for k,v in ENTS.items():
    pp=price(k) or v.get('entry');pnl=(pp/v.get('entry')-1)*100
    out+=k+' '+str(round(pnl,2))+'% | '
   send_text(cid,out)
  return 'ok',200
 send_text(cid,SEL+' '+str(round(p,4)))
 return 'ok',200
if __name__=='__main__':
 app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
