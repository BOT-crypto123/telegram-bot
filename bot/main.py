import os, json, time, threading, requests
from flask import Flask, request
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "trades.json"
app = Flask(__name__)

def load_trades():
    try:
        with open(CHAT_FILE,"r") as f:
            return json.load(f)
    except:
        return {"trades":[],"balance":0,"chat_id":None}

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
    return f"RESUMEN {hoy} - 10PM\nBalance: ${bal:.2f}\nTrades: {len(trades)} Gan: {gan} Per: {per}"

def send_msg(chat_id,text):
    if not TOKEN or not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":chat_id,"text":text,"parse_mode":"Markdown"})
    except:
        pass

HTML = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
HTML += '<title>JOHAN TRADER V502 - BTC 15min</title><script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>'
HTML += '<style>*{margin:0;padding:0;box-sizing:border-box;font-family:Arial}body{background:#050508;color:#fff}'
HTML += '.header{display:flex;justify-content:space-between;padding
