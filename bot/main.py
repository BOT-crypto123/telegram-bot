import os, json, asyncio, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
from zoneinfo import ZoneInfo
import datetime as dt

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN","")
BASE = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "/tmp/bot_state.json"
MONEDAS = ["BTC","ETH","SOL","XRP"]
COMISION = 0.002
CAPITAL_INICIAL = 1000.0
DASHBOARD_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME','tu-bot.onrender.com')}/dashboard"

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except:
        return {"auto": False, "chat_id": None, "ultima_senal": {}, "precios_compra": {}, "virtual_balance": CAPITAL_INICIAL, "holdings": {}, "trade_history": []}
def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(f,s)

async def get_data(symbol):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT")
            d = r.json()
            return float(d["lastPrice"]), float(d["priceChangePercent"])
    except: return 0,0

async def send_msg(chat_id, text, moneda="BTC", show_trade_buttons=False):
    if show_trade_buttons:
        kb = {"inline_keyboard": [[{"text": f"GRAFICA {moneda}", "url": f"https://www.tradingview.com/symbols/{moneda}USDT/"}, {"text": "DASHBOARD", "url": DASHBOARD_URL}], [{"text": f"COMPRAR {moneda} SIM", "callback_data": f"BUY_{moneda}"}, {"text": f"VENDER {moneda} SIM", "callback_data": f"SELL_{moneda}"}]]}
    else:
        kb = {"inline_keyboard": [[{"text": f"GRAFICA {moneda}", "url": f"https://www.tradingview.com/symbols/{moneda}USDT/"}, {"text": "DASHBOARD", "url": DASHBOARD_URL}]]}
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{BASE}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "reply_markup": kb})

async def send_menu(chat_id, text):
    kb = {"keyboard": [[{"text": "BTC"}, {"text": "ETH"}, {"text": "SOL"}, {"text": "XRP"}], [{"text": "AUTO ON"}, {"text": "AUTO OFF"}], [{"text": "ESTADO"}, {"text": "PORTAFOLIO"}, {"text": "DASHBOARD"}]], "resize_keyboard": True}
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{BASE}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "reply_markup": kb})

async def cq_answer(id, txt):
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{BASE}/answerCallbackQuery", json={"callback_query_id": id, "text": txt})

async def send_daily_summary():
    s=load_state()
    if not s.get("chat_id"): return
    total_val=s.get("virtual_balance",0)
    txt_dia=""; gan_hoy=0; trades_hoy=0
    hoy=datetime.now().strftime("%d/%m")
    for m in MONEDAS:
        price,_=await get_data(m)
        hold=s.get("holdings",{}).get(m)
        if hold:
            val=hold["amount"]*price
            total_val+=val
            gan=((price-hold["entry"])/hold["entry"]*100)-(COMISION*100)
            txt_dia+=f"{m}: ${val:,.2f} ({gan:+.2f}%)\n"
    for t in s.get("trade_history",[]):
        if hoy in t["fecha"] and "VENTA" in t["tipo"]:
            trades_hoy+=1; gan_hoy+=t["ganancia"]
    total_pl=total_val-CAPITAL_INICIAL
    total_pl_pct=(total_val-CAPITAL_INICIAL)/CAPITAL_INICIAL*100
    resumen=f"RESUMEN 10PM\nTotal: ${total_val:,.2f}\nEfectivo: ${s['virtual_balance']:,.2f}\nP&L Total: ${total_pl:+.2f} ({total_pl_pct:+.2f}%)\nHoy: {gan_hoy:+.2f}% {trades_hoy} trades\n{txt_dia}\n{DASHBOARD_URL}"
    await send_msg(s["chat_id"], resumen, "BTC")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    s=load_state()
    rows=""
    for h in reversed(s.get("trade_history",[])[-20:]):
        color="#00e676" if h["ganancia"]>=0 else "#ff5252"
        rows+=f"<tr><td>{h['fecha']}</td><td>{h['tipo']} {h['moneda']}</td><td>${h['precio']:,.2f}</td><td>${h['monto']:,.2f}</td><td style='color:{color}'>{h['ganancia']:+.2f}%</td></tr>"
    portfolio_html=""
    total_val=s.get("virtual_balance",0)
    for m in MONEDAS:
        price,_=await get_data(m)
        hold=s.get("holdings",{}).get(m)
        if hold:
            val=hold["amount"]*price
            total_val+=val
            gan=((price-hold["entry"])/hold["entry"]*100)-(COMISION*100)
            c="#00e676" if gan>=0 else "#ff5252"
            portfolio_html+=f"<div style='background:#1a1f2e;padding:12px;border-radius:10px;margin:8px 0'><b>{m}</b> {hold['amount']:.6f} @ ${hold['entry']:,.2f} -> ${price:,.2f} <span style='color:{c}'>{gan:+.2f}%</span></div>"
    return f"<html><head><meta name='viewport' content='width=device-width'><style>body{{background:#0f1219;color:white;font-family:Arial;padding:20px}} table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #333;padding:8px}}</style></head><body><h1>V860 V861 FIX</h1><h2>Bal: ${s.get('virtual_balance',0):,.2f} Total: ${total_val:,.2f}</h2>{portfolio_html}<table><tr><th>Fecha</th><th>Op</th><th>Precio</th><th>Monto</th><th>P&L</th></tr>{rows}</table></body></html>"

@app.post("/webhook
