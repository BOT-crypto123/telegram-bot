import os, requests

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
MONEDAS = ["BTC", "ETH", "XRP"]
MAPA = {"BTC":"bitcoin", "ETH":"ethereum", "XRP":"ripple"}

def get_datos(s):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={MAPA[s]}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=10).json()
        return r[MAPA[s]]["usd"], r[MAPA[s]].get("usd_24h_change",0)
    except:
        return None, None

def main():
    reporte = ""
    alertas = ""
    for m in MONEDAS:
        precio, cambio = get_datos(m)
        if not precio: continue
        reporte += f"• {m}: ${precio:,.2f} ({cambio:+.2f}%)\n"
        if cambio <= -2:
            alertas += f"🟢 {m} BAJÓ {cambio:.2f}% - OPORTUNIDAD!\n"
        elif cambio >= 2:
            alertas += f"🔴 {m} SUBIÓ +{cambio:.2f}% - VENDE!\n"

    if alertas:
        texto = f"🚨 ALERTA 2% 🚨\n{alertas}\n⏰ REPORTE - Vicente\n{reporte}\n¿Qué hacemos?"
    else:
        texto = f"⏰ REPORTE BTC - Vicente\n\n{reporte}\n😴 Mercado estable (sin +-2%)\n¿Qué hacemos?"

    teclado = {
        "inline_keyboard": [
            [{"text": "🟢 COMPRAR", "callback_data": "comprar"}, {"text": "🔴 VENDER", "callback_data": "vender"}],
            [{"text": "📊 Ver gráfica", "url": "https://www.tradingview.com/symbols/BTCUSDT/"}]
        ]
    }

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": texto, "reply_markup": teclado})

if __name__ == "__main__":
    main()
