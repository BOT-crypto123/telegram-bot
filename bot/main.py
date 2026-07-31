import os, json, time, threading, requests
from flask import Flask
import telebot
from telebot import types

print("INICIANDO VICENTE V3 - 3 MONEDAS ULTRA BLINDADO", flush=True)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COMISION = 0.0078
bot = telebot.TeleBot(TOKEN)
CARTERA_FILE = "cartera.json"

def load_cartera():
    if os.path.exists(CARTERA_FILE):
        try:
            with open(CARTERA_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"usd": 1000.0, "btc": 0.0, "eth": 0.0, "xrp": 0.0, "precio_btc": 0.0, "precio_eth": 0.0, "precio_xrp": 0.0}

def save_cartera(c):
    with open(CARTERA_FILE, "w") as f:
        json.dump(c, f)

def get_precios():
    headers = {"User-Agent": "Mozilla/5.0"}
    # 1. Coinbase - nunca bloquea
    try:
        def cb(coin):
            r = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-USD/spot", headers=headers, timeout=8).json()
            p = float(r['data']['amount'])
            # 24h change de Coinbase no da, sacamos de stats
            try:
                s = requests.get(f"https://api.coinbase.com/v2/prices/{coin}-USD/spot?date={(requests.get('https://api.coinbase.com/v2/time', timeout=5).json())}", timeout=8)
            except: pass
            return p, 0.0
        btc_p = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", headers=headers, timeout=8).json()['data']['amount'])
        eth_p = float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", headers=headers, timeout=8).json()['data']['amount'])
        xrp_p = float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot", headers=headers, timeout=8).json()['data']['amount'])
        # para el cambio 24h usamos cryptocompare
        try:
            cc = requests.get("https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,XRP&tsyms=USD", headers=headers, timeout=8).json()
            btc_c = cc['RAW']['BTC']['USD']['CHANGEPCT24HOUR']
            eth_c = cc['RAW']['ETH']['USD']['CHANGEPCT24HOUR']
            xrp_c = cc['RAW']['XRP']['USD']['CHANGEPCT24HOUR']
        except:
            btc_c = eth_c = xrp_c = 0.0
        print(f"Precios Coinbase OK: BTC {btc_p}", flush=True)
        return {"btc": (btc_p, btc_c), "eth": (eth_p, eth_c), "xrp": (xrp_p, xrp_c)}
    except Exception as e:
        print(f"Fallo coinbase: {e}", flush=True)

    # 2. CoinGecko
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true", headers=headers, timeout=10).json()
        return {"btc": (r['bitcoin']['usd'], r['bitcoin']['usd_24h_change']), "eth": (r['ethereum']['usd'], r['ethereum']['usd_24h_change']), "xrp": (r['ripple']['usd'], r['ripple']['usd_24h_change'])}
    except Exception as e:
        print(f"Fallo coingecko: {e}", flush=True)
    return None

def get_keyboard():
    m = types.InlineKeyboardMarkup()
    m.row(types.InlineKeyboardButton("🟢 BTC", callback_data="comprar_btc"), types.InlineKeyboardButton("🟢 ETH", callback_data="comprar_eth"), types.InlineKeyboardButton("🟢 XRP", callback_data="comprar_xrp"))
    m.row(types.InlineKeyboardButton("🔴 BTC", callback_data="vender_btc"), types.InlineKeyboardButton("🔴 ETH", callback_data="vender_eth"), types.InlineKeyboardButton("🔴 XRP", callback_data="vender_xrp"))
    return m

@bot.message_handler(commands=['start','balance'])
def start(msg):
    p = get_precios()
    if not p:
        bot.send_message(msg.chat.id, "⏳ Espera 20 seg, APIs saturadas, ya estoy reintentando solo")
        return
    c = load_cartera()
    total = c["usd"] + c["btc"]*p['btc'][0] + c["eth"]*p['eth'][0] + c["xrp"]*p['xrp'][0]
    txt = f"⚡ *VICENTE CRYPTO PRO - 3 MONEDAS (5min)*\n\nBTC: ${p['btc'][0]:,.2f} ({p['btc'][1]:+.2f}%)\nETH: ${p['eth'][0]:,.2f} ({p['eth'][1]:+.2f}%)\nXRP: ${p['xrp'][0]:,.4f} ({p['xrp'][1]:+.2f}%)\n\nUSD: ${c['usd']:.2f} | TOTAL: ${total:.2f}"
    bot.send_message(msg.chat.id, txt, reply_markup=get_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda x: True)
def cbq(call):
    c = load_cartera(); pr = get_precios()
    if not pr: return
    acc, mon = call.data.split("_")
    precio = pr[mon][0]
    if acc=="comprar":
        if c["usd"]<1: bot.answer_callback_query(call.id,"Sin USD"); return
        usd=c["usd"]*0.33; cant=(usd*(1-COMISION))/precio; c["usd"]-=usd; c[mon]+=cant; c[f"precio_{mon}"]=precio; save_cartera(c)
        bot.send_message(call.message.chat.id,f"✅ COMPRA {mon.upper()} {cant:.6f} a ${precio:,.2f}")
    else:
        if c[mon]==0: bot.answer_callback_query(call.id,f"No tienes {mon.upper()}"); return
        usd=c[mon]*precio*(1-COMISION); c["usd"]+=usd; c[mon]=0; save_cartera(c)
        bot.send_message(call.message.chat.id,f"✅ VENTA {mon.upper()} ${usd:.2f}", reply_markup=get_keyboard())
    bot.answer_callback_query(call.id,"Listo")

def alertas():
    while True:
        time.sleep(300)
        try:
            pr=get_precios()
            if not pr or not CHAT_ID: continue
            c=load_cartera()
            for mon in ["btc","eth","xrp"]:
                precio,cambio=pr[mon]
                if cambio<=-2:
                    bot.send_message(CHAT_ID,f"🟢 *COMPRA {mon.upper()}!* Cayó {cambio:.2f}% - ${precio:,.4f}", reply_markup=get_keyboard(), parse_mode="Markdown")
                if c[mon]>0 and c[f"precio_{mon}"]>0:
                    gan=(precio-c[f"precio_{mon}"])/c[f"precio_{mon}"]*100-1.56
                    if gan>=2:
                        bot.send_message(CHAT_ID,f"🔴 *VENDE {mon.upper()}!* +{gan:.2f}% NETA - ${precio:,.4f}", reply_markup=get_keyboard(), parse_mode="Markdown")
        except Exception as e: print(e)

threading.Thread(target=alertas, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return "Vicente V3 Live - 3 monedas"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
