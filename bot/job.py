import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # Asegúrate de tenerlo en Secrets

def get_btc():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5).json()
        return float(r['price'])
    except:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
        return float(r['bitcoin']['usd'])

precio = get_btc()

# Texto del reporte
texto = f"⏰ REPORTE BTC - Vicente\n\n💰 BTC: ${precio:,.2f}\n\n¿Qué hacemos?"

# BOTONES COMPRAR / VENDER
teclado = {
    "inline_keyboard": [
        [
            {"text": "🟢 COMPRAR", "callback_data": "comprar"},
            {"text": "🔴 VENDER", "callback_data": "vender"}
        ],
        [
            {"text": "📊 Ver gráfica", "url": "https://www.tradingview.com/symbols/BTCUSDT/"}
        ]
    ]
}

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {
    "chat_id": CHAT_ID,
    "text": texto,
    "reply_markup": teclado
}

resp = requests.post(url, json=data)
print(resp.text)
