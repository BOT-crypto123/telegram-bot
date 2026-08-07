import os, requests, time, threading
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
VERSION = "V40 MULTI"
app = Flask(__name__)

SYMBOLS = ["BTC","ETH","SOL","XRP","DOGE","ADA"]
ENTRIES = {} # symbol -> price
CHAT_ID_SAVED = None
SELECTED = "BTC"

def get_price(sym="BTC"):
    sym = sym.upper()
    try:
        r = requests.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", timeout=5).json()
        return float(r["data"]["amount"])
    except: pass
    try:
        # Coingecko fallback
        ids = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","DOGE":"dogecoin","ADA":"cardano"}
        cid = ids.get(sym, "bitcoin")
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd", timeout=5).json()
        return float(r[cid]["usd"])
    except:
        return 0.0

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    kb = {"keyboard": [[{"text":"BTC"},{"text":"ETH"},{"text":"SOL"}],[{"text":"XRP"},{"text":"DOGE"},{"text":"ADA"}],[{"text":"COMPRAR"},{"text":"VENDER"}],[{"text":"SL"},{"text":"TP"}],[{"text":"GRAF"},{"text":"PRO"}]], "resize_keyboard": True}
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=10)
    except: pass

def monitor():
    while True:
        time.sleep(300)
        if CHAT_ID_SAVED and ENTRIES:
            for sym, entry in list(ENTRIES.items()):
                try:
                    p = get_price(sym)
                    if p==0: continue
                    if p <= entry * 0.95:
                        send_msg(CHAT_ID_SAVED, f"🚨 ALERTA {sym} SL -5% Compra {round(entry,2)} Ahora {round(p,2)}")
                    if p >= entry * 1.10:
                        send_msg(CHAT_ID_SAVED, f"💰 ALERTA {sym} TP +10% Compra {round(entry,2)} Ahora {round(p,2)}")
                except: pass

threading.Thread(target=monitor, daemon=True).start()

@app.route("/")
def home():
    prices = ", ".join([f"{s}:{round(get_price(s),2)}" for s in ["BTC","ETH"]])
    return f"{VERSION} ON - {prices}", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    global CHAT_ID_SAVED, SELECTED
    try:
        data = request.get_json(force=True, silent=True)
        if not data: return "ok",200
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            CHAT_ID_SAVED = chat_id
            txt = data["message"].get("text","").upper().strip()

            # Seleccion de moneda
            if txt in SYMBOLS:
                SELECTED = txt
                p = get_price(txt)
                e = ENTRIES.get(txt)
                if e:
                    gan = (p/e-1)*100
                    send_msg(chat_id, f"{VERSION} {txt}\nENTRY: {round(e,4)}\nAHORA: {round(p,4)}\nGan: {round(gan,2)}%\nSL: {round(e*0.95,4)}\nTP: {round(e*1.10,4)}")
                else:
                    send_msg(chat_id, f"{VERSION} {txt}\nBTC REAL: {round(p,4)}\nSin partida en {txt}\nDale COMPRAR")
                return "ok",200

            # Info moneda con texto "BTC 1000" etc? solo simbolo ya manejado
            btc_price = get_price(SELECTED)

            if "/START" in txt or "PRO" in txt or "GRAF" in txt or "ACT" in txt:
                if not ENTRIES:
                    # muestra todos los precios
                    msg = f"{VERSION}\nSeleccionada: {SELECTED} = {round(btc_price,4)}\nSin partidas\nElige moneda y dale COMPRAR\n\n"
                    for s in SYMBOLS:
                        msg += f"{s}: {round(get_price(s),4)} "
                    send_msg(chat_id, msg)
                else:
                    msg = f"{VERSION} PORTAFOLIO:\n"
                    for s, entry in ENTRIES.items():
                        p = get_price(s)
                        gan = (p/entry-1)*100 if entry else 0
                        msg += f"\n{s} E:{round(entry,4)} A:{round(p,4)} G:{round(gan,2)}% SL:{round(entry*0.95,2)} TP:{round(entry*1.10,2)}"
                    send_msg(chat_id, msg)
            elif "COMPRAR" in txt:
                ENTRIES[SELECTED] = btc_price
                send_msg(chat_id, f"PARTIDA INICIADA {SELECTED}\nCompra: {round(btc_price,4)}\nSL: {round(btc_price*0.95,4)}\nTP: {round(btc_price*1.10,4)}")
            elif "VENDER" in txt:
                # Si dice "VENDER ETH" vende esa, si solo VENDER vende la seleccionada
                target = SELECTED
                for s in SYMBOLS:
                    if s in txt:
                        target = s
                        break
                if target in ENTRIES:
                    e = ENTRIES[target]
                    p = get_price(target)
                    gan = (p/e-1)*100
                    send_msg(chat_id, f"CERRADA {target}\nCompra: {round(e,4)}\nVenta: {round(p,4)}\nRes: {round(gan,2)}%")
                    del ENTRIES[target]
                else:
                    send_msg(chat_id, f"Sin partida en {target}")
            elif "SL" in txt:
                if SELECTED in ENTRIES:
                    send_msg(chat_id, f"SL {SELECTED}: {round(ENTRIES[SELECTED]*0.95,4)}")
                else:
                    send_msg(chat_id, f"Sin partida en {SELECTED}")
            elif "TP" in txt:
                if SELECTED in ENTRIES:
                    send_msg(chat_id, f"TP {SELECTED}: {round(ENTRIES[SELECTED]*1.10,4)}")
                else:
                    send_msg(chat_id, f"Sin partida en {SELECTED}")
        return "ok",200
    except Exception as e:
        print(e)
        return "ok",200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
