import os, requests, time, threading, re
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V46 SLTP %"
app = Flask(__name__)

SYMS = ["BTC","ETH","SOL","XRP"]
ENTS = {}
CHAT = None
SEL = "BTC"
SL_PCT = 5.0 # default -5%
TP_PCT = 10.0 # default +10%

def price(sym):
    try:
        u = "https://api.coinbase.com/v2/prices/" + sym + "-USD/spot"
        r = requests.get(u, timeout=5).json()
        return float(r["data"]["amount"])
    except:
        return 0.0

def msg(cid, txt):
    u = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]], "resize_keyboard":True}
    try:
        requests.post(u, json={"chat_id":cid, "text":txt, "reply_markup":kb}, timeout=10)
    except:
        pass

def chart(cid, sym):
    try:
        import urllib.parse as up
        u = "https://api.exchange.coinbase.com/products/" + sym + "-USD/candles?granularity=300"
        r = requests.get(u, timeout=10, headers={"User-Agent":"bot"}).json()
        if not isinstance(r, list):
            r = []
        pr = []
        d2 = list(reversed(r))
        cnt = len(d2)
        st = max(0, cnt-80)
        for i in range(st, cnt):
            try:
                pr.append(float(d2[i][4]))
            except:
                pass
        if len(pr) < 5:
            p = price(sym)
            pr = [p*0.995, p*1.002, p*0.998, p]
        last = pr[-1]
        first = pr[0]
        lo = min(pr)
        hi = max(pr)
        ch = (last/first-1)*100
        col = "#00ff88" if ch >=0 else "#ff4444"
        bg = "rgba(0,255,136,0.15)" if ch>=0 else "rgba(255,68,68,0.15)"
        dat = ",".join([str(v) for v in pr])
        base = "https://quickchart.io/chart?bkg=black&width=800&height=450&c="
        cfg = "{type:'line',data:{datasets:[{data:[" + dat + "],borderColor:'" + col + "',backgroundColor:'" + bg + "',fill:true,pointRadius:0,borderWidth:3}]},options:{legend:{display:false},scales:{yAxes:[{ticks:{fontColor:'white'}}]},title:{display:true,text:'" + sym + " " + str(round(last,2)) + " " + str(round(ch,2)) + "% 24h',fontColor:'white',fontSize:18}}}"
        url = base + up.quote(cfg)
        cap = "GRAF " + sym + " " + str(round(last,2)) + " " + str(round(ch,2)) + "%\nL:" + str(round(lo,2)) + " H:" + str(round(hi,2))
        if sym in ENTS:
            en = ENTS[sym]
            g = (last/en-1)*100
            cap += "\nENT:" + str(round(en,2)) + " G:" + str(round(g,2)) + "%"
        cap += "\nSL:-" + str(SL_PCT) + "% TP:+" + str(TP_PCT) + "%"
        uu = "https://api.telegram.org/bot" + TOKEN + "/sendPhoto"
        requests.post(uu, data={"chat_id":cid, "caption":cap, "photo":url}, timeout=15
