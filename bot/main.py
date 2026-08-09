import os, json, asyncio, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN","")
BASE = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "/tmp/bot_state.json"
MONEDAS = ["BTC","ETH","SOL","XRP"]
COMISION = 0.002
CAPITAL = 1000.0
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME","tu-app.onrender.com")
DASH_URL = f"https://{HOST}/dashboard"
MAPA = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple"}

def load_state():
    try:
        with open(STATE_FILE,"r") as f:
            return json.load(f)
    except:
        return {"auto": False, "chat_id": None, "virtual_balance": CAPITAL, "holdings": {}, "trade_history": []}

def save_state(s):
    with open(STATE_FILE,"w") as f:
        json.dump(s,f)

async def get_data(sym):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            try:
                r = await c.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}USDT", headers={"User-Agent": "Mozilla/5.0"})
                d = r.json()
                if "lastPrice" in d:
                    return float(d["lastPrice"]), float(d["priceChangePercent"])
            except:
                pass
            cg_id = MAPA.get(sym, "bitcoin")
            r2 = await c.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true")
            d2 = r2.json()
            price = float(d2[cg_id]["usd"])
            change = float(d2[cg_id].get("usd_24h_change", 0) or 0)
            return price, change
    except:
        return 0.0, 0.0

async def send_msg(chat_id, text, moneda="BTC", btns=False):
    if btns:
        kb = {"inline_keyboard
