import os, json, requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
FILE = "state.json"
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage" if TOKEN else ""

def load():
    try:
        with open(FILE,"r") as f:
            return json.load(f)
    except:
        return {"disponible_usd":500.0,"bloqueado_usd":0.0,"gan_acum":0.0,"disponible_m":500.0,"bloqueado_m":0.0,"gan_mt5":0.0}

def save(s):
    with open(FILE,"w") as f:
        json.dump(s,f)

def send(cid,txt):
    if not TOKEN:
        return
    try:
        requests.post(URL, json={"chat_id":cid,"text":txt,"parse_mode":"Markdown"}, timeout=5)
    except:
        pass

@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("index.html","r",encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return HTMLResponse(f"no index.html found: {e}", status_code=404)

@app.get("/api/state")
async def get_state():
    return load()

@app.post("/telegram")
@app.post("/telegram/")
async def telegram_route(req:Request):
    s=load()
    tb=s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"]
    tm=s["disponible_m"]+s["bloqueado_m"]+s["gan_mt5"]
    try:
        data=await req.json()
        msg=data.get("message",{}) or {}
        cid=msg.get("chat",{}).get("id")
        txt=(msg.get("text","") or "").upper()
        if cid and ("DASHBOARD" in txt or "START" in txt):
            send(cid,f"DUAL V6 REAL LIVE\nBINANCE: ${tb:.2f} BOLA ${tb/8:.2f}\nMT5: ${tm:.2f} BOLA ${tm/8:.2f}\n\nD:BINANCE ${s['disponible_usd']:.2f} B:${s['bloqueado_usd']:.2f} G:${s['gan_acum']:.2f}\nD:MT5 ${s['disponible_m']:.2f} B:${s['bloqueado_m']:.2f} G:${s['gan_mt5']:.2f}\n\nEntra: https://telegram-bot-cijp.onrender.com/")
    except Exception as e:
        print(f"tg error {e}")
    return JSONResponse({"ok":True})

@app.get("/health")
async def health():
    return {"ok":True}
