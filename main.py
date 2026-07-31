import os, requests

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
INVERSION = 1000
MONEDAS = ["BTC", "ETH", "XRP"]

def get_precio(s):
    try:
        m = {"BTC":"bitcoin", "ETH":"ethereum", "XRP":"ripple"}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={m[s]}&vs_currencies=usd"
        r = requests.get(url, timeout=10).json()
        return r[m[s]]["usd"]
    except:
        return None

def main():
    mensaje = f"⏰ REPORTE PRO - Vicente\n💰 Inversion: ${INVERSION}\n\n"
    total_alerta = ""

    for moneda in MONEDAS:
        precio = get_precio(moneda)
        if not precio:
            continue

        # Lógica de Compra/Venta - CAMBIA ESTOS % SI QUIERES
        # Si quieres que sea más sensible pon 1.0, si menos pon 3.0
        if moneda == "BTC":
            # Ejemplo: Alerta si BTC baja de 63000 o sube de 67000
            if precio < 63000:
                total_alerta += f"🟢 {moneda} BARATO para COMPRAR: ${precio:,.2f} (bajo $63k)\n"
            elif precio > 67000:
                total_alerta += f"🔴 {moneda} CARO para VENDER: ${precio:,.2f} (sobre $67k)\n"

        mensaje += f"• {moneda}: ${precio:,.2f}\n"

    if total_alerta:
        mensaje = f"🚨🚨 ALERTA DE MERCADO 🚨🚨\n\n{total_alerta}\n" + mensaje
    else:
        mensaje += "\n😴 Mercado estable, sin alertas."

    # Enviar a Telegram
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje})

if __name__ == "__main__":
    main()
