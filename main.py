import os, time, io, requests, json, threading
from flask import Flask, Response, render_template_string, redirect, request
import telebot
from telebot import types
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytz
from datetime import datetime
import pandas as pd

TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
URL = os.environ.get("RENDER_EXTERNAL_URL","").strip().rstrip("/")
SYMBOLS_CG = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}
SYMBOLS_YF = {"XAUUSD":"GC=F","NVDA":"NVDA","TSLA":"TSLA"}
ALL_SYMS = ["BTC","ETH","SOL","XAUUSD","NVDA","TSLA"]

# === TU ESTRATEGIA ORIGINAL - NO TOCADA ===
CAPITAL = 5000
BOLA = [500,750,1000]
TP_PCT = 1.5
TRAIL_PCT = 3.0
RSI_BUY = 45
RSI_SELL = 70

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
TZ_MX = pytz.timezone("America/Mexico_City")

STATE_FILE="/tmp/state.json"
POS_FILE="/tmp/positions.json"

def load_json(f, default):
    try: return json.load(open(f))
    except: return default

def save_json(f, data):
    try: json.dump(data, open(f,"w"))
    except: pass

state = load_json(STATE_FILE, {"auto": False})
AUTO_ON = state.get("auto", False)
positions = load_json(POS_FILE, {}) # {BTC: {entry: 63000, qty:..., max:..., bola_idx:0}}

chart_cache={}
data_cache={"prices":{},"rsis":{},"time":0}

def rsi_calc(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean(); rs=g/l; return 100-(100/(1+rs))

def get_price_kraken(sym):
    try:
        pair={"BTC":"XXBTZUSD","ETH":"XETHZUSD","SOL":"SOLUSD"}[sym]
        r=requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}", timeout=6).json()
        k=list(r['result'].keys())[0]; return float(r['result'][k]['c'][0])
    except: return None

def get_price_cg(sym):
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={SYMBOLS_CG[sym]}&vs_currencies=usd", timeout=6).json()
        return float(r[SYMBOLS_CG[sym]]['usd'])
    except: return None

def get_history_cg(sym, days=5):
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/coins/{SYMBOLS_CG[sym]}/market_chart?vs_currency=usd&days={days}", timeout=10).json()
        df=pd.DataFrame(r['prices'], columns=['t','Close']); df['t']=pd.to_datetime(df['t'], unit='ms'); df=df.set_index('t')
        df=df.resample('15min').last().dropna(); return df
    except: return None

def get_yahoo(ticker):
    try:
        import yfinance as yf
        try:
            from curl_cffi import requests as creq
            session = creq.Session(impersonate="chrome")
            df=yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True, threads=False, session=session)
        except:
            df=yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True, threads=False)
        if len(df)>10: return df
    except Exception as e: print(f"yahoo {ticker} {e}")
    return None

def get_all_data():
    if time.time()-data_cache["time"]<20 and data_cache["prices"]: return data_cache["prices"], data_cache["rsis"]
    prices, rsis={}, {}
    for k in ["BTC","ETH","SOL"]:
        pr = get_price_kraken(k) or get_price_cg(k) or 0
        prices[k]=pr
        df=get_history_cg(k)
        rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if df is not None and len(df)>14 else 50.0
    for k in ["XAUUSD","NVDA","TSLA"]:
        df=get_yahoo(SYMBOLS_YF[k])
        if df is not None and len(df)>0:
            prices[k]=float(df['Close'].iloc[-1])
            rsis[k]=float(rsi_calc(df['Close']).iloc[-1]) if len(df)>14 else 50.0
        else:
            prices[k]=0; rsis[k]=50.0
    data_cache.update({"prices":prices,"rsis":rsis,"time":time.time()})
    return prices, rsis

