from flask import Flask, jsonify
import time
import yfinance as yf
import pandas as pd

app = Flask(__name__)

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V59 ANALISIS ON",
    "BALANCE_TOTAL": 10000,
    "STOP_PCT": -1.5,
    "COOLDOWN_MIN": 20,
    "bolas": [],
    "last_buy_time": 0,
    "flot_retail": 0
}

def get_analysis():
    try:
        df = yf.download("BTC-USD", period="2d", interval="5m", progress=False)
        if len(df) < 200:
            return False, "Sin datos suficientes"
        
        close = df["Close"]
        ema200 = close.ewm(span=200).mean().iloc[-1]
        price = float(close.iloc[-1])
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_last = float(rsi.iloc[-1])
        
        vol_avg = float(df["Volume"].rolling(20).mean().iloc[-1])
        vol_last = float(df["Volume"].iloc[-1])
        
        if price < ema200:
            return False, f"EMA BLOQUEO {price:.0f} < {ema200:.0f}"
        if rsi_last > 60:
            return False, f"RSI ALTO {rsi_last:.0f}"
        if rsi_last < 30:
            return False, f"RSI BAJO {rsi_last:.0f}"
        if vol_last < vol_avg * 0.8:
            return False, "VOLUMEN BAJO"
        if time.time() - CONFIG["last_buy_time"] < CONFIG["COOLDOWN_MIN"] * 60:
            return False, f"COOLDOWN {CONFIG['COOLDOWN_MIN']}m"
            
        return True, f"OK EMA {ema200:.0f} RSI {rsi_last:.0f} VOL OK"
    except Exception as e:
        return False, str(e)

@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"] if CONFIG["MAX"] > 0 else 0
    max_links = ""
    for i in range(1, 7):
        max_links += f'<a href="/set_max/{i}">[{i}]</a> '
    trail_links = ""
    for p in [0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0]:
        trail_links += f'<a href="/set_trail/{p}">{p}%</a> '
    
    html = f"""
    <h3>{CONFIG["VERSION"]} | MAX {len(CONFIG["bolas"])}/{CONFIG["MAX"]} | TRAIL {CONFIG["TRAIL_PCT"]}%</h3>
    <p>Costo bola: ${costo:.2f} | Balance: ${CONFIG["BALANCE_TOTAL"]} | FLOT: ${CONFIG["flot_retail"]}</p>
    <p>MAX: <a href="/set_max/{max(1, CONFIG["MAX"]-1)}">-</a> {max_links} <a href="/set_max/{CONFIG["MAX"]+1}">+</a></p>
    <p>TRAIL: {trail_links} <a href="/set_trail/{CONFIG["TRAIL_PCT"]+0.1}">+</a></p>
    <p><a href="/reset">RESET</a> | <a href="/estado">ESTADO</a> | <a href="/analisis">ANALISIS</a></p>
    <pre>Bolas: {CONFIG["bolas"]}</pre>
    """
    return html

@app.route("/set_max/<int:n>")
def set_max(n):
    if n < 1:
        n = 1
    if n > 20:
        n = 20
    CONFIG["MAX"] = n
    return jsonify(CONFIG)

@app.route("/set_trail/<float:p>")
def set_trail(p):
    CONFIG["TRAIL_PCT"] = p
    return jsonify(CONFIG)

@app.route("/reset")
def reset():
    CONFIG["bolas"] = []
    CONFIG["flot_retail"] = 0
    return jsonify({"reset": "OK", "config": CONFIG})

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

@app.route("/analisis")
def analisis():
    ok, msg = get_analysis()
    return jsonify({"pasa": ok, "analisis": msg})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
