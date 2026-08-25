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
            s=json.load(f)
            # Migra a V6 si viene de V5
            if "disponible_usd" in s:
                return s
            return s
    except:
        pass
    # V6 REAL - CERO, SIN MERMA BTC+ETH ONLY
    return {
        "disponible_usd":500.0,
        "bloqueado_usd":0.0,
        "gan_acum":0.0,
        "disponible_m":500.0,
        "bloqueado_m":0.0,
        "gan_mt5":0.0,
        "max_entradas":2, # SOLO BTC+ETH PARA NO MERMAR
        "max_m":5,
        "version":"V6 REAL LIVE"
    }

def save(s):
    try:
        with open(FILE,"w") as f: json.dump(s,f)
    except: pass

def send(chat_id,text):
    if not TOKEN: return
    try:
        requests.post(URL, json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print("send err",e)

@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("index.html","r",encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        print("root err",e)
        return HTMLResponse(f"no index - {e}", status_code=404)

@app.get("/{name}.html", response_class=HTMLResponse)
async def html(name:str):
    fname = f"{name}.html"
    try:
        # Evita path traversal
        if ".." in name or "/" in name:
            return HTMLResponse("no html", status_code=404)
        with open(fname,"r",encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        print(f"html err {fname}: {e}")
        return HTMLResponse(f"no html {fname}", status_code=404)

@app.get("/api/state")
async def get_state():
    s=load()
    tb = s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0)
    tm = s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0)
    # Agrega calculados para tu portada V6
    s["total_binance"] = tb
    s["total_mt5"] = tm
    s["bola_binance"] = tb / 8
    s["bola_mt5"] = tm / 8
    s["capital_binance"] = tb
    s["capital_mt5"] = tm
    return s

@app.post("/api/state")
async def post_state(req:Request):
    s=load()
    try:
        data=await req.json()
        for k,v in data.items():
            if k in s or k in ["gan_acum","gan_mt5","disponible_usd","disponible_m"]:
                try:
                    s[k]=float(v)
                except:
                    s[k]=v
        save(s)
    except Exception as e:
        print("post state err",e)
    return s

# RUTA QUE TE DABA 404 - YA BLINDADA PARA LIVE
@app.post("/telegram")
@app.post("/telegram/")
@app.post("/webhook")
async def telegram(req:Request):
    s=load()
    tb = s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0)
    tm = s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0)
    bola_b = tb/8
    bola_m = tm/8
    try:
        data=await req.json()
        msg=data.get("message",{}) or data.get("edited_message",{}) or {}
        chat_id=msg.get("chat",{}).get("id")
        text=(msg.get("text","") or "").upper()
        if not chat_id:
            return JSONResponse({"ok":True})

        if "DASHBOARD" in text or "/START" in text or "START" in text or "VICENTE" in text:
            txt=(
                f"*DUAL V6 REAL LIVE*\n"
                f"BINANCE: ${tb:.2f} BOLA ${bola_b:.2f}\n"
                f"MT5: ${tm:.2f} BOLA ${bola_m:.2f}\n\n"
                f"D:BINANCE ${s.get('disponible_usd',0):.2f} B:${s.get('bloqueado_usd',0):.2f} G:${s.get('gan_acum',0):.2f}\n"
                f"D:MT5 ${s.get('disponible_m',0):.2f} B:${s.get('bloqueado_m',0):.2f} G:${s.get('gan_mt5',0):.2f}\n\n"
                f"Entra: https://telegram-bot-cijp.onrender.com/"
            )
            send(chat_id,txt)
    except Exception as e:
        print("tel err",e)
    return JSONResponse({"ok":True})

@app.get("/health")
async def health():
    return {"status":"V6 REAL LIVE OK"}
