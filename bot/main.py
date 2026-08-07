import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V41.3 4COINS GRAF LITE"
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","XRP"]
ENTRIES = {}
CHAT_ID_SAVED = None
SELECTED = "BTC"

def get_price(sym="BTC"):
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except:
        try:
            ids = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
            cid = ids.get(sym,"bitcoin")
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd", timeout=5).json()
            return float(r[cid]["usd"])
        except:
            return 0.0

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    kb = {"keyboard": [["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]], "resize_keyboard": True}
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=10)
    except:
        pass

def send_chart(chat_id, symbol):
    try:
        # Usa coingecko para datos y quickchart para grafica negra
        ids = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
        cid = ids.get(symbol,"bitcoin")
        data = requests.get(f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=1", timeout=10).json()
        prices = [p[1] for p in data["prices"]][-50:]
        # Grafica negra con QuickChart
        chart_url = f"https://quickchart.io/chart?c={{type:'line',data:{{labels:{list(range(len(prices)))},datasets:[{{data:{prices},borderColor:'#00ff88',backgroundColor:'rgba(0,255,136,0.1)',fill:true}}]}},options:{{legend:{{display:false}},scales:{{xAxes:[{{display:false}}],yAxes:[{{ticks:{{fontColor:'#fff'}}}}]}},title:{{display:true,text:'{symbol} 24h {round(prices[-1],4)}',fontColor:'#fff'}},plugins:{{backgroundImageUrl:''}}}}}}&backgroundColor=black&width=600&height=300"
        # Manda como foto directa de coingecko chart
        img_url = f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=1" # fallback
        # Intentamos mandar quickchart
        urlp = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        requests.post(urlp, data={"chat_id": chat_id, "caption": f"GRAFICA {symbol} {round(prices[-1],4)} USD NEGRA", "photo": chart_url}, timeout=15)
    except Exception as e:
        print(e)
        # fallback envia tradingview link
        send_msg(chat_id, f"Grafica {symbol}: https://www.tradingview.com/symbols/{symbol}USD/")

def monitor():
    while True:
        time.sleep(300)
        if CHAT_ID_SAVED and ENTRIES:
            for sym, entry in list(ENTRIES.items()):
                try:
                    p = get_price(sym)
                    if p==0: continue
                    if p <= entry*0.95:
                        send_msg(CHAT_ID_SAVED, f"SL {sym} E:{round(entry,4)} A:{round(p,4)}")
                    if p >= entry*1.10:
                        send_msg(CHAT_ID_SAVED, f"TP {sym} E:{round(entry,4)} A:{round(p,4)}")
                except:
                    pass

threading.Thread(target=monitor, daemon=True).start()

@app.route("/")
def home():
    return f"{VERSION} ON", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    global CHAT_ID_SAVED, SELECTED
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return "ok",200
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            CHAT_ID_SAVED = chat_id
            txt = data["message"].get("text","").upper().strip()
            if txt in SYMBOLS:
                SELECTED = txt
                p = get_price(txt)
                e = ENTRIES.get(txt)
                if e:
                    send_msg(chat_id, f"{VERSION} {txt} E:{round(e,4)} A:{round(p,4)} G:{round((p/e-1)*100,2)}%")
                else:
                    send_msg(chat_id, f"{VERSION} {txt} {round(p,4)} Sin partida")
                return "ok",200
            ps = get_price(SELECTED)
            if "GRAF" in txt:
                send_chart(chat_id, SELECTED)
            elif "PRO" in txt or "/START" in txt:
                if not ENTRIES:
                    msg = f"{VERSION} Sel:{SELECTED} {round(ps,4)}\n"
                    for s in SYMBOLS:
                        msg += f"{s}:{round(get_price(s),4)} "
                    send_msg(chat_id, msg)
                else:
                    msg = f"{VERSION} PORTAFOLIO:\n"
                    for s, en in ENTRIES.items():
                        p = get_price(s)
                        msg += f"\n{s} E:{round(en,4)} A:{round(p,4)} G:{round((p/en-1)*100,2)}%"
                    send_msg(chat_id, msg)
            elif "COMPRAR" in txt:
                ENTRIES[SELECTED] = ps
                send_msg(chat_id, f"PARTIDA {SELECTED} {round(ps,4)}")
            elif "VENDER" in txt:
                if SELECTED in ENTRIES:
                    e = ENTRIES[SELECTED]
                    p = get_price(SELECTED)
                    del ENTRIES[SELECTED]
                    send_msg(chat_id, f"CERRADA {SELECTED} G:{round((p/e-1)*100,2)}%")
                else:
                    send_msg(chat_id, f"Sin partida {SELECTED}")
        return "ok",200
    except:
        return "ok",200

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