def chart_bytes(sym):
    now=time.time()
    if sym in chart_cache and now-chart_cache[sym][0]<60: return chart_cache[sym][1]
    try:
        if sym in ["BTC","ETH","SOL"]: df=get_history_cg(sym)
        else: df=get_yahoo(SYMBOLS_YF[sym])
        if df is None or len(df)<30: return None
        df['RSI']=rsi_calc(df['Close']); df['SMA20']=df['Close'].rolling(20).mean(); df['SMA50']=df['Close'].rolling(50).mean()
        price=float(df['Close'].iloc[-1]); r=float(df['RSI'].iloc[-1])
        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,6),gridspec_kw={'height_ratios':[3,1]},sharex=True)
        ax1.plot(df['Close'],linewidth=2.2,label='Precio'); ax1.plot(df['SMA20'],linewidth=1,alpha=.7,label='SMA20'); ax1.plot(df['SMA50'],linewidth=1,alpha=.7,label='SMA50')
        entradas=df[df['RSI']<RSI_BUY]; ax1.scatter(entradas.index, entradas['Close'], marker='^', color='green', s=70, label=f'ENTRADA RSI<{RSI_BUY}')
        pos=positions.get(sym); if pos: ax1.axhline(pos['entry'], color='orange', ls='--', label=f"Entrada ${pos['entry']:.1f}")
        ax1.set_title(f"{sym} ${price:.2f} RSI {r:.1f} TP{TP_PCT}% Trail{TRAIL_PCT}% BOLA {BOLA}"); ax1.legend(fontsize=8); ax1.grid(True,alpha=.3)
        ax2.plot(df['RSI'],label='RSI'); ax2.axhline(RSI_BUY,color='green',ls='--'); ax2.axhline(RSI_SELL,color='red',ls='--'); ax2.grid(True,alpha=.3)
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=135,bbox_inches='tight'); plt.close(fig); buf.seek(0)
        data=buf.getvalue(); chart_cache[sym]=(now,data); return data
    except Exception as e:
        print(f"chart err {sym} {e}"); plt.close('all'); return None

# === MOTOR DE ESTRATEGIA ===
def trading_loop():
    global positions
    while True:
        try:
            if not load_json(STATE_FILE, {"auto":False}).get("auto", False):
                time.sleep(10); continue
            prices, rsis = get_all_data()
            for sym in ALL_SYMS:
                pr=prices.get(sym,0); r=rsis.get(sym,50)
                if pr==0: continue
                # VENDER
                if sym in positions:
                    entry=positions[sym]['entry']; max_p=positions[sym].get('max', pr)
                    if pr>max_p: positions[sym]['max']=pr; max_p=pr
                    profit = (pr-entry)/entry*100
                    trail_drop = (max_p-pr)/max_p*100
                    if profit>=TP_PCT or trail_drop>=TRAIL_PCT:
                        # VENDE
                        del positions[sym]; save_json(POS_FILE, positions)
                        try: bot.send_message(int(os.environ.get("CHAT_ID","0")), f"🔴 VENTA {sym} ${pr:.2f} Profit {profit:.2f}% TP{TP_PCT}% Trail{TRAIL_PCT}%")
                        except: pass
                # COMPRAR
                else:
                    if r < RSI_BUY:
                        bola = BOLA[0]
                        positions[sym]={'entry':pr, 'max':pr, 'bola':bola, 'time':str(datetime.now(TZ_MX))}
                        save_json(POS_FILE, positions)
                        try: bot.send_message(int(os.environ.get("CHAT_ID","0")), f"🟢 COMPRA {sym} ${pr:.2f} RSI {r:.1f} Bola ${bola} Cap ${CAPITAL}")
                        except: pass
            save_json(POS_FILE, positions)
        except Exception as e: print(f"loop err {e}")
        time.sleep(30)

