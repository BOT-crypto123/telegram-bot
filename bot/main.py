import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN","")
BASE = f"https://api.telegram.org/bot{TOKEN}"

print(f"=== BOT INICIADO V515 === TOKEN len={len(TOKEN)}")

@app.get("/")
def home():
    return {"status":"V515 LIVE", "token_ok": bool(TOKEN), "url": "https://telegram-bot-cijp.onrender.com"}

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    print(f"DATA: {data}")
    msg = data.get("message",{})
    chat_id = msg.get("chat",{}).get("id")
    text = msg.get("text","")
    print(f">>> MENSAJE RECIBIDO: '{text}' de {chat_id}")

    if chat_id:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(f"{BASE}/sendMessage", json={"chat_id": chat_id, "text": f"V515 LIVE ✅ Recibí: {text}"})
                print(f"RESPUESTA TELEGRAM: {r.status_code} {r.text}")
        except Exception as e:
            print(f"ERROR ENVIANDO: {e}")
    
    return {"ok": True}
