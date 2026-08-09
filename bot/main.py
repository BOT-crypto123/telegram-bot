import os, json, time, threading, requests
from flask import Flask, request, render_template_string
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "trades.json"
app = Flask(__name__)

def load_trades():
    try:
        with open(CHAT_FILE,"r") as f:
            return json.load(f)
    except: return {"trades":[],"balance":0,"chat_id":None}

def save_trades(d):
    with open(CHAT_FILE,"w") as f:
        json.dump(d,f)

def resumen_texto():
    d=load_trades()
    bal=d.get("balance",0)
    trades=d.get("trades",[])
    gan=sum(1 for t in trades if t.get("pnl",0)>0)
    per=len(trades)-gan
    hoy=datetime.now(pytz.timezone("America/Mexico_City")).strftime("%d/%m/%Y")
    return f"📊 *RESUMEN {hoy} - 10:00 PM*\n💰 Balance: ${bal:.2f}\n📦 Trades: {len(trades)}\n✅ Ganados: {gan} ❌ Perdidos: {per}"

def m(chat_id,text):
    if not TOKEN or not chat_id: return
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown"})
    except: pass

DASH_15M = """<!DOCTYPE html><html lang=es><head><meta charset=UTF-8><meta name=viewport content="width=device-width, initial-scale=1.0">
<title>JOHAN TRADER - BTC 15min REAL</title>
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Inter,Arial}body{background:#050508;color:#fff}
.header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:#0e0e14;border-bottom:1px solid #1f1f2a}
.live{background:#ff2b2b;padding:5px 12px;border-radius:8px;font-weight:900}
.prices{display:flex;justify-content:space-between;padding:16px;background:#0a0a0f}
.prices label{color:#777;font-size:12px;text-transform:uppercase} .prices .v{font-size:30px;font-weight:900;margin-top:4px}
#chartWrap{height:42vh;margin:10px 12px;background:#0e0e14;border-radius:16px;border:1px solid #222;position:relative}
#chart{width:100%;height:100%}
.stats{display:flex;gap:8px;padding:0 12px;margin-top:10px}
.stat{flex:1;background:#12121a;border-radius:12px;padding:10px
