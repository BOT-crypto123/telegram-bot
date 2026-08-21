import os, sys, requests, threading, time
from flask import Flask, request
from datetime import datetime

os.environ['PYTHONUNBUFFERED']='1'
sys.stdout.reconfigure(line_buffering=True)

print("INICIANDO V108.1 FIX", flush=True)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = "https://telegram-bot-cijp.onrender.com"
CHAT_ID = None

CONFIG = {
    "BASE": 10000.0,
    "ACUMULADO": 316.0,
    "BOLAS_MAX": 10,
    "COSTO_BOLA": 1031.63,
    "FEES_PCT": 0.50,
    "TP_PCT": 0.50,
    "SL_PCT": -3.0,
    "AUTO": False
}

bolas = [
    {"moneda":"XRP","compra":22.24,"costo":1031.63,"cantidad":46.38,"fecha":"2025-01-10"},
    {"moneda":"ETH","compra":40049.34,"costo":1031.63,"cantidad":0.0257,"fecha":"2025-01-11"},
]

PRECIOS_CACHE = {"BTC":1273222,"ETH":39926,"SOL":1531,"DOGE":1.42,"XRP":22.13,"ADA":3.54,"AVAX":125.33,"BNB":9870,"LTC":1450}

def get_precio_bitso(moneda):
    return PRECIOS_CACHE.get(moneda, 0)

def calc_ganancia(entrada, actual, costo):
    if not entrada or not actual or entrada < 0.001:
        return 0, 0, 0
    bruto = ((actual - entrada) / entrada) * 100
    neto = bruto - CONFIG["FEES_PCT"]
    usd = costo * (neto / 100)
    return bruto, neto, usd

def dashboard_text():
    total_flotante = 0
    ganadoras = 0
    msg = "MAQUINA V108.1 FINAL\n"
    msg += f"BAL: ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f}\n"
    msg += f"ACUM: +${CONFIG['ACUMULADO']:.2f} BASE: ${CONFIG['BASE']:.2f}\n"
    msg += f"AUTO: {'ON' if CONFIG['AUTO'] else 'OFF'} | FEES: {CONFIG['FEES_PCT']}%\n"
    msg += f"TP: >= {CONFIG['TP_PCT']}% NETO | SL: {CONFIG['SL_PCT']}%\n"
    msg += "------------------------\n\n"

    for i, b in enumerate(bolas, 1):
        actual = get_precio_bitso(b['moneda'])
        bruto, neto, usd = calc_ganancia(b['compra'], actual, b['costo'])
        total_flotante += usd
        if neto >= CONFIG["TP_PCT"]:
            ganadoras += 1

        if neto >= CONFIG["TP_PCT"]:
            estado = "VERDE VENDIBLE"
        elif neto >= 0:
            estado = "AMARILLO EN VERDE pero no llega a 0.5 neto"
        else:
            estado = "ROJO"

        msg += f"{estado} BOLA {i} {b['moneda']}\n"
        msg += f" Compra: {b['compra']} -> Ahora: {actual}\n"
        msg += f" Bruto: {bruto:.2f}% | NETO REAL: {neto:.2f}%\n"
        msg += f" Ganancia: ${usd:.2f}\n\n"

    msg += "------------------------\n"
    msg += f"FLOTANTE TOTAL: ${total_flotante:.2f}\n"
    msg += f"VENDIBLES mayor igual 0.5 pct: {ganadoras}/{len(bolas)}\n"
    msg += f"BOLAS: {len(bolas)}/{CONFIG['BOLAS_MAX']}\n"
    msg += f"{datetime.now().strftime('%d/%m %H:%M:%S')}\n"
    return msg, total_flotante, ganadoras

def enviar(cid, texto):
    try:
        print(f"ENVIANDO A {cid}", flush=True)
        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":cid,"text":texto}, timeout=10)
        print(f"TELEGRAM OK {r.status_code} {r.text}", flush=True)
    except Exception as e:
        print(f"ERROR ENVIO {e}", flush=True)

def vender_bola(index):
    try:
        b = bolas[index]
        actual = get_precio_bitso(b['moneda'])
        _, neto, usd = calc_ganancia(b['compra'], actual, b['costo'])
        CONFIG["ACUMULADO"] += usd
        CONFIG["BASE"] += b['costo']
        msg = f"VENDIDA {b['moneda']} Compra {b['compra']} Venta {actual} Neto {neto:.2f}% Gan ${usd:.2f} Nuevo BAL ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f}"
        bolas.pop(index)
        return msg
    except Exception as e:
        return f"Error vendiendo: {e}"

def auto_trading_loop():
    print("AUTO LOOP V108.1 INICIADO", flush=True)
    while True:
        try:
            if CONFIG["AUTO"] and CHAT_ID:
                for b in bolas[:]:
                    actual = get_precio_bitso(b['moneda'])
                    _, neto, usd = calc_ganancia(b['compra'], actual, b['costo'])
                    if neto >= CONFIG["TP_PCT"]:
                        print(f"TP {b['moneda']} {neto:.2f}%", flush=True)
                        texto = vender_bola(bolas.index(b))
                        enviar(CHAT_ID, f"AUTO VENTA {texto}")
                        time.sleep(2)
            time.sleep(30)
        except Exception as e:
            print(f"ERROR AUTO {e}", flush=True)
            time.sleep(10)

threading.Thread(target=auto_trading_loop, daemon=True).start()

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    txt, _, _ = dashboard_text()
    return f"<pre>{txt}</pre><h3>V108.1 FIX LIVE {datetime.now()}</h3>"

@app.route('/', methods=['POST'])
def webhook():
    global CHAT_ID
    print("POST WEBHOOK RECIBIDO", flush=True)
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return "ok", 200
        print(f"DATA {data}", flush=True)
        message = data.get("message", {})
        text = message.get("text","").strip()
        text_upper = text.upper()
        cid = message.get("chat",{}).get("id")
        if cid:
            CHAT_ID = cid
        print(f"CMD {text_upper} FROM {cid}", flush=True)

        if text_upper == "DASHBOARD" and cid:
            txt, _, _ = dashboard_text()
            enviar(cid, txt)
        elif text_upper == "AUTO ON" and cid:
            CONFIG["AUTO"] = True
            enviar(cid, f"AUTO ON TP {CONFIG['TP_PCT']}% NETO REAL")
        elif text_upper == "AUTO OFF" and cid:
            CONFIG["AUTO"] = False
            enviar(cid, "AUTO OFF")
        elif text_upper == "BALANCE" and cid:
            enviar(cid, f"BALANCE ${CONFIG['BASE']+CONFIG['ACUMULADO']:.2f} BASE ${CONFIG['BASE']} ACUM {CONFIG['ACUMULADO']}")
        elif text_upper == "AYUDA" and cid:
            enviar(cid, "COMANDOS:\nDASHBOARD\nAUTO ON/OFF\nBALANCE")
    except Exception as e:
        print(f"ERROR WEBHOOK {e}", flush=True)
    return "ok", 200

if TOKEN:
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL}", timeout=10).json()
        print(f"WEBHOOK SET {r}", flush=True)
    except Exception as e:
        print(f"ERROR SET WEBHOOK {e}", flush=True)

print("V108.1 LISTO", flush=True)
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
