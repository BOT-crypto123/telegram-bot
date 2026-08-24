from flask import Flask, jsonify, request, send_from_directory
import json, os, random
from datetime import datetime

app = Flask(__name__)

# ===== CONFIG BINANCE $500.59 =====
CAPITAL_BINANCE = 500.59
disponible = 375.0
bloqueado = 125.59
gan = 0.59
gan_mes = 0.0
pct_mes = 0.0
ganadas = 1
winrate = 50.0
usd_mxn = 16.96
tp = 0.6
sl = -1.0
rsi_compra = 30
rsi_venta = 70
filtro_ema = "ON"
modo = "AMBOS"
max_bolas = 8
bola = CAPITAL_BINANCE / 8
auto_on = True
auto_tune = True
pos = []
historial = []
coins_activas = {"BTCUSDT": True, "ETHUSDT": True, "BNBUSDT": True, "SOLUSDT": True}

# ===== CONFIG MT5 $500 - 5 BOLAS AJUSTADO PA QUE JALE =====
CAPITAL_MT5 = 500.0
capital_mt5 = 500.0
disponible_m = 500.0
bloqueado_m = 0.0
gan_mt5 = 0.0
gan_mes_m = 0.0
pct_mes_m = 0.0
ganadas_m = 0
winrate_m = 0.0
tp_m = 0.8  # 0.6% NETO (0.8 bruto) AJUSTADO
sl_m = -1.2 # AJUSTADO PA QUE JALE
rsi_compra_m = 35 # AJUSTADO PA QUE JALE (no 25 que no compra nunca)
rsi_venta_m = 65
filtro_ema_m = "OFF" # OFF PA QUE JALE
modo_m = "AMBOS"
max_m = 5 # 5 BOLAS $100 C/U
auto_m = True
auto_tune_m = True
pos_m = []
historial_m = []
coins_mt5_activas = {"XAUUSD": True, "XAGUSD": True, "USOIL": True, "SPX500": True}

BOT_FILE = "bot_data.json"

def save_data():
    try:
        data = {
            "disponible": disponible, "bloqueado": bloqueado, "gan": gan,
            "disponible_m": disponible_m, "bloqueado_m": bloqueado_m, "gan_mt5": gan_mt5,
            "max_m": max_m, "modo_m": modo_m, "tp_m": tp_m, "sl_m": sl_m,
            "rsi_compra_m": rsi_compra_m
        }
        with open(BOT_FILE, "w") as f:
            json.dump(data, f)
    except: pass

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')
@app.route('/dashboard')
@app.route('/dashboard.html')
def dash():
    return send_from_directory('.', 'dashboard.html')

@app.route('/dashboard_mt5')
@app.route('/dashboard_mt5.html')
def dash_mt5():
    return send_from_directory('.', 'dashboard_mt5.html')

@app.route('/api/state')
def state():
    total_binance = disponible + bloqueado + gan
    total_mt5 = disponible_m + bloqueado_m + gan_mt5
    return jsonify({
        # BINANCE
        "disponible": disponible, "bloqueado": bloqueado, "gan": gan,
        "gan_mes": gan_mes, "pct_mes": pct_mes, "ganadas": ganadas, "winrate": winrate,
        "usd_mxn": usd_mxn, "tp": tp, "sl": sl, "rsi_compra": rsi_compra, "rsi_venta": rsi_venta,
        "filtro_ema": filtro_ema, "modo": modo, "max_bolas": max_bolas, "bola": bola,
        "auto_on": auto_on, "auto_tune": auto_tune, "pos": pos, "capital": CAPITAL_BINANCE,
        # MT5 5 BOLAS
        "disponible_m": disponible_m, "bloqueado_m": bloqueado_m, "gan_mt5": gan_mt5,
        "gan_mes_m": gan_mes_m, "pct_mes_m": pct_mes_m, "ganadas_m": ganadas_m, "winrate_m": winrate_m,
        "capital_mt5": CAPITAL_MT5, "capital_mt5_real": total_mt5, "total_real_mt5": total_mt5,
        "tp_m": tp_m, "sl_m": sl_m, "rsi_compra_m": rsi_compra_m, "rsi_venta_m": rsi_venta_m,
        "filtro_ema_m": filtro_ema_m, "modo_m": modo_m, "max_m": max_m, "auto_m": auto_m, "auto_tune_m": auto_tune_m,
        "pos_m": pos_m, "fee_total": 0.2
    })

