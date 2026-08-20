import os
from flask import Flask, jsonify

app = Flask(__name__)

CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,
    "VERSION": "V59 ANALISIS ON",
    "BALANCE_TOTAL": 10000,
    "bolas": [],
    "last_buy_time": 0,
    "flot_retail": 0
}

def get_analysis():
    # Analisis sin romper el deploy
    try:
        import yfinance as yf
        df = yf.download("BTC-USD", period="2d", interval="5m", progress=False)
        close = df["Close"]
        ema200 = close.ewm(span=200).mean().iloc[-1]
        price = float(close.iloc[-1])
        if price < ema200:
            return False, f"EMA BLOQUEO {price:.0f} < {ema200:.0f}"
        return True, f"OK EMA {ema200:.0f}"
    except Exception as e:
        return False, f"ANALISIS ERROR: {str(e)[:100]}"

@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"]
    html = f"""
    <h3>{CONFIG["VERSION"]} | MAX {len(CONFIG["bolas"])}/{CONFIG["MAX"]} | TRAIL {CONFIG["TRAIL_PCT"]}%</h3>
    <p>Costo bola: ${costo:.2f} | Balance: 10000</p>
    <p>MAX: <a href="/set_max/1">[1]</a> <a href="/set_max/2">[2]</a> <a href="/set_max/3">[3]</a> <a href="/set_max/4">[4]</a> <a href="/set_max/5">[5]</a> <a href="/set_max/6">[6]</a></p>
    <p>TRAIL: <a href="/set_trail/0.1">0.1%</a> <a href="/set_trail/0.2">0.2%</a> <a href="/set_trail/0.3">0.3%</a> <a href="/set_trail/0.6">0.6%</a> <a href="/set_trail/1.0">1.0%</a></p>
    <p><a href="/analisis">PROBAR ANALISIS</a> | <a href="/estado">ESTADO</a></p>
    <pre>Bolas: {CONFIG["bolas"]}</pre>
    """
    return html

@app.route("/set_max/<int:n>")
def set_max(n):
    CONFIG["MAX"] = max(1, min(20, n))
    return jsonify(CONFIG)

@app.route("/set_trail/<float:p>")
def set_trail(p):
    CONFIG["TRAIL_PCT"] = p
    return jsonify(CONFIG)

@app.route("/analisis")
def analisis():
    ok, msg = get_analysis()
    return jsonify({"pasa": ok, "msg": msg})

@app.route("/estado")
def estado():
    return jsonify(CONFIG)

@app.route("/reset")
def reset():
    CONFIG["bolas"] = []
    return jsonify(CONFIG)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
