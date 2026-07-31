import os, requests

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
INVERSION = 1000
MONEDAS = ["BTC", "ETH", "XRP"]

def get_datos(s):
    try:
        m = {"BTC":"bitcoin", "ETH":"ethereum", "XRP":"ripple"}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={m[s]}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=10).json()
        precio = r[m[s]]["usd"]
        cambio = r[m[s]].get("usd_24h_change", 0)
        return precio, cambio
    except:
        return None, None

def main():
    mensaje = f"⏰ REPORTE PRO - Vicente\n💰 Inversion: ${INVERSION}\n\n"
    alertas = ""

    for moneda in MONEDAS:
        precio, cambio = get_datos(moneda)
        if not precio:
            continue

        if cambio <= -2:
            alertas += f"🟢 {moneda} BAJO {cambio:.2f}% - OPORTUNIDAD COMPRA: ${precio:,.2f}\n"
        elif cambio >= 2:
            alertas += f"🔴 {moneda} SUBIO +{cambio:.2f}% - CONSIDERA VENDER: ${precio:,.2f}\n"

        mensaje += f"• {moneda}: ${precio:,.2f} ({cambio:+.2f}%)\n"

    if alertas:
        mensaje = f"🚨🚨 ALERTA 2% 🚨🚨\n{alertas}\n" + mensaje
    else:
        mensaje += "\n😴 Mercado estable (sin movimientos de +-2%)."

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje})

if __name__ == "__main__":
    main()
