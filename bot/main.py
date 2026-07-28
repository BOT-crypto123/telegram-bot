import os, asyncio, aiohttp
from telegram import Bot
import numpy as np

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT"]
NAMES = {"XRPUSDT":"XRP", "BTCUSDT":"BTC", "ETHUSDT":"ETH"}

def calc_ema(prices, period):
    if len(prices) < period: return None
    ema = np.mean(prices[:period])
    k = 2/(period+1)
    for p in prices[period:]:
        ema = p*k + ema*(1-k)
    return ema

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50
    deltas = np.diff(prices)
    gains = np.where(deltas>0, deltas, 0)
    losses = np.where(deltas<0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0: return 100
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

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
        return f"{NAMES[symbol]}: ${price:.4f if symbol=='XRPUSDT' else '.0f'} - {sig} (RSI {rsi:.0f} EMA20 {ema20:.2f})"
    except Exception as e:
        return f"{NAMES[symbol]}: Error {e}"

async def main():
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="🤖 Bot Vicente ACTIVADO\nXRP + BTC + ETH\nReporte cada 2 horas 📊")

    while True:
        try:
            report = "📊 REPORTE 2H - VICENTE\n\n"
            for sym in SYMBOLS:
                line = await get_signal(sym)
                report += line + "\n\n"
            report += "🌐 Ver grafica: https://telegram-bot-r3qd.onrender.com"
            await bot.send_message(chat_id=CHAT_ID, text=report)
        except Exception as e:
            print(f"Error reporte: {e}")
        await asyncio.sleep(7200) # 2 horas
