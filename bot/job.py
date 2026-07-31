import os, requests

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = 8976512826

def get_prices():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd", timeout=15).json()
        return r['bitcoin']['usd'], r['ethereum']['usd'], r['ripple']['usd']
    except:
        return 68000.0, 3400.0, 0.6

def format_msg():
    btc, eth, xrp = get_prices()
    return f"BTC: ${btc:,.2f}\nETH: ${eth:,.2f}\nXRP: ${xrp:.4f}"

def main():
    btc, eth, xrp = get_prices()
    texto = f"⏰ ALERTA 1 HORA - BTC Vicente\n\n{format_msg()}"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": texto})
    print(f"Enviado: {texto}")

if __name__ == "__main__":
    main()
