from flask import Flask, send_from_directory, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    # Sirve dashboard.html, dashboard_mt5.html y cualquier otro html
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return "no html", 404

@app.route('/api/state')
def state():
    # Para que el bot de Telegram lea el estado
    return jsonify({
        "capital_binance": 500,
        "capital_mt5": 500,
        "ganancia_binance": 0,
        "ganancia_mt5": 0
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
