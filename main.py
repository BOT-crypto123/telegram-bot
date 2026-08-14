import os, time, threading, requests, pytz, math
from flask import Flask, request
from datetime import datetime, timedelta
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== CONFIG V47 ==========
CAPITAL_BASE = 5000
BOLA_CRYPTO = 500
BOLA_NY = 1750
BOLA_JEFE_MULT = 2.2 # Bola grande $3375
TOPES = {"crypto": 1500, "ny": 4000}
MAX_PERDIDAS = 3

ESTADO = {
    "auto": True, "ganancia_total": 0.0, "perdidas_seguidas": 0,
    "jefe_cazo_hoy": {}, # JEFE 1 vez por dia por moneda
    "posiciones": {}
}

SYMBOLS = ["BTC", "ETH", "SOL", "XAUUSD", "NVDA", "TSLA"]

# ========== KRAKEN ==========
def kraken_request(method, params={}):
    try:
        url = f"https://api.kraken.com/0/public/{method}"
        r = requests.get(url, params=params, timeout=10)
        return r.json()['result']
    except: return None

def get_precio(simbolo):
    try:
        if simbolo == "XAUUSD":
            import yfinance as yf
            return yf.Ticker("GC=F").history(period="1d")['Close'][-1]
        par = f"{simbolo}/USD" if simbolo!= "BTC" else "XBT/USD"
        ohlc = kraken_request('OHLC', {'pair': par, 'interval': 1})
        if ohlc:
            k = list(ohlc.keys())[0]
            return float(ohlc[k][-1][4])
    except: return 0
    return 0

# ========== 3 VATOS LOGIC ==========
def detectar_lineas_automaticas(closes):
    # VATO 1 - MAQUINA
    lineas = []
    if len(closes) < 30: return lineas
    for i in range(10, len(closes)-10):
        precio = closes[i]
        rebotes = 0
        # Cuenta rebotes
        for j in range(len(closes)):
            if abs(closes[j] - precio) / precio < 0.002: # 0.2% cerca
                rebotes += 1
        if rebotes >= 3:
            fuerza = min(95, rebotes*15 + (100 - abs(closes[-1]-precio)/precio*1000))
            lineas.append({"precio": precio, "rebotes": rebotes, "fuerza": fuerza})
    # Ordena por rebotes
    lineas = sorted(lineas, key=lambda x: x['rebotes'], reverse=True)
    # Elimina duplicadas
    unicas = []
    for l in lineas:
        if not any(abs(l['precio']-u['precio'])/u['precio'] < 0.005 for u in unicas):
            unicas.append(l)
    return unicas[:10]

def chalan_confirma(lineas, closes):
    # VATO 2 - CHALAN - Doble candado 30 lineas
    if not lineas: return False, 0
    top = lineas[0]
    confirmacion = 0
    for c in closes[-30:]:
        if abs(c - top['precio'])/top['precio'] < 0.003:
            confirmacion += 1
    fuerza_chalan = (confirmacion/30*100 + top['fuerza'])/2
    es_valida = top['rebotes'] >= 4 and fuerza_chalan > 70 and top['fuerza'] > 75
    return es_valida, fuerza_chalan

def get_bolas_snowball(simbolo):
    # VATO 3 - BOLA DE NIEVE + JEFE
    base = BOLA_NY if simbolo in ["NVDA", "TSLA", "XAUUSD"] else BOLA_CRYPTO
    ganancia = ESTADO["ganancia_total"]
    bola = base + (ganancia * 0.2) # Crece 20% de ganancia
    # JEFE 1 vez al dia
    hoy = datetime.now().strftime("%Y-%m-%d")
    key = f"{simbolo}_{hoy}"
    if key not in ESTADO["jefe_cazo_hoy"]:
        # Si es JEFE, bola grande
        tope = TOPES["ny"] if simbolo in ["NVDA", "TSLA", "XAUUSD"] else TOPES["crypto"]
        bola_jefe = min(tope, bola * BOLA_JEFE_MULT)
        return bola, bola_jefe, True # base, jefe, puede_cazar
    else:
        return bola, bola, False

# ========== DASHBOARD ==========
@app.route('/')
def dashboard():
    html = """
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{background:#000;color:#fff;font-family:Arial;padding:10px}
   .card{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:8px 0}
   .verde{color:#00ff88}.naranja{color:orange}.btn{background:#00ff88;color:#000;padding:10px 20px;border-radius:8px;text-decoration:none;display:inline-block;margin:5px}
    </style></head><body>
    <h1>MAQUINA DE HACER DINERO 💰</h1>
    <h3>V47 DOBLE CANDADO - MAQUINA + CHALAN + JEFE</h3>
    """
    auto_txt = "AUTO ON 🟢" if ESTADO["auto"] else "AUTO OFF 🔴"
    html += f'<div class="card">Estado: <b class="verde">{auto_txt}</b> | Gan: ${ESTADO["ganancia_total"]:.2f} | Perdidas seguidas: {ESTADO["perdidas_seguidas"]}</div>'

    for s in SYMBOLS:
        precio = get_precio(s)
        bola_base, bola_jefe, puede = get_bolas_snowball(s)
        jefe_txt = f"JEFE LISTO ${bola_jefe:.0f}" if puede else "JEFE YA CAZO HOY"
        html += f'<div class="card"><b>{s}</b> ${precio:.2f} | Bola ${bola_base:.0f} | <span class="naranja">{jefe_txt}</span><br><a class="btn" href="/grafica/{s}">VER GRAFICA PRO 📈</a></div>'

    html += '<div class="card">MAQUINA analiza + CHALAN confirma = BOLA GRANDE | Sin posiciones - Escaneando lineas...</div>'
    html += '</body></html>'
    return html