threading.Thread(target=trading_loop, daemon=True).start()

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="20">
<style>body{background:#0d1117;color:#fff;font-family:Arial;text-align:center;padding:8px}.top{max-width:560px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;display:flex;justify-content:space-between;align-items:center}.on{background:#238636;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.off{background:#da3633;color:#fff;padding:10px 18px;border-radius:20px;border:0;font-weight:900}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:580px;margin:14px auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:12px;text-decoration:none;color:#fff;position:relative}.price{font-size:20px;font-weight:900;color:#58a6ff}.pos{position:absolute;top:6px;right:6px;background:#238636;color:#fff;font-size:10px;padding:2px 6px;border-radius:8px}</style></head><body>
<div class="top"><div><b>MAQUINA V45.5 FULL</b><br><small>Cap ${{cap}} Bola $500/750/1000 | RSI<45 TP1.5 Trail3</small></div><a href="/toggle"><button class="{{'on' if auto else 'off'}}">AUTO {{'ON' if auto else 'OFF'}}</button></a></div>
<p>{{hora}} | Kraken+CG+Yahoo | Estrategia Activa</p><div class="grid">
{% for s in syms %}<a class="card" href="/chart/{{s}}">{% if s in positions %}<span class="pos">EN POS</span>{% endif %}<h2>{{s}}</h2><div class="price">${{prices[s]}}</div><div>RSI {{rsis[s]}}</div>{% if s in positions %}<small>Ent ${{positions[s].entry}}</small>{% endif %}</a>{% endfor %}
</div><small>Toca tarjeta = grafica viva SMA20/50 + Entradas RSI<45</small></body></html>"""

@app.route('/')
def home():
    pr,rs=get_all_data(); pos=load_json(POS_FILE, {})
    return render_template_string(HTML, syms=ALL_SYMS, auto=load_json(STATE_FILE,{"auto":False}).get("auto",False), hora=datetime.now(TZ_MX).strftime("%H:%M:%S"),
        cap=CAPITAL, positions=pos,
        prices={k:f"{v:.2f}" if v>0 else "CARGANDO" for k,v in pr.items()}, rsis={k:f"{v:.1f}" for k,v in rs.items()})

@app.route('/toggle')
def tog():
    s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s); return redirect('/')
@app.route('/chart/<sym>')
def ch(sym): d=chart_bytes(sym.upper()); return Response(d,mimetype='image/png') if d else ("Generando grafica 10s...",503)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string=request.get_data().decode('utf-8'); update=telebot.types.Update.de_json(json_string); bot.process_new_updates([update]); return ''

@bot.message_handler(commands=['start','balance'])
def start(m):
    pos=load_json(POS_FILE,{}); auto=load_json(STATE_FILE,{"auto":False}).get("auto",False)
    txt=f"✅ V45.5 FULL CON ESTRATEGIA\n{'🟢AUTO ON' if auto else '🔴AUTO OFF'} Cap ${CAPITAL}\nBola {BOLA} TP{TP_PCT}% Trail{TRAIL_PCT}% RSI<{RSI_BUY}\nPosiciones: {len(pos)}\n{URL}"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=3); kb.add("BTC","ETH","SOL","XAUUSD","NVDA","TSLA"); kb.add(f"AUTO {'ON' if auto else 'OFF'}","DASHBOARD")
    bot.send_message(m.chat.id, txt, reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def allh(m):
    t=m.text.upper().strip()
    if "AUTO" in t:
        s=load_json(STATE_FILE,{"auto":False}); s["auto"]=not s["auto"]; save_json(STATE_FILE,s)
        bot.send_message(m.chat.id,f"{'🟢AUTO ON - estrategia comprando solo RSI<45' if s['auto'] else '🔴AUTO OFF'}"); start(m); return
    if t=="DASHBOARD": bot.send_message(m.chat.id, URL); return
    if t in ALL_SYMS:
        d=chart_bytes(t); pr,rs=get_all_data()
        bot.send_photo(m.chat.id,d,caption=f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} TP{TP_PCT}% Trail{TRAIL_PCT}%") if d else bot.send_message(m.chat.id,f"{t} ${pr.get(t,0):.2f} RSI {rs.get(t,0):.1f} (grafica en 10s)")

try:
    if URL: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{URL}/{TOKEN}"); print("WEBHOOK V45.5 FULL OK")
except Exception as e: print(e)

app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
