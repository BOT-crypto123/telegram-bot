import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V44 GRAF VOLATIL"
app = Flask(__name__)

SYMS = ["BTC","ETH","SOL","XRP"]
ENTS = {}
CHAT = None
SEL = "BTC"

def price(sym):
    try:
        u = "https://api.coinbase.com/v2/"
        u += "prices/" + sym + "-USD/spot"
        r = requests.get(u, timeout=5).json()
        return float(r["data"]["amount"])
    except:
        return 0.0

def msg(cid, txt):
    u = "https://api.telegram.org/bot"
    u += TOKEN + "/sendMessage"
    kb = {"keyboard": [["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]], "resize_keyboard": True}
    try:
        requests.post(u, json={"chat_id": cid, "text": txt, "reply_markup": kb}, timeout=10)
    except:
        pass

def chart(cid, sym):
    try:
        import urllib.parse as up
        # binance klines reales 24h
        bsym = sym + "USDT"
        u1 = "https://api.binance.com/api/v3/"
        u2 = "klines?symbol=" + bsym
        u3 = "&interval=30m&limit=48"
        u = u1 + u2 + u3
        d = requests.get(u, timeout=10).json()
        pr = [float(x[4]) for x in d]
        if not pr:
            pr = [price(sym)]
        last = round(pr[-1], 4)
        lo = min(pr)
        hi = max(pr)
        # si la moneda es estable, amplifica variacion para que se vea
        dat = ",".join(str(round(x,4)) for x in pr)
        base = "https://quickchart.io/chart?"
        base += "bkg=black&width=800&height=400&c="
        cfg1 = "{type:'line',data:{labels:["
        labs = ",".join(["''"]*len(pr))
        cfg1a = labs + "],datasets:[{data:["
        cfg2 = dat + "],borderColor:'#00ff88',"
        cfg3 = "backgroundColor:'rgba(0,255,136,0.15)',"
        cfg4 = "fill:true,pointRadius:0,borderWidth:2}]},"
        cfg5 = "options:{legend:{display:false},"
        cfg6 = "scales:{yAxes:[{ticks:{fontColor:'white'}}],"
        cfg7 = "xAxes:[{display:false}]},"
        cfg8 = "title:{display:true,text:'"
        cfg9 = sym + " " + str(last) + " 24h',"
        cfg10 = "fontColor:'white',fontSize:18}}}"
        full = cfg1+cfg1a+cfg2+cfg3+cfg4+cfg5+cfg6+cfg7+cfg8+cfg9+cfg10
        url = base + up.quote(full)
        cap = "GRAF REAL " + sym + " " + str(last)
        cap += " L:" + str(round(lo,4))
        cap += " H:" + str(round(hi,4))
        uu = "https://api.telegram.org/bot"
        uu += TOKEN + "/sendPhoto"
        requests.post(uu, data={"chat_id": cid, "caption": cap, "photo": url}, timeout=15)
    except Exception as e:
        print(e)
        msg(cid, "Error graf " + str(e)[:50])

def mon():
    while True:
        time.sleep(300)
        if CHAT and ENTS:
            for s, en in list(ENTS.items()):
                p = price(s)
                if p == 0:
                    continue
                if p <= en * 0.95:
                    msg(CHAT, "SL " + s)
                if p >= en * 1.10:
                    msg(CHAT, "TP " + s)

threading.Thread(target=mon, daemon=True).start()

@app.route
