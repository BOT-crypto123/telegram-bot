from flask import Flask, send_from_directory, jsonify, request
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# --- RUTAS PRINCIPALES V6 REAL ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/dashboard')
@app.route('/dashboard.html')
def dash_binance():
    return send_from_directory(app.static_folder, 'dashboard.html')

@app.route('/dashboard_mt5')
@app.route('/dashboard_mt5.html')
def dash_mt5():
    return send_from_directory(app.static_folder, 'dashboard_mt5.html')

# Sirve cualquier otro archivo (css, js, etc)
@app.route('/<path:filename>')
def serve_any(filename):
    file_path = os.path.join(app.static_folder, filename)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, filename)
    # Si no existe, regresa index para no mostrar "no html" blanco
    if filename.endswith('.html'):
        return f"<h3 style='font-family:system-ui'>No se encontró {filename} - revisa GitHub que sí esté subido</h3>", 404
    return send_from_directory(app.static_folder, 'index.html')

# --- API QUE LEE TU BOT DE TELEGRAM V6 ---
@app.route('/api/state')
def state():
    # V6 REAL - lee en cero, es lo que manda a Telegram
    return jsonify({
        "version": "DUAL V6 REAL",
        "capital_binance": 500.00,
        "capital_mt5": 500.00,
        "ganancia_binance": 0.00,
        "ganancia_mt5": 0.00,
        "bola_binance": 62.50,
        "bola_mt5": 62.50,
        "status": "LIVE REAL SIN MERMA - BTC+ETH ONLY"
    })

@app.route('/api/ping')
def ping():
    return "V6 REAL LIVE", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
