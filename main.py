# V39.0 MAQUINA DE HACER DINERO - TELEGRAM + WEB + FIX $4369 + 8/10
import os, time, requests, threading
import yfinance as yf
from flask import Flask, request, jsonify
import telebot
from datetime import datetime
import pytz

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN') or 'PON_TU_TOKEN_AQUI'
NPOINT_ID = '455c95667066c8b158d0'
NPOINT_URL = f'https://api.npoint.io/{NPOINT_ID}'

B1=600; B2=850; RSI_BUY=42; TP=1.3; SL=18; MAX=6; RES=1500
MAP={'BTC':'BTC-USD','ETH':'ETH-USD','SOL':'SOL-USD','XAUUSD':'GC=F','NVDA':'NVDA','TSLA':'TSLA'}

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

data={'b':5000,'pos':[],'auto':True,'gan_total':0,'com_total':0}
prices={}; rsis={'BTC':38,'ETH':42,'SOL':43,'XAUUSD':40,'NVDA':52,'TSLA':51}

def ny_open():
    try:
        ny=datetime.now(pytz.timezone('America/New_York'))
        if ny.weekday()>=5: return False
        h=ny.hour+ny.minute/60.0
        return 7.5 <= h <= 14.0
    except: return False

def puede(s):
    return True if s in ['BTC','ETH','SOL','XAUUSD'] else ny_open()

def get_price(sym):
    try:
        if sym=='XAUUSD':
            try:
                p=yf.Ticker('GC=F').fast_info.last_price
                if p and p>4000: return float(p)
            except: pass
            return 4369.0
        p=yf.Ticker(MAP.get(sym,sym)).fast_info.last_price
        return float(p) if p else prices.get(sym,0)
    except: return prices.get(sym,0)

def load():
    global data
    try:
        r=requests.get(NPOINT_URL,timeout=8).json()
        data['b']=r.get('b',5000)
        data['pos']=r.get('pos',[])
        data['auto']=r.get('auto',True)
        data['gan_total']=r.get('gan_total',0)
        data['com_total']=r.get('com_total',0)
    except: pass

def save():
    try: requests.post(NPOINT_URL,json=data,timeout=8)
    except: pass

def get_estado_text():
    flot=0
    for p in data['pos']:
        pr=prices.get(p.get('sym'), p.get('entry',0))
        p['price']=pr
        entry=p.get('entry',0)
        if entry!=0:
            p['pct']=(pr-entry)/entry*100
        else: p['pct']=0
        p['flot']=p.get('amt',0)*p['pct']/100 - p.get('amt',0)*0.006
        flot+=p['flot']
    total_amt=sum([x.get('amt',0) for x in data['pos']])
    total=data['b']+total_amt+flot
    if len(data['pos'])==0: total=data['b']
    ny='ABIERTO' if ny_open() else 'CERRADO'
    auto='ON' if data['auto'] else 'OFF'
    txt=f"V39.0 MAQUINA 8/10 🔥\n💰 Total NETO ${total:.2f}\nSaldo ${data['b']:.2f}\nFlot {flot:.2f}$\nPos {len(data['pos'])}/6\nNY: {ny}\nAUTO {auto}\nHist NETO ${data.get('gan_total',0):.2f}\nhttps://telegram-bot-cijp.onrender.com"
    return txt

def trading_loop():
    while True:
        try:
            for s in ['BTC','ETH','SOL','XAUUSD','NVDA','TSLA']:
                pr=get_price(s)
                if pr==0: continue
                prices[s]=pr
                for p in list(data['pos']):
                    if p.get('sym')!=s: continue
                    entry=p.get('entry',0)
                    if entry==0: continue
                    pct=(pr-entry)/entry*100
                    if pct>=TP or pct<=-SL:
                        amt=p.get('amt',0)
                        com=amt*0.006
                        neto=amt*pct/100 - com
                        data['b']+=amt+neto
                        data['gan_total']+=neto
                        data['com_total']+=com
                        data['pos'].remove(p)
                        save()
                if not data['auto']: continue
                if len(data['pos'])>=MAX: continue
                cnt=len([x for x in data['pos'] if x.get('sym')==s])
                if cnt>=2: continue
                if data['b']-RES < B1: continue
                if rsis.get(s,50) < RSI_BUY and puede(s):
                    amt=B1 if cnt==0 else B2
                    data['pos'].append({'sym':s,'entry':pr,'price':pr,'amt':amt,'nivel':cnt+1,'pct':0,'flot':-3})
                    data['b']-=amt
                    save()
            time.sleep(5)
        except: time.sleep(5)

# --- TELEGRAM ---
@bot.message_handler(commands=['start','balance','b'])
def cmd_start(m):
    markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('BTC','ETH','SOL')
    markup.add('XAUUSD','NVDA','TSLA')
    markup.add('DASHBOARD','AUTO ON','AUTO OFF')
    bot.send_message(m.chat.id, get_estado_text(), reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.strip().upper()
    if t=='DASHBOARD' or t=='/BALANCE':
        bot.send_message(m.chat.id, get_estado_text())
    elif t in MAP:
        pr=prices.get(t, get_price(t))
        bot.send_message(m.chat.id, f"{t} ${pr:.2f} RSI {rsis.get(t,50)} NY:{'ABIERTO' if puede(t) else 'CERRADO'}")
    elif t=='AUTO ON':
        data['auto']=True; save()
        bot.send_message(m.chat.id, "AUTO ON ✅")
    elif t=='AUTO OFF':
        data['auto']=False; save()
        bot.send_message(m.chat.id, "AUTO OFF ❌")
    else:
        bot.send_message(m.chat.id, get_estado_text())

def tg_loop():
    while True:
        try: bot.polling(none_stop=True, timeout=20)
        except: time.sleep(5)

@app.route('/')
def home():
    return jsonify({'status':'V39.0 LIVE MAQUINA DE HACER DINERO','b':data['b'],'pos':data['pos'],'prices':prices,'total':data['b']+sum([x.get('amt',0) for x in data['pos']])})

@app.route('/api/estado')
def estado():
    flot=0
    for p in data['pos']:
        pr=prices.get(p.get('sym'), p.get('entry',0))
        p['price']=pr
        entry=p.get('entry',0)
        p['pct']=(pr-entry)/entry*100 if entry!=0 else 0
        p['flot']=p.get('amt',0)*p['pct']/100 - p.get('amt',0)*0.006
        flot+=p['flot']
    total=data['b']+sum([x.get('amt',0) for x in data['pos']])+flot
    if len(data['pos'])==0: total=data['b']
    return jsonify({'b':data['b'],'pos':data['pos'],'total':total,'flot':flot,'auto':data['auto'],'ny_open':ny_open(),'gan_total':data.get('gan_total',0),'com_total':data.get('com_total',0),'prices':prices,'rsis':rsis})

load()
threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=tg_loop, daemon=True).start()

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',10000)))