@app.route('/api/prices')
def prices():
    return jsonify({
        "BTCUSDT": {"price": 67234.12, "rsi": 28, "sug": "COMPRAR LONG", "ema": 68000, "limite": rsi_compra, "change": -1.2, "motivo": "BTC barato"},
        "ETHUSDT": {"price": 2543.21, "rsi": 32, "sug": "COMPRAR LONG", "ema": 2600, "limite": rsi_compra, "change": -0.8, "motivo": "ETH en descuento"},
        "BNBUSDT": {"price": 612.45, "rsi": 45, "sug": "HOLD", "ema": 600, "limite": rsi_compra, "change": 0.5, "motivo": "BNB lateral"},
        "SOLUSDT": {"price": 142.12, "rsi": 50, "sug": "HOLD", "ema": 140, "limite": rsi_compra, "change": 1.1, "motivo": "SOL subiendo"}
    })

@app.route('/api/prices_mt5')
def prices_mt5():
    return jsonify({
        "XAUUSD": {"price": 2341.20 + random.uniform(-2,2), "rsi": 32, "sug": "COMPRAR LONG", "ema": 2360, "limite": 35, "change": 0.64, "motivo": "Oro barato - AJUSTADO PA QUE JALE"},
        "XAGUSD": {"price": 28.15 + random.uniform(-0.1,0.1), "rsi": 38, "sug": "COMPRAR LONG", "ema": 28.5, "limite": 35, "change": -0.31, "motivo": "Plata en descuento"},
        "USOIL": {"price": 76.42 + random.uniform(-0.2,0.2), "rsi": 42, "sug": "COMPRAR LONG", "ema": 77, "limite": 35, "change": 1.08, "motivo": "Petroleo subiendo"},
        "SPX500": {"price": 5432 + random.uniform(-5,5), "rsi": 48, "sug": "HOLD", "ema": 5400, "limite": 35, "change": 0.42, "motivo": "SPX lateral"}
    })

@app.route('/api/config', methods=['POST'])
def config():
    global tp, sl, rsi_venta, filtro_ema, rsi_compra, modo, max_bolas, bola
    global tp_m, sl_m, rsi_venta_m, filtro_ema_m, rsi_compra_m, modo_m, max_m, auto_tune_m, auto_tune
    d = request.get_json()
    if not d: return jsonify({"ok": True})
    if "tp" in d: tp = float(d["tp"])
    if "sl" in d: sl = float(d["sl"])
    if "rsi_venta" in d: rsi_venta = int(d["rsi_venta"])
    if "rsi_compra" in d: rsi_compra = int(d["rsi_compra"])
    if "filtro_ema" in d: filtro_ema = d["filtro_ema"]
    if "modo" in d: modo = d["modo"]
    # MT5
    if "tp_m" in d: tp_m = float(d["tp_m"])
    if "sl_m" in d: sl_m = float(d["sl_m"])
    if "rsi_venta_m" in d: rsi_venta_m = int(d["rsi_venta_m"])
    if "rsi_compra_m" in d: rsi_compra_m = int(d["rsi_compra_m"])
    if "filtro_ema_m" in d: filtro_ema_m = d["filtro_ema_m"]
    if "modo_m" in d: modo_m = d["modo_m"]
    if "max_m" in d: max_m = int(d["max_m"])
    if "auto_tune_m" in d: auto_tune_m = (d["auto_tune_m"] == "ON")
    if "auto_tune" in d: auto_tune = (d["auto_tune"] == "ON")
    save_data()
    return jsonify({"ok": True})

@app.route('/api/toggle', methods=['POST'])
def toggle():
    global auto_on, auto_m
    d = request.get_json()
    if d.get("side") == "mt5":
        auto_m = not auto_m
    else:
        auto_on = not auto_on
    return jsonify({"ok": True})

@app.route('/api/sell/<sym>', methods=['POST'])
def sell(sym):
    return jsonify({"ok": True})

@app.route('/api/sell_mt5/<sym>', methods=['POST'])
def sell_mt5(sym):
    return jsonify({"ok": True, "msg": f"Vendido {sym} MT5"})

@app.route('/api/backup')
def backup():
    return jsonify({"binance": {"gan": gan}, "mt5": {"gan_mt5": gan_mt5, "max_m": max_m, "capital": 500}})

@app.route('/api/restore', methods=['POST'])
def restore():
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
