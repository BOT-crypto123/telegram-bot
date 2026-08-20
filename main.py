import os
import time
from flask import Flask, jsonify, request

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
    "flot_retail": -68.66,
    "analisis_log": "Esperando"
}

# --- ANALISIS V59 ---
def get_analysis():
    try:
        import yfinance as yf
        df = yf.download("BTC-USD", period="2d", interval="5m", progress=False)
        if len(df) < 200:
            return False, "Sin datos"
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
            return False, f"EMA BLOQUEO {price:.0f}<{ema200:.0f}"
        if rsi_last > 60:
            return False, f"RSI ALTO {rsi_last:.0f}"
        if vol_last < vol_avg * 0.8:
            return False, "VOL BAJO"
        if time.time() - CONFIG["last_buy_time"] < CONFIG["COOLDOWN_MIN"]*60:
            return False, f"COOLDOWN {CONFIG['COOLDOWN_MIN']}m"
        
        return True, f"OK EMA:{ema200:.0f} RSI:{rsi_last:.0f} VOL:OK"
    except Exception as e:
        return False, f"ERR: {str(e)[:80]}"

# --- DASHBOARD AJUSTABLE (como lo tienes) ---
@app.route("/")
def dashboard():
    costo = CONFIG["BALANCE_TOTAL"] / CONFIG["MAX"] if CONFIG["MAX"]>0 else 0
    max_btns = " ".join([f'<a href="/set_max/{i}">[{i}]</a>' for i in range(1,7)])
    trail_btns = " ".join([f'<a href="/set_trail/{p}">{p}%</a>' for p in [0.1,0.2,0.3,0.4,0.6,0.8,1.0]])
    
    return f"""
    <html><body style="font-family:monospace
