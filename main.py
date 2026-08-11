import os, json, time, threading, requests
from flask import Flask, request, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)

# === CONFIG V1002.12 REAL $5,000 ===
DATA_FILE = "bot_data.json"
OBJETIVO_TOTAL = 5000.0
TRADE_AMOUNT = 50.0
MAX_POS = 5
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

data = {
    "b": 1850.0,
    "pos": [],
    "gan_total": 0.0,
    "gan_hoy": 0.0,
    "trades_hoy": 0,
    "historial_diario": {},
    "alert_users": []
}

def load_data():
    global data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
    except: pass

def save_data():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(e)

# === MIGRACION REALISTA A $5000 - LO QUE PEDISTE ===
def migrar_a_5000_real():
    total_pos = sum([p.get('monto',50) * (1 + p.get('gan',0)/100) for p in data.get('pos',[])])
    total_actual = data.get('b',0) + total_pos
    if total_actual < 4900 and total_actual > 100:
        diferencia = OBJETIVO_TOTAL - total_actual
        data['b'] += diferencia
        print(f">> MIGRACION REAL: Total era ${total_actual:.2f}, se sumó ${diferencia:.2f} -> Ahora ${OBJETIVO_TOTAL}")
        save_data()
        return diferencia
    return 0

load_data()
dif = migrar_a_5000_real()

def send_tg(uid, txt):
    try:
        requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": uid, "text": txt}, timeout=10)
    except: pass

def texto_reporte():
    total_pos = sum([p.get('monto',50) * (1 + p.get('gan',0)/100) for p in data.get('pos',[])])
    total = data['b'] + total_pos
    pos_txt = "\n".join([f"- {p.get('sym')} {p.get('gan',0):.2f}% ${p.get('monto',50)}" for p in data['pos']]) or "Sin posiciones"
    hist = ""
    for k,v in list(data.get('historial_diario',{}).items())[-7:]:
        hist += f"{k} +${v.get('gan',0):.2f} ({v.get('trades',0)} trades)\n"
    if not hist: hist = "Primer dia con $5000"

    return f"""📊 REPORTE V1002.12 REAL - $5,000
💰 Saldo: ${data['b']:.2f} MXN
💵 Valor posiciones: ${total_pos:.2f}
💵 Total: ${total:.2f} MXN
📈 Gan total: ${data.get('gan_total',0):.2f}
🔄 Hoy: ${data.get('gan_hoy',0):.2f} Trades hoy: {data.get('trades_hoy',0)}
Pos: {len(data.get('pos',[]))}/{MAX_POS}
{pos_txt}
Dias:
{hist}
Guardado en: {DATA_FILE}"""

# --- DASHBOARD SIMPLE ---
@app.route('/')
def home():
    total_pos = sum([p.get('monto',50) * (1 + p.get('gan',0)/100) for p in data.get('pos',[])])
    total = data['b'] + total_pos
    return f"<h2>V1002.12 REAL $5,000 ACTIVO</h2>Total: ${total:.2f} Saldo: ${data['b']:.2f} Pos: {len(data['pos'])}<br><a href='/dashboard'>Dashboard</a> | <a href='/reporte'>Reporte</a>"

@app.route('/dashboard')
def dashboard():
    # Pega aqui tu HTML grande del dashboard original si quieres, este es resumen
    total_pos = sum([p.get('monto',50) * (1 + p.get('gan',0)/100) for p in data.get('pos',[])])
    total = data['b'] + total_pos
    html = f"""
    <h3>Saldo: ${data['b']:.2f} | Total: ${total:.2f} | Pos: {len(data['pos'])}/5</h3>
    <pre>{texto_reporte()}</pre>
    """
    return html

@app.route('/reporte')
def reporte():
    return texto_reporte().replace("\n","<br>")

@app.route('/webhook', methods=['POST'])
def webhook():
    d = request.json
    if "message" in d:
        chat_id = d["message"]["chat"]["id"]
        text = d["message"].get("text","")
        if chat_id not in data["alert_users"]:
            data["alert_users"].append(chat_id)
        if "/start" in text:
            send_tg(chat_id, f"Bot V1002.12 REAL $5000 activo. Total: ${data['b'] + sum([p.get('monto',50) for p in data['pos']]):.0f}")
        if "/reporte" in text:
            send_tg(chat_id, texto_reporte())
        save_data()
    return jsonify(ok=True)

def loop():
    while True:
        try:
            mx = pytz.timezone("America/Mexico_City")
            ahora_mx = datetime.now(mx)
            # Reporte 10 PM
            if ahora_mx.hour == 22 and ahora_mx.minute == 0:
                txt = texto_reporte()
                for uid in data["alert_users"]:
                    send_tg(uid, txt)
                hoy = ahora_mx.strftime("%d/%m")
                data["historial_diario"][hoy] = {"gan": data["gan_hoy"], "trades": data["trades_hoy"]}
                data["gan_hoy"] = 0
                data["trades_hoy"] = 0
                save_data()
                time.sleep(90)
            time.sleep(30)
        except Exception as e:
            print(e)
            time.sleep(10)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
