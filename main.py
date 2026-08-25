from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json, os, asyncio, random

app = FastAPI()

FILE = "state.json"

def load():
    try:
        with open(FILE,"r") as f:
            return json.load(f)
    except:
        return {
            "disponible_usd":500.0,"bloqueado_usd":0.0,"gan_acum":0.0,
            "disponible_m":500.0,"bloqueado_m":0.0,"gan_mt5":0.0,
            "max_entradas":8,"max_m":8,
            "pos":[],"pos_m":[],"historial":[]
        }

def save(s):
    with open(FILE,"w") as f:
        json.dump(s,f)

@app.get("/")
async def root():
    with open("index.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/state")
async def state():
    s=load()
    s["total_b"]=s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"]
    s["total_m"]=s["disponible_m"]+s["bloqueado_m"]+s["gan_mt5"]
    return s

@app.post("/api/state")
async def update_state(req: Request):
    data = await req.json()
    s=load()
    for k,v in data.items():
        if k in s:
            s[k]=float(v)
    save(s)
    return s

# Sirve los otros html
@app.get("/{path}.html")
async def htmls(path: str):
    try:
        with open(f"{path}.html","r",encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except:
        return HTMLResponse("no existe", status_code=404)
