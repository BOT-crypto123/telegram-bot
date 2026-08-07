import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V45 FINAL"
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
            pr = [p*0.995, p*1.002, p*0.998, p]
        last = pr[-1]
        first = pr[0]
        lo = min(pr)
        hi = max(pr)
        ch = (last/first-1)*100
        col = "#00ff88"
        if ch < 0:
            col = "#ff4444"
        dat = ""
        for i, v in enumerate(pr):
            if i > 0:
                dat += ","
            dat += str(v)
        base = "https://quickchart.io/chart?"
        base += "bkg=black&width=800&height=450&c="
        c1 = "{type:'line',data:{datasets:[{data:["
        c2 = dat + "],borderColor:'" + col + "',"
        c3 = "backgroundColor:'rgba(0,255,136,0.15)',"
        c4 = "fill:true,pointRadius:0,borderWidth:3}]},"
        c5 = "options:{legend:{display:false},"
        c6 = "scales:{yAxes:[{ticks:{fontColor:'white'}}]},"
        c7 = "title:{display:true,text:'"
        c8 = sym + " " + str(round(last,2)) + " "
        c9 = str(round(ch,2)) + "% 24h',fontColor:'white',fontSize:18}}}"
        # si es rojo cambia bg
        if ch < 0:
            c3 = "backgroundColor:'rgba(255,68,68,0.15)',"
        full = c1+c2+c3+c4+c5+c6+c7+c8+c9
        url = base + up.quote(full)
        cap = "GRAF " + sym + " " + str(round(last,2))
        cap += " " + str(round(ch,2)) + "%\n"
        cap += "L:" + str(round(lo,2)) + " H:" + str(round(hi,2))
        # si tiene partida pon ganancia
        if sym in ENTS:
            en = ENTS[sym]
            g = (last/en-1)*100
            cap += "\nENT:" + str(round(en,2)) + " G:" + str(round(g,2)) + "%"
        uu = "https://api.telegram.org/bot"
        uu += TOKEN + "/sendPhoto"
        requests.post(uu, data={"chat_id": cid, "caption": cap, "photo": url}, timeout=15)
    except Exception as e:
        print(e)
        msg(cid, "Error graf")

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
            e = ENTS.get(t,0)
            if e:
                g = (p/e-1)*100
                msg(cid, t + " E:" + str(round(e,2)) + " A:" + str(round(p,2)) + " G:" + str(round(g,2)) + "%")
            else:
                msg(cid, VERSION + " " + t + " " + str(round(p,2)))
            return "ok", 200
        ps = price(SEL)
        if "GRAF" in t:
            msg(cid, "Generando " + SEL + "...")
            chart(cid, SEL)
        elif "PRO" in t or t.startswith("/START"):
            m = VERSION + " Sel:" + SEL + " " + str(round(ps,2)) + "\n"
            for s in SYMS:
                m += s + ":" + str(round(price(s),2)) + " "
            if ENTS:
                m += "\n"
                for s, en in ENTS.items():
                    pp = price(s)
                    g = (pp/en-1)*100
                    m += s + " G:" + str(round(g,2)) + "% "
            msg(cid, m)
        elif "COMPRAR" in t:
            ENTS[SEL] = ps
            msg(cid, "PARTIDA " + SEL + " " + str(round(ps,2)))
        elif "VENDER" in t:
            if SEL in ENTS:
                en = ENTS[SEL]
                g = (ps/en-1)*100
                del ENTS[SEL]
                msg(cid, "CERRADA " + SEL + " G:" + str(round(g,2)) + "%")
            else:
                msg(cid, "Sin partida")
        return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
