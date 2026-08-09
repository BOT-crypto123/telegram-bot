import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
URL_BASE = f"https://api.telegram.org/bot{TOKEN}"

@app.get("/")
def root():
    return {"status": "BOT LIVE V513 OK", "token_ok": bool(TOKEN)}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("WEBHOOK:", data)
    message = data.get("message")
    if not message: return {"ok": True}

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").upper()

    reply = f"Recibi: {text} - Bot LIVE ✅"
    if "BTC" in text:
        reply = "BTC LIVE - Precio OK 🚀"

    async with httpx.AsyncClient() as c:
        await c.post(f"{URL_BASE}/sendMessage", json={"chat_id": chat_id, "text": reply})

    return {"ok": True}
