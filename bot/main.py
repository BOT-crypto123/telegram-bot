import os, json, asyncio, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
from zoneinfo import ZoneInfo
import datetime as dt

app = FastAPI()
TOKEN = os.getenv('TELEGRAM_TOKEN','')
BASE = f'https://api.telegram.org/bot{TOKEN}'
STATE_FILE = '/tmp/bot_state.json'
MONEDAS = ['BTC','ETH','SOL','XRP']
COMISION = 0.002
CAPITAL_INICIAL = 1000.0
HOST = os.getenv('RENDER_EXTERNAL_HOSTNAME','tu-bot.onrender.com')
DASHBOARD_URL = f'https://{HOST}/dashboard'

def load_state():
    try:
        with open(STATE_FILE,'r') as f:
            return json.load(f)
    except:
        return {'auto': False, 'chat_id': None, 'virtual_balance': CAPITAL_INICIAL, 'holdings': {}, 'trade_history': []}

def save_state(s):
    with open(STATE_FILE,'w') as f:
        json.dump(f,s)

async def get_data(symbol):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT')
            d = r.json()
            return float(d['lastPrice']), float(d['priceChangePercent'])
    except:
        return 0,0

async def send_msg(chat_id, text, moneda='BTC', buttons=False):
    if buttons:
        kb = {'inline_keyboard': [[{'text': f'GRAFICA {moneda}', 'url': f'https://www.tradingview.com/symbols/{moneda}USDT/'}, {'text': 'DASHBOARD', 'url': DASHBOARD_URL}], [{'text': f'COMPRAR {moneda}', 'callback_data': f'BUY_{moneda}'}, {'text': f'VENDER {moneda}', 'callback_data': f'SELL_{moneda}'}]]}
    else:
        kb = {'inline_keyboard': [[{'text': f'GRAFICA {moneda}', 'url': f'https://www.tradingview.com/symbols/{moneda}USDT/'}, {'text': 'DASHBOARD', 'url': DASHBOARD_URL}]]}
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f'{BASE}/sendMessage', json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown', 'reply_markup': kb})

async def send_menu(chat_id, text):
    kb = {'keyboard': [[{'text': 'BTC'}, {'text': 'ETH'}, {'text': 'SOL'}, {'text': 'XRP'}], [{'text': 'AUTO ON'}, {'text': 'AUTO OFF'}], [{'text': 'ESTADO'}, {'text': 'PORTAFOLIO'}]], 'resize_keyboard': True}
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f'{BASE}/sendMessage', json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown', 'reply_markup': kb})

async def cq_answer(id, txt):
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f'{BASE}/answerCallbackQuery', json={'callback_query_id': id, 'text': txt})

async def send_daily_summary():
    s = load_state()
    if not s.get('chat_id'):
        return
    total_val = s.get('virtual_balance',0)
    hoy = datetime.now().strftime('%d/%m')
    txt_dia = ''
    gan_hoy = 0
    trades_hoy = 0
    for m in MONEDAS:
        price,_ = await get_data(m)
        hold = s.get('holdings',{}).get(m)
        if hold:
            val = hold['amount']*price
            total_val += val
            gan = ((price-hold['entry'])/hold['entry']*100)
            txt_dia += f'{m}: ${val:,.2f} ({gan:+.2f}%)\n'
    for t in s.get('trade_history',[]):
        if hoy in t['fecha'] and 'VENTA' in t['tipo']:
            trades_hoy+=1
            gan_hoy+=t['ganancia']
    total_pl = total_val - CAPITAL_INICIAL
    pct = (total_val-CAPITAL_INICIAL)/CAPITAL_INICIAL*100
    msg = f'RESUMEN 10PM\nTotal: ${total_val:,.2f}\nEfectivo: ${s["virtual_balance"]:,.2f}\nP&L Total: ${total_pl:+.2f} ({pct:+.2f}%)\nHoy: {gan_hoy:+.2f}% {trades_hoy} trades\n{txt_dia}\n{DASHBOARD_URL}'
    await send_msg(s['chat_id'], msg, 'BTC')

@app.get('/dashboard', response_class=HTMLResponse)
async def dashboard():
    s = load_state()
    rows = ''
    for h in reversed(s.get('trade_history',[])[-20:]):
        rows += f"<tr><td>{h['fecha']}</td><td>{h['tipo']} {h['moneda']}</td><td>{h['precio']}</td><td>{h['monto']:.2f}</td><td>{h['ganancia']:.2f}%</td></tr>"
    total = s.get('virtual_balance',0)
    holds = ''
    for m in MONEDAS:
        hd = s.get('holdings',{}).get(m)
        if hd:
            holds += f"<p>{m} {hd['amount']:.6f} entry {hd['entry']:.2f}</p>"
    html = f"<html><body style='background:#111;color:#fff;font-family:sans-serif;padding:20px'><h1>V862 PAPER + 10PM</h1><h2>Balance {s.get('virtual_balance',0):.2f} Total {total:.2f}</h2>{holds}<table border=1><tr><th>Fecha</th><th>Op</th><th>Precio</th><th>Monto</th><th>PnL</th></tr>{rows}</table></body></html>"
    return html

@app.post('/webhook')
async def webhook(req: Request):
    data = await req.json()
    if 'callback_query' in data
