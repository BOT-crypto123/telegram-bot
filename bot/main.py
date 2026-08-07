import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = ""

VERSION = "V42 4COINS GRAF"
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
        p = price(sym)
        # url corta, sin partir
        base = "https://quickchart.io/chart?"
        base += "bkg=black&width=600&height=300&c="
        c = "{type:'line',data:{datasets:[{data:[1,2,3,2,4],borderColor:'#00ff88'}]}}"
        import urllib.parse as up
        url = base + up.quote(c)
        # precio real para caption
        cap = "GRAF " + sym + " " + str(round(p,2))
        u = "https://api.telegram.org/bot" + TOKEN + "/sendPhoto"
        requests.post(u, data={"chat_id": cid, "caption": cap, "photo": url}, timeout=10)
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
            msg(cid, VERSION + " " + t + " " + str(round(p,2)))
            return "ok", 200
        ps = price(SEL)
        if "GRAF" in t:
            msg(cid, "Generando " + SEL + "...")
            chart(cid, SEL)
        elif "PRO" in t or t.startswith("/START"):
            m = VERSION + " Sel:" + SEL
            m += " " + str(round(ps,2)) + "\n"
            for s in SYMS:
                m += s + ":" + str(round(price(s),2)) + " "
            if ENTS:
                for s, en in ENTS.items():
                    pp = price(s)
                    g = round((pp/en-1)*100,2)
                    m += "\n" + s + " G:" + str(g) + "%"
            msg(cid, m)
        elif "COMPRAR" in t:
            ENTS[SEL] = ps
            msg(cid, "PARTIDA " + SEL + " " + str(round(ps,2)))
        elif "VENDER" in t:
            if SEL in ENTS:
                del ENTS[SEL]
                msg(cid, "CERRADA " + SEL)
            else:
                msg(cid, "Sin partida " + SEL)
        return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
