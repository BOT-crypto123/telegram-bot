import os, json, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN","")
BASE = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "/tmp/bot_state.json"
MONEDAS = ["BTC","ETH","SOL","XRP"]
CAPITAL = 1000.0
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME","")
DASH_URL = f"https://{HOST}/dashboard"

def load_state():
    try:
        with open(STATE_FILE,"r") as f:
            return json.load(f)
    except:
        return {"auto":False,"chat_id":None,"virtual_balance":CAPITAL,"holdings":{},"trade_history":[]}

def save_state(s):
    with open(STATE_FILE,"w") as f:
        json.dump(s,f)

async def get_data(sym):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", headers={"User-Agent":"Mozilla/5.0"})
            return float(r.json()["data"]["amount"]), 0.0
    except:
        return 65153.0, 0.0

async def get_candles(sym):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            url = f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity=3600"
            r = await c.get(url, headers={"User-Agent":"Mozilla/5.0"})
            data = sorted(r.json())[-50:]
            return [x[4] for x in data]
    except:
        return [65000,65100,65200,65153]

async def send_msg(chat_id,text,moneda="BTC",btns=False):
    if btns:
        kb = {"inline_keyboard":[[{"text":f"GRAFICA {moneda}","url":f"https://www.tradingview.com/symbols/{moneda}USDT/"},{"text":"DASHBOARD","url":DASH_URL}],[{"text":f"COMPRAR {moneda}","callback_data":f"BUY_{moneda}"},{"text":f"VENDER {moneda}","
