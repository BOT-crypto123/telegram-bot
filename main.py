import time
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd

app = Flask(__name__)

# --- CONFIG AJUSTABLE DESDE DASHBOARD (como lo tienes) ---
CONFIG = {
    "MAX": 5,
    "TRAIL_PCT": 0.1,  # 0.1% = $1.10
    "VERSION": "V59 ANALISIS ON",
    "BALANCE_TOTAL": 10000,
    "STOP_PCT": -1.5,
    "COOLDOWN_MIN": 20,
    "COSTO_BOLA": 0, # se calcula
    "bolas": [], # {"entry": 69556, "retail": -23, "estado": "Esperando"}
    "last_buy_time": 0,
    "flot_retail": 0
}

def get_analysis(symbol="BTC-USD"):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False)
        if len(df) < 200:
            return False, "Sin datos"
        
        close = df['Close']
        # EMA 200
        ema200 = close.ewm(span=200).mean().iloc[-1]
        price = close.iloc[-1]
        
        # RSI 14
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_last = rsi.iloc[-1]
        
        # Volumen
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_last = df['Volume'].iloc[-1]
        
        # FILTROS V59
        if
