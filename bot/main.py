import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELE_TOKEN") or ""
print(f"TOKEN CARGADO: {TOKEN[:10]}...")

@app.get("/")
def home():
    return "BOT V512 LIVE - OK"

@app.post("/webhook")
async def webhook(req: Request):
    try:
        data = await req.json()
        print(f"WEBHOOK RECIBIDO: {data}")
        msg = data.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")
        
        if chat_id and TOKEN:
            async with httpx.AsyncClient() as client:
                await client.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                  json={"chat_id": chat_id, "text": f"Recibi: {text} - V512 OK"})
            print(f"RESPONDI A {chat_id}")
    except Exception as e:
        print(f"ERROR: {e}")
    return {"ok": True}
