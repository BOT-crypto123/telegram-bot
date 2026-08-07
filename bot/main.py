import os, requests, time, threading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, request
from io import BytesIO

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V41.2 4COINS GRAF"
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","XRP"]
ENTRIES = {}
CHAT_ID_SAVED = None
SELECTED = "BTC"

def get_price(sym="BTC"):
    sym = sym.upper()
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except:
        pass
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
        ids = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
        cid = ids.get(symbol,"bitcoin")
        data = requests.get(f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=1", timeout=10).json()
        prices = data["prices"]
        y = [p[1] for p in prices][-120:]
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(y, color='#00ff88', linewidth=2)
        ax.set_title(f"{symbol} 24h", color='white')
        ax.set_facecolor('black')
        fig.patch.set_facecolor('black')
        ax.grid(color='#333333', linestyle='--', alpha=0.3)
        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()
        urlp = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        requests.post(urlp, data={"chat_id": chat_id, "caption": f"GRAFICA NEGRA {symbol} {round(y[-1],4)}"}, files={"photo": ("graf.png", buf, "image/png")}, timeout=15)
    except Exception as e:
        print(e)
        send_msg(chat_id, f"Error graf {symbol}")

def monitor():
    while True:
        time.sleep(300)
        if CHAT_ID_SAVED and ENTRIES:
            for sym, entry in list(ENTRIES.items()):
                try:
                    p = get_price(sym)
                    if p == 0:
                        continue
                    if p <= entry * 0.95:
                        send_msg(CHAT_ID_SAVED, f"SL {sym} E:{round(entry,4)} A:{round(p,4)}")
                    if p >= entry * 1.10:
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
                    gan = (p/e-1)*100
                    send_msg(chat_id, f"{VERSION} {txt} E:{round(e,4)} A:{round(p,4)} G:{round(gan,2)}%")
                else:
                    send_msg(chat_id, f"{VERSION} {txt} Precio:{round(p,4)} Sin partida")
                return "ok",200
            price_sel = get_price(SELECTED)
            if "GRAF" in txt:
                send_msg(chat_id, f"Generando grafica {SELECTED}...")
                send_chart(chat_id, SELECTED)
            elif "PRO" in txt or "/START" in txt or "ACT" in txt:
                if not ENTRIES:
                    msg = f"{VERSION} Sel:{SELECTED} {round(price_sel,4)}\n"
                    for s in SYMBOLS:
                        msg += f"{s}:{round(get_price(s),4)} "
                    send_msg(chat_id, msg)
                else:
                    msg = f"{VERSION} PORTAFOLIO:\n"
                    for s, entry in ENTRIES.items():
                        p = get_price(s)
                        gan = (p/entry-1)*100
                        msg += f"\n{s} E:{round(entry,4)} A:{round(p,4)} G:{round(gan,2)}%"
                    send_msg(chat_id, msg)
            elif "COMPRAR" in txt:
                ENTRIES[SELECTED] = price_sel
                send_msg(chat_id, f"PARTIDA {SELECTED} Compra:{round(price_sel,4)}")
            elif "VENDER" in txt:
                target = SELECTED
                for s in SYMBOLS:
                    if s in txt:
                        target = s
                if target in ENTRIES:
                    e = ENTRIES[target]
                    p = get_price(target)
                    gan = (p/e-1)*100
                    send_msg(chat_id, f"CERRADA {target} G:{round(gan,2)}%")
                    del ENTRIES[target]
                else:
                    send_msg(chat_id, f"Sin partida {target}")
        return "ok",200
    except Exception as e:
        print(e)
        return "ok",200

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
