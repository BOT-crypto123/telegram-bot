async def get_signal(symbol):
    try:
        async with aiohttp.ClientSession() as s:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
            async with s.get(url) as r:
                data = await r.json()
                closes = [float(c[4]) for c in data]
        price = closes[-1]
        ema20 = calc_ema(closes, 20)
        ema50 = calc_ema(closes, 50)
        rsi = calc_rsi(closes, 14)

        if ema20 and ema50:
            if ema20 > ema50 and rsi < 70 and rsi > 45:
                sig = "🟢 COMPRA"
            elif ema20 < ema50 and rsi > 30:
                sig = "🔴 VENTA"
            else:
                sig = "🟡 NEUTRAL"
        else:
            sig = "🟡 NEUTRAL"

        if symbol == "XRPUSDT":
            p_str = f"${price:.4f}"
        else:
            p_str = f"${price:.0f}"

        return f"{NAMES[symbol]}: {p_str} - {sig} (RSI {rsi:.0f} EMA20 {ema20:.2f})"
    except Exception as e:
        return f"{NAMES[symbol]}: Error {e}"
