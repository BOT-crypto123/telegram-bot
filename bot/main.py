import os, json, asyncio, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
from zoneinfo import ZoneInfo
import datetime as dt

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN","")
BASE = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "/tmp/bot_state.json"
MONEDAS = ["BTC","ETH","SOL","XRP"]
COMISION = 0.002
CAPITAL_INICIAL = 1000.0
DASHBOARD_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','tu-bot.onrender.com')}/dashboard"

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except:
        return {"auto": False, "chat_id": None, "ultima_senal": {}, "precios_compra": {}, "virtual_balance": CAPITAL_INICIAL, "holdings": {}, "trade_history": []}
def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(f,s)

async def get_data(symbol):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT")
            d = r.json()
            return float(d["lastPrice"]), float(d["priceChangePercent"])
    except: return 0,0

async def send_msg(chat_id, text, moneda="BTC", show_trade_buttons=False):
    if show_trade_buttons:
        kb = {"inline_keyboard": [[{"text": f"📊 GRÁFICA {moneda}", "url": f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text": "📈 DASHBOARD", "url": DASHBOARD_URL}],[{"text": f"🟢 COMPRAR {moneda} SIM", "callback_data": f"BUY_{moneda}"},{"text": f"🔴 VENDER {moneda} SIM", "callback_data": f"SELL_{moneda}"}]]}
    else:
        kb = {"inline_keyboard": [[{"text": f"📊 GR
