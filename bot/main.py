import os, requests, threading, time, re
from flask import Flask, request

TOKEN = os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app = Flask(__name__)

SEL = "BTC"
SL = 2.0
TP = 2.2
ENTS = {}
HIGHS = {}
LAST = {}

def price(s):
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot", timeout=8).json()
        return float(r["data"]["amount"])
    except:
        return 0

def send_text(cid, txt):
    try:
        u = "https://api.telegram.org/bot"+TOKEN+"/sendMessage"
        kb = {"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
        requests.post(u, json={"chat_id":cid,"text":txt,"reply_markup":kb}, timeout=10)
    except:
        pass

def send_graf(cid, sym, p):
    try:
        from PIL import Image, ImageDraw
        import random, io
        W, H = 800, 400
        img = Image.new("RGB", (W, H), "#111111")
        dr = ImageDraw.Draw(img)
        entry = ENTS[sym]["entry"] if sym in ENTS else p
        # simula 20 velas
        prices = []
        base = p
        for i in range(20):
            base = base * (1 + random.uniform(-0.01, 0.01))
            prices.append(base)
        mn = min(prices + [entry]) * 0.99
        mx = max(prices + [entry]) * 1.01
        def yf(v):
            return H-40 - (v-mn)/(mx-mn)*(H-80)
        for i, pr in enumerate(prices):
            x = i * 40 + 20
            dr.line([x, yf(pr*0.99), x, yf(pr*1.01)], fill="#00ff88" if i%2==0 else "#ff4444", width=2)
        if sym in ENTS:
            ye = yf(entry)
            dr.line([0, ye, W, ye], fill="#ffcc00", width=2)
            dr.text((10, ye-15), f"ENT {round(entry,4)}", fill="#ffcc00")
            dr.line([0, yf(entry*1.022), W, yf(entry*1.022)], fill="#00ff88", width=1)
            dr.line([0, yf(entry*0.98), W, yf(entry*0.98)], fill="#ff4444", width=1)
        dr.text((10, 10), f"{sym} {round(p,4)}", fill="white")
        bio = io.BytesIO()
        bio.name = "graf.png"
        img.save(bio, "PNG")
        bio.seek(0)
        u = "https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
        requests.post(u, data={"chat_id":cid}, files={"photo":bio}, timeout=20)
