import os, json, requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
FILE = "state.json"
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage" if TOKEN else ""

def load():
    try:
        with open(FILE,"r") as f: return json.load(f)
    except:
        return {"disponible_usd":500.0,"bloqueado_usd":0.0,"gan_acum":0.0,"disponible_m":500.0,"bloqueado_m":0.0,"gan_mt5":0.0,"max_entradas":8,"max_m":8}

def save(s):
    with open(FILE,"w") as f: json.dump(s,f)

def send(chat_id,text):
    if not TOKEN: return
    try: requests.post(URL, json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}, timeout=5)
    except: pass

@app.get("/")
async def root():
    try:
        with open("index.html","r",encoding="utf-8") as f: return HTMLResponse(f.read())
    except: return HTMLResponse("no index")

@app.get("/{name}.html")
async def html(name:str):
    try:
        with open(f"{name}.html","r",encoding="utf-8") as f: return HTMLResponse(f.read())
    except: return HTMLResponse("no html", status_code=404)

@app.get("/api/state")
async def get_state():
    s=load()
    return s

@app.post("/api/state")
async def post_state(req:Request):
    s=load()
    try:
        data=await req.json()
        for k,v in data.items():
            if k in s:
                try: s[k]=float(v)
                except: s[k]=v
        save(s)
    except: pass
    return s

# ESTA ES LA RUTA QUE BORRASTE Y CAUSA 404
@app.post("/telegram")
@app.post("/telegram/")
async def telegram(req:Request):
    s=load()
    tb = s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0)
    tm = s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0)
    try:
        data=await req.json()
        msg=data.get("message",{}) or data.get("edited_message",{})
        chat_id=msg.get("chat",{}).get("id")
        text=(msg.get("text","") or "").upper()
        if not chat_id: return JSONResponse({"ok":True})
        
        if "DASHBOARD" in text or "/START" in text or "START" in text:
            txt=f"DUAL V5 LIVE\nBINANCE: ${tb:.2f}\nMT5: ${tm:.2f}\n\nD:BINANCE ${s.get('disponible_usd',0):.2f} B:${s.get('bloqueado_usd',0):.2f} G:${s.get('gan_acum',0):.2f}\nD:MT5 ${s.get('disponible_m',0):.2f} B:${s.get('bloqueado_m',0):.2f} G:${s.get('gan_mt5',0):.2f}\n\nEntra: https://telegram-bot-cijp.onrender.com/"
            send(chat_id,txt)
    except Exception as e:
        print("tel err",e)
    return JSONResponse({"ok":True})