# ========== GRAFICA ULTRA PRO LIVE ==========
@app.route('/grafica/<simbolo>')
def grafica(simbolo):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import io, base64, yfinance as yf

        # Trae 100 velas 5min LIVE
        if simbolo == "XAUUSD":
            df = yf.Ticker("GC=F").history(period="1d", interval="5m")
            closes = df['Close'].tolist()[-100:]
            highs = df['High'].tolist()[-100:]
            lows = df['Low'].tolist()[-100:]
            opens = df['Open'].tolist()[-100:]
        else:
            par = f"{simbolo}/USD" if simbolo!= "BTC" else "XBT/USD"
            ohlc = kraken_request('OHLC', {'pair': par, 'interval': 5})
            k = list(ohlc.keys())[0]
            data = ohlc[k][-100:]
            opens = [float(x[1]) for x in data]
            highs = [float(x[2]) for x in data]
            lows = [float(x[3]) for x in data]
            closes = [float(x[4]) for x in data]

        precio_actual = closes[-1]
        lineas = detectar_lineas_automaticas(closes)
        es_jefe, fuerza = chalan_confirma(lineas, closes)

        # PLOT ULTRA PRO
        fig = plt.figure(figsize=(12, 7), facecolor='black')
        ax = plt.subplot2grid((4,1), (0,0), rowspan=3, facecolor='black')
        ax2 = plt.subplot2grid((4,1), (3,0), facecolor='black')

        # Velas
        for i in range(len(closes)):
            color = '#00ff88' if closes[i] >= opens[i] else '#ff4444'
            ax.plot([i,i], [lows[i], highs[i]], color=color, linewidth=1)
            ax.plot([i,i], [opens[i], closes[i]], color=color, linewidth=3)

        # Lineas MAQUINA + CHALAN
        for l in lineas[:6]:
            col = '#00ff00' if l['rebotes'] >= 4 else '#ffaa00'
            style = '-' if l['rebotes'] >= 4 else '--'
            ax.axhline(l['precio'], color=col, linestyle=style, linewidth=1.2, alpha=0.8)
            ax.text(2, l['precio'], f" {l['precio']:.2f} {l['rebotes']}R {l['fuerza']:.0f}%", color=col, fontsize=9, fontweight='bold', backgroundcolor='black')

        # Precio actual linea
        ax.axhline(precio_actual, color='white', linestyle=':', alpha=0.5)
        titulo_jefe = "🔥 JEFE ACTIVO - DOBLE CANDADO" if es_jefe else "MAQUINA ESCANEANDO"
        ax.set_title(f'MAQUINA DE HACER DINERO 💰 | {simbolo} ${precio_actual:.2f} | {titulo_jefe} Fuerza {fuerza:.0f}%', color='white', fontsize=13, fontweight='bold')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.1)

        # RSI
        rsi_vals = []
        for i in range(14, len(closes)):
            g = sum(max(0, closes[j]-closes[j-1]) for j in range(i-13, i+1))/14
            l = sum(max(0, closes[j-1]-closes[j]) for j in range(i-13, i+1))/14
            rsi_vals.append(100 - (100/(1+g/(l+0.0001))))
        ax2.plot(rsi_vals, color='#00ffff', linewidth=1.5)
        ax2.axhline(70, color='red', ls='--', alpha=0.4)
        ax2.axhline(30, color='green', ls='--', alpha=0.4)
        ax2.set_ylim(0,100)
        ax2.tick_params(colors='white')

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', facecolor='black', dpi=150)
        buf.seek(0)
        img = base64.b64encode(buf.read()).decode()
        plt.close()

        return f'<html style="background:#000;color:#fff;font-family:Arial"><body style="margin:0;padding:10px"><h2>MAQUINA DE HACER DINERO 💰 - {simbolo} LIVE</h2><p>Precio: ${precio_actual:.2f} | Lineas: {len(lineas)} | CHALAN: {"CONFIRMA ✅" if es_jefe else "Buscando..."}</p><img src="data:image/png;base64,{img}" style="width:100%;border-radius:12px;border:1px solid #333"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">← VOLVER A MAQUINA</a></body></html>'
    except Exception as e:
        return f'Error grafica PRO {simbolo}: {e}'

# ========== BOT TELEGRAM ==========
@bot.message_handler(commands=['start', 'dashboard'])
def start(m):
    bot.send_message(m.chat.id, f"MAQUINA DE HACER DINERO 💰 V47 DOBLE CANDADO\nAUTO {'ON 🟢' if ESTADO['auto'] else 'OFF 🔴'}\nCap ${CAPITAL_BASE}+${ESTADO['ganancia_total']:.2f}\nBola ${BOLA_CRYPTO}/${BOLA_NY} | JEFE x{BOLA_JEFE_MULT}\nPerdidas seguidas: {ESTADO['perdidas_seguidas']}")

@app.route('/webhook', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

@app.route('/check')
def check():
    return "MAQUINA DE HACER DINERO V47 LIVE"

if __name__ == '__main__':
    print("MAQUINA DE HACER DINERO 💰 V47 ULTRA PRO LIVE - MAQUINA + CHALAN + JEFE 1x DIA")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
