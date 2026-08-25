from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import json, os, requests

app = FastAPI()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
RENDER_URL = "https://telegram-bot-cijp.onrender.com/"

def load():
    try:
        with open("state.json","r") as f:
            return json.load(f)
    except:
        return {
            "disponible_usd":500,"bloqueado_usd":0,"gan_acum":0,
            "disponible_m":500,"bloqueado_m":0,"gan_mt5":0,
            "max_entradas":8,"max_m":8,
            "pos":[],"pos_m":[],"pos_m_short":[],
            "historial":[],"historial_m":[]
        }

def save(s):
    with open("state.json","w") as f:
        json.dump(s,f)

def safe_html(fn):
    if os.path.exists(fn):
        with open(fn,"r",encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse(f"falta {fn}", status_code=404)

@app.get("/")
async def root():
    return safe_html("index.html")

@app.get("/dashboard")
async def dash1():
    return safe_html("dashboard.html")

@app.get("/dashboard.html")
async def dash2():
    return safe_html("dashboard.html")

@app.get("/dashboard_mt5.html")
async def dash3():
    return safe_html("dashboard_mt5.html")

@app.get("/api/state")
async def state():
    s=load()
    s["total_b"]=float(s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0))
    s["total_m"]=float(s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0))
    s["bola_b"]=s["total_b"]/max(1,s.get("max_entradas",8))
    s["bola_m"]=s["total_m"]/max(1,s.get("max_m",8))
    return s

@app.get("/api/backup")
async def backup():
    return JSONResponse(load())

@app.post("/api/restore")
async def restore(req: Request):
    s=await req.json()
    save(s)
    return {"ok":True}

def send_telegram(chat_id, text):
    if not BOT_TOKEN:
        return
    try:
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload={
            "chat_id":chat_id,
            "text":text,
            "reply_markup":{"keyboard":[["DASHBOARD"]],"resize_keyboard":True}
        }
        requests.post(url,json=payload,timeout=5)
    except:
        pass

@app.post("/telegram")
async def telegram_webhook(req: Request):
    try:
        data=await req.json()
        msg=data.get("message",{})
        chat_id=msg.get("chat",{}).get("id")
        text=msg.get("text","").strip().upper()
        if not chat_id:
            return {"ok":True}
        if text in ["/START","DASHBOARD","START"]:
            s=load()
            tb=s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0)
            tm=s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0)
            send_telegram(chat_id,f"DUAL V5 LIVE\nBINANCE: ${tb:.2f}\nMT5: ${tm:.2f}\n\nEntra: {RENDER_URL}")
        return {"ok":True}
    except:
        return {"ok":True}
