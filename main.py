from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json, os

app = FastAPI()

def load():
    try:
        with open("state.json","r") as f:
            return json.load(f)
    except:
        return {"disponible_usd":500,"bloqueado_usd":0,"gan_acum":0,"disponible_m":500,"bloqueado_m":0,"gan_mt5":0,"max_entradas":8,"max_m":8,"pos":[],"pos_m":[]}

def save(s):
    with open("state.json","w") as f:
        json.dump(s,f)

def safe_html(fn):
    try:
        if os.path.exists(fn):
            with open(fn,"r",encoding="utf-8") as f:
                return HTMLResponse(f.read())
    except:
        pass
    return HTMLResponse(f"<h1>No existe {fn}</h1>", status_code=404)

@app.get("/")
async def root():
    return safe_html("index.html")

@app.get("/dashboard")
async def dash():
    return safe_html("dashboard.html")

@app.get("/dashboard.html")
async def dash_html():
    return safe_html("dashboard.html")

@app.get("/dashboard_mt5.html")
async def dash_mt5():
    return safe_html("dashboard_mt5.html")

@app.get("/dual_v5.html")
async def dual():
    return safe_html("dual_v5.html")

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
async def restore(req:Request):
    s=await req.json()
    save(s)
    return {"ok":True}

@app.post("/telegram")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        return {"ok": True}
    except:
        return {"ok": True}
