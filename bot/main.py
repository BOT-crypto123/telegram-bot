import os, json, time, threading, requests
from flask import Flask, request
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_FILE = "trades.json"
app = Flask(__name__)

def load_trades():
    try:
        with open(CHAT_FILE, "r") as f:
            return json.load(f)
    except:
        return {"trades": [], "balance": 0, "chat_id": None}

def save_trades(d):
    with open(CHAT_FILE, "w") as f:
        json.dump(d, f)

def resumen():
    d = load_trades()
    bal = d.get("balance", 0)
    total = len(d.get("trades", []))
    return f"Balance: ${bal:.2f} Trades: {total}"

def send_msg(chat_id, text):
    if not TOKEN:
        return
    if not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except:
        pass

HTML_PAGE = """
<!DOCTYPE html><html><head><meta charset=UTF-8><meta name=viewport content="width=device-width,initial-scale=1"><title>JOHAN V504</title><script src=https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js></script><style>body{background:#050508;color:#fff;margin:0;font-family:Arial}.top{padding:12px;background:#0e0e14;display:flex;justify-content:space-between}.box{display:flex;justify-content:space-between;padding:16px;background:#0a0a0f}#chartWrap{height:45vh;margin:10px;background:#0e0e14;border-radius:16px;border:1px solid #222}#chart{width:100%;height:100%}.btns{display:flex;gap:10px;padding:14px}.b{flex:1;padding:18px;border-radius:14px;border:none;font-weight:900;font-size:18px}.up{background:#7ef7cc;color:#000}.down{background:#ff4d5a;color:#fff}</style></head><body><div class=top><b>BTC 15min LIVE V504</b><span id=clock></span></div><div class=box><div><small>Price to beat</small><div id=beat style=font-size:26px;font-weight:900>$0.00</div></div><div style=text-align:right><small>Current</small><div id=cur style=font-size:26px;font-weight:900>$0.00</div></div></div><div id=chartWrap><div id=chart></div></div><div class=btns><button class="b up" id=upBtn>Up</button><button class="b down" id=downBtn>Down</button></div><script>
var chart=LightweightCharts.createChart(document.getElementById("chart"),{layout:{background:{color:"#0e0e14"},textColor:"#555"},grid:{vertLines:{color:"#15151e"},horzLines:{color:"#15151e"}},width:document.getElementById("chartWrap").clientWidth,height:document.getElementById("chartWrap").clientHeight});
var line=chart.addLineSeries({color:"#ffb020",lineWidth:2});
var priceBeat=0;var lastPrice=0;
async function init(){var r=await fetch("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60");var j=await r.json();j=j.reverse();priceBeat=j[Math.floor(j.length/2)][4];document.getElementById("beat").innerText="$"+priceBeat.toFixed(2);var data=[];for(var i=0;i<j.length;i++){data.push({time:j[i][0],value:j[i][4]})}
