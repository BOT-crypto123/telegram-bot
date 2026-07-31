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

def mandar_mensaje(texto, moneda):
    # Botones específicos de ESA moneda
    teclado = {
        "inline_keyboard": [
            [
                {"text": f"🟢 COMPRAR {moneda}", "callback_data": f"comprar_{moneda}"},
                {"text": f"🔴 VENDER {moneda}", "callback_data": f"vender_{moneda}"}
            ],
            [{"text": f"📊 Ver gráfica de {moneda}", "url": f"https://www.tradingview.com/symbols/{moneda}USDT/"}]
        ]
    }
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": texto, "reply_markup": teclado, "parse_mode": "Markdown"})

def main():
    for m in MONEDAS:
        precio, cambio = get_datos(m)
        if precio is None: continue

        # SOLO SI SE MUEVE +-2%
        if cambio <= -2:
            texto = f"🚨 *ALERTA DE COMPRA* 🚨\n\n🟢 *{m} BAJÓ {cambio:.2f}%*\n💰 Precio actual: ${precio:,.2f}\n\n📉 Cayó más de 2% en 24h - ¡OPORTUNIDAD!\n\n¿Compramos {m}?"
            mandar_mensaje(texto, m)

        elif cambio >= 2:
            texto = f"🚨 *ALERTA DE VENTA* 🚨\n\n🔴 *{m} SUBIÓ +{cambio:.2f}%*\n💰 Precio actual: ${precio:,.2f}\n\n📈 Subió más de 2% en 24h - ¡GANANCIA!\n\n¿Vendemos {m}?"
            mandar_mensaje(texto, m)

    print("Revisión terminada. Solo se mandó alerta si hubo +-2%")

if __name__ == "__main__":
    main()
