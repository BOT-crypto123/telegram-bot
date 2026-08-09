import os, json, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN","")
BASE = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "/tmp/bot_state.json"
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
        async
