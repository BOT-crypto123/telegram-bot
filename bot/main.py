import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V43 GRAF REAL"
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
        # mapa ids
        m = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
        coin = m.get(sym, "bitcoin")
        # url corta armada
        u1 = "https://api.coingecko.com/api/v3/"
        u2 = "coins/" + coin + "/market_chart"
        u3 = "?vs_currency=usd&days=1"
        u = u1 + u2 + u3
        d = requests.get(u, timeout=10).json()
        pr = [x[1] for x in d["prices"]][-40:]
        last = round(pr[-1], 2)
        # arma datos
        import urllib.parse as up
        dat = ",".join(str(round(x,2)) for x in pr)
        base = "https://quickchart.io/chart?"
        base += "bkg=black&width=600&height=300&c="
        cfg1 = "{type:'line',data:{datasets:[{"
        cfg2 = "data:[" + dat + "],"
        cfg3 = "borderColor:'#00ff88',"
        cfg4 = "backgroundColor:'rgba(0,255,136,0.1)',"
        cfg5 = "fill:true,pointRadius:0,borderWidth:2}]},"
        cfg6 = "options:{legend:{display:false},"
        cfg7 = "title:{display:true,text:'"
        cfg8 = sym + " " + str(last) + "',"
        cfg9 = "fontColor:'white'}}}"
        full = cfg1+cfg2+cfg3+cfg4+cfg5+cfg6+cfg7+cfg8+cfg9
        url = base + up.quote(full)
        cap = "GRAF REAL " + sym + " " + str(last)
        uu = "https://api.telegram.org/bot"
        uu += TOKEN + "/sendPhoto"
        requests.post(uu, data={"chat_id": cid, "caption": cap, "photo": url}, timeout=15)
    except Exception as e:
        print(e)
        # fallback dummy
        try:
            p = price(sym)
            base = "https://quickchart.io/chart?"
            base += "bkg=black&width=600&height=300&c="
            c = "{type:'line',data:{datasets:[{data:[1,2,3],borderColor:'green'}]}}"
            import urllib.parse as up
            url = base + up.quote(c)
            uu = "https://api.telegram.org/bot" + TOKEN + "/sendPhoto"
            requests.post(uu, data={"chat_id": cid, "caption": "GRAF " + sym + " " + str(p), "photo": url}, timeout=10)
        except:
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
                    msg(CHAT, "SL " + s + " " + str(round(p,2)))
                if p >= en * 1.10:
                    msg(CHAT, "TP " + s + " " + str(round(p,2)))

threading.Thread(target=mon, daemon=True).start()

@app.route("/")
def home():
    return VERSION + " ON", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    global CHAT, SEL
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return "ok", 200
        if "message" not in data:
            return "ok", 200
        cid = data["message"]["chat"]["id"]
        CHAT = cid
        t = data["message"].get("text","").upper().strip()
        if t in SYMS:
            SEL = t
            p = price(t)
            e = ENTS.get(t, 0)
            if e:
                g = round((p/e-1)*100,2)
                msg(cid, VERSION + " " + t + " E:" + str(round(e,2)) + " A:" + str(round(p,2)) + " G:" + str(g) + "%")
            else:
                msg(cid, VERSION + " " + t + " " + str(round(p,2)) + " Sin partida")
            return "ok", 200
        ps = price(SEL)
        if "GRAF" in t:
            msg(cid, "Generando " + SEL + " real...")
            chart(cid, SEL)
        elif "PRO" in t or t.startswith("/START"):
            m = VERSION + " Sel:" + SEL + " " + str(round(ps,2)) + "\n"
            for s in SYMS:
                m += s + ":" + str(round(price(s),2)) + " "
            if ENTS:
                m += "\n"
                for s, en in ENTS.items():
                    pp = price(s)
                    g = round((pp/en-1)*100,2)
                    m += "\n" + s + " E:" + str(round(en,2)) + " G:" + str(g) + "%"
            msg(cid, m)
        elif "COMPRAR" in t:
            ENTS[SEL] = ps
            msg(cid, "PARTIDA " + SEL + " " + str(round(ps,2)))
        elif "VENDER" in t:
            if SEL in ENTS:
                en = ENTS[SEL]
                pp = price(SEL)
                g = round((pp/en-1)*100,2)
                del ENTS[SEL]
                msg(cid, "CERRADA " + SEL + " G:" + str(g) + "%")
            else:
                msg(cid, "Sin partida " + SEL)
        return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
