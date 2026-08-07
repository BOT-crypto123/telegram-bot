import os, requests, time, threading, re
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V46.1 FIX"
app = Flask(__name__)

SYMS = ["BTC","ETH","SOL","XRP"]
ENTS = {}
CHAT = None
SEL = "BTC"
SL_PCT = 5.0
TP_PCT = 10.0

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
        url = "https://api.exchange.coinbase.com/products/" + sym + "-USD/candles?granularity=300"
        d = requests.get(url, timeout=10, headers={"User-Agent":"bot"}).json()
        if not isinstance(d, list):
            d = []
        pr = []
        rev = list(reversed(d))
        n = len(rev)
        s = 0
        if n > 80:
            s = n - 80
        for i in range(s, n):
            try:
                pr.append(float(rev[i][4]))
            except:
                pass
        if len(pr) < 5:
            p = price(sym)
            pr = [p*0.995, p*1.002, p*0.998, p]

        last = pr[-1]
        lo = min(pr)
        hi = max(pr)
        ch = (last/pr[0]-1)*100
        col = "#00ff88"
        if ch < 0:
            col = "#ff4444"
        bg = "rgba(0,255,136,0.15)"
        if ch < 0:
            bg = "rgba(255,68,68,0.15)"

        data_str = ""
        for i, v in enumerate(pr):
            if i > 0:
                data_str += ","
            data_str += str(v)

        chart_cfg = "{type:'line',data:{datasets:[{data:[" + data_str + "],borderColor:'" + col + "',backgroundColor:'" + bg + "',fill:true,pointRadius:0,borderWidth:3}]},options:{legend:{display:false},scales:{yAxes:[{ticks:{fontColor:'white'}}]},title:{display:true,text:'" + sym + " " + str(round(last,2)) + " " + str(round(ch,2)) + "%',fontColor:'white',fontSize:18}}}"

        qurl = "https://quickchart.io/chart?bkg=black&width=800&height=450&c=" + up.quote(chart_cfg)

        cap = "GRAF " + sym + " " + str(round(last,2)) + " " + str(round(ch,2)) + "% L:" + str(round(lo,2)) + " H:" + str(round(hi,2))
        if sym in ENTS:
            en = ENTS[sym]
            g
