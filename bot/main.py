import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V44.2 GRAF COINBASE"
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
        # coinbase candles reales
        u = "https://api.exchange.coinbase.com/"
        u += "products/" + sym + "-USD/candles"
        u += "?granularity=1800"
        r = requests.get(u, timeout=10, headers={"User-Agent":"bot"})
        d = r.json()
        pr = []
        # d viene al reves
        d = d[::-1]
        for x in d[-48:]:
            pr.append(float(x[4]))
        if len(pr) < 5:
            pr = [price(sym)-10, price(sym)-5, price(sym), price(sym)+5, price(sym)+2]
        last = round(pr[-1], 2)
        dat = ""
        for i, v in enumerate(pr):
            if i > 0:
                dat += ","
            dat += str(round(v, 2))
        base = "https://quickchart.io/chart?"
        base += "bkg=black&width=800&height=400&c="
        c1 = "{type:'line',data:{datasets:[{data:["
        c2 = dat + "],borderColor:'#00ff88',"
        c3 = "backgroundColor:'rgba(0,255,136,0.15)',"
        c4 = "fill:true,pointRadius:0,borderWidth:2}]},"
        c5 = "options:{legend:{display:false},"
        c6 = "scales:{yAxes:[{ticks:{fontColor:'white'}}]},"
        c7 = "title:{display:true,text:'"
        c8 = sym + " " + str(last) + " 24h',"
        c9 = "fontColor:'white',fontSize:16}}}"
        full = c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8 + c9
        url = base + up.quote(full)
        cap = "GRAF REAL " + sym + " " + str(last)
        uu = "https://api.telegram.org/bot"
        uu += TOKEN + "/sendPhoto"
        requests.post(uu, data={"chat_id": cid, "caption": cap, "photo": url}, timeout=15)
    except Exception as e:
        print(e)
        msg(cid, "Error graf: " + str(e)[:100])

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
        if not data:
            return "ok", 200
        if "message" not in data:
            return "ok", 200
        cid = data["message"]["chat"]["id"]
        CHAT = cid
        t = data["message"].get("text", "")
        t = t.upper().strip()
        if t in SYMS:
            SEL = t
            p = price(t)
            msg(cid, VERSION + " " + t + " " + str(p))
            return "ok", 200
        ps = price(SEL)
        if "GRAF" in t:
            msg(cid, "Generando " + SEL + " vol real...")
            chart(cid, SEL)
        elif "PRO" in t or t.startswith("/START"):
            m = VERSION + " " + SEL + " "
            m += str(round(ps, 2)) + "\n"
            for s in SYMS:
                m += s + ":" + str(round(price(s), 2)) + " "
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
