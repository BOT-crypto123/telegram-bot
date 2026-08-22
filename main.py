import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"

# Carga data
try:
    with open(DATA_FILE) as f: data=json.load(f)
except: data={"capital_actual":500,"alert_users":[],"usd_mxn":16.96,"gan_acum_total":0}

def save():
    with open(DATA_FILE,"w") as f: json.dump(data,f)

def tg(chat_id, text):
    if not BOT_TOKEN: 
        print("NO BOT_TOKEN en Render!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "inline_keyboard": [[{"text":"📊 VER DASHBOARD","url":f"{os.getenv('RENDER_EXTERNAL_URL','https://telegram-bot-cijp.onrender.com')}/dashboard"}]]
            }
        }, timeout=10)
        print("TG RESP:", r.text)
    except Exception as e:
        print("TG ERROR:", e)

@app.route("/", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def webhook():
    if request.method == "GET":
        return "BOT LIVE",200
    
    d = request.get_json(force=True, silent=True) or {}
    print("INCOMING:", d)
    
    if "message" in d and "chat" in d["message"]:
        chat = d["message"]["chat"]["id"]
        txt = d["message"].get("text","")
        
        if chat not in data["alert_users"]:
            data["alert_users"].append(chat)
            save()
            print(f"Nuevo usuario guardado: {chat}")

        # SIEMPRE CONTESTA, no importa que escribas
        base = os.getenv("RENDER_EXTERNAL_URL","https://telegram-bot-cijp.onrender.com")
        tg(chat, f"500 USD = ${data['usd_mxn']*500:.0f} MXN\nAcum: ${data['gan_acum_total']:.2f}\n{base}/dashboard")
    
    return jsonify(ok=True)

# ... deja el resto de tu main.py igual (dashboard, /api/prices, etc)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
