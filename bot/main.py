import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V44.4 ZOOM REAL"
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
    kb = {}
    kb["keyboard"] = [["BTC","ETH"],["SOL","XRP"]]
    kb["keyboard"] += [["COMPRAR","VENDER"]]
    kb["keyboard"] += [["GRAF","PRO"]]
    kb["resize_keyboard"] = True
    try:
        requests.post(u, json={"chat_id": cid, "text": txt, "reply_markup": kb}, timeout=10)
    except:
        pass

def chart(cid, sym):
    try:
        import urllib.parse as up
        # 5 min = 300 seg = mucho mas vol
        u = "https://api.exchange.coinbase.com/"
        u += "products/" + sym + "-USD/candles"
        u += "?granularity=300"
        r = requests.get(u, timeout=10, headers={"User-Agent":"bot"})
        d = r.json()
        if not isinstance(d, list):
            d = []
        pr = []
        d2 = list(reversed(d))
        cnt = len(d2)
        start = 0
        if cnt > 80:
            start = cnt - 80
        for i in range(start, cnt):
            try:
                pr.append(float(d2[i][4]))
            except:
                pass
        if len(pr) < 5:
            p = price(sym)
            pr = [p*0.995, p*1.002, p*0.998, p*1.003, p]
        last = pr[-1]
        # zoom auto: usa min/max real
        lo = min(pr)
        hi = max(pr)
        dat = ""
        for i, v in enumerate(pr):
            if i > 0:
                dat += ","
            dat += str(v)
        base = "https://quickchart.io/chart?"
        base += "bkg=black&width=800&height=450&c="
        c1 = "{type:'line',data:{datasets:[{data:["
        c2 = dat + "],borderColor:'#00ff88',"
        c3 = "backgroundColor:'rgba(0,255,136,0.2)',"
        c4 = "fill:true,pointRadius:0,borderWidth:3}]},"
        c5 = "options:{legend:{display:false},"
        c6 = "scales:{yAxes:[{ticks:{fontColor:'white',"
        c7 = "fontSize:12},gridLines:{color:'rgba(255,255,255,0.1)'}}],"
        c8 = "xAxes:[{display:false}]},"
        c9 = "title:{display:true,text:'"
        c10 = sym + " " + str(round(last,4)) + " 24h ZOOM',"
        c11 = "fontColor:'white',fontSize:18}}}"
        full = c1+c2+c3+c4+c5+c6+c7+c8+c9+c10+c11
        url = base + up.quote(full)
        cap = "GRAF ZOOM " + sym + " " + str(round(last,4))
        cap += " L:" + str(round(lo,4)) + " H:" + str(round(hi,4))
        uu = "https://api.telegram.org/bot"
        uu += TOKEN + "/sendPhoto"
        requests.post(uu, data={"chat_id": cid, "caption": cap, "photo": url}, timeout=15)
    except Exception as e:
        print(e)
        msg(cid, "Error: " + str(e)[:100])

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

@app.route("/")
def home():
    return VERSION + " ON", 200

@app.route("/webhook", methods=["POST"])
def wh():
    global CHAT, SEL
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data:
            return "ok", 200
        cid = data["message"]["chat"]["id"]
        CHAT = cid
        t = data["message"].get("text","")
        t = t.upper().strip()
        if t in SYMS:
            SEL = t
            p = price(t)
            msg(cid, VERSION + " " + t + " " + str(p))
            return "ok", 200
        ps = price(SEL)
        if "GRAF" in t:
            msg(cid, "Generando " + SEL + " zoom...")
            chart(cid, SEL)
        elif "PRO" in t or t.startswith("/START"):
            m = VERSION + " " + SEL + " "
            m += str(round(ps,2)) + "\n"
            for s in SYMS:
                m += s + ":" + str(round(price(s),2)) + " "
            msg(cid, m)
        elif "COMPRAR" in t:
            ENTS[SEL] = ps
            msg(cid, "PARTIDA " + SEL)
        elif "VENDER" in t:
            if SEL in ENTS:
                del ENTS[SEL]
                msg(cid, "CERRADA " + SEL)
            else:
                msg(cid, "Sin partida")
        return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
