import os,requests,threading,time,re,io,json
from flask import Flask,request
from datetime import datetime,timedelta
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
def get_candles(sym,n=50):
 try:
  url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=10).json()
  return sorted(r)[-n:]
 except: return []
def send_text(cid,txt):
 try:
  url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
  kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['🟢 COMPRAR 100','🔴 VENDER'],['GRAF','PRO'],['🟩 AUTO ON','🟥 AUTO OFF']],'resize_keyboard':True}
  requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
 except: pass
@app.route('/')
def home(): return 'V91 OK',200
@app.route('/webhook',methods=['POST'])
def wh():
 global SEL
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d: return 'ok',200
 msg=d.get('message');cid=msg.get('chat').get('id')
 t=msg.get('text','').upper().strip()
 CONFIG['LAST_CID']=cid;save()
 if 'AUTO ON' in t: CONFIG['AUTO']=True;save();send_text(cid,'V91 🟩 AUTO ON');return 'ok',200
 if 'AUTO OFF' in t: CONFIG['AUTO']=False;save();send_text(cid,'V91 🟥 AUTO OFF');return 'ok',200
 for s in ['BTC','ETH','SOL','XRP']:
  if s in t: SEL=s
 p=price(SEL)
 if p==0 and SEL in ENTS: p=ENTS.get(SEL).get('entry')
 if 'GRAF' in t:
  from PIL import Image,ImageDraw
  candles=get_candles(SEL,50);W=900;H=520
  img=Image.new('RGB',(W,H),'#0b0e14');dr=ImageDraw.Draw(img)
  mn=mx=p
  if candles:
   lows=[c[1] for c in candles];highs=[c[2] for c in candles]
   mn=min(min(lows),p)*0.9995;mx=max(max(highs),p)*1.0005
  def yf(v): return H-70-(v-mn)/(mx-mn)*(H-110) if mx!=mn else H//2
  def xf(i): return 20+i*(W-40)//50
  if candles:
   for i,c in enumerate(candles):
    x=xf(i);col='#00ff88' if c[4]>=c[3] else '#ff4444'
    dr.line([x+3,yf(c[1]),x+3,yf(c[2])],fill=col,width=1)
    dr.rectangle([x,yf(max(c[3],c[4])),x+6,yf(min(c[3],c[4]))],fill=col)
  # HORA MEXICO UTC-6
  hora_mx=(datetime.utcnow()-timedelta(hours=6)).strftime('%I:%M %p')
  txt=SEL+' '+str(round(p,2))+' | '+hora_mx
  if SEL in ENTS:
   entry=ENTS.get(SEL).get('entry');pnl=(p/entry-1)*100
   sym_p='+' if pnl>=0 else ''
   txt+=' | '+sym_p+str(round(pnl,2))+'%'
   ye=yf(entry);dr.line([0,ye,W,ye],fill='#ffcc00',width=1)
   dr.text((W-150,ye-12),'ENT '+str(round(entry,2)),fill='#ffcc00')
  dr.text((10,10),txt,fill='white')
  bio=io.BytesIO();bio.name='g.png';img.save(bio,'PNG');bio.seek(0)
  requests.post('https://api.telegram.org/bot'+TOKEN+'/sendPhoto',data={'chat_id':cid,'caption':txt},files={'photo':bio},timeout=20)
  return 'ok',200
 if 'COMPRAR' in t:
  nums=re.findall(r'[\d\.]+',t);m=float(nums[0]) if nums else 100.0
  ENTS[SEL]={'entry':p,'chat':cid,'usd':m};save()
  send_text(cid,'COMPRADA '+SEL);return 'ok',200
 if 'VENDER' in t:
  if SEL in ENTS:
   e=ENTS.get(SEL).get('entry');pnl=(p/e-1)*100;del ENTS[SEL];save()
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
