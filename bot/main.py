import os, requests, threading, time, re, io, json
from flask import Flask, request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="XRP"; SL=2.0; TP2=2.2; DROP_AUTO=1.0
ENTS={}; FILE="/tmp/bot81.json"
CONFIG={"AUTO":False,"LAST_CID":0}
def load():
    global ENTS, CONFIG
    try:
        if os.path.exists(FILE):
            import json
            with open(FILE,"r") as f:
                d=json.load(f);
                global ENTS
                ENTS=d.get("ENTS",{}); CONFIG=d.get("CONFIG",CONFIG)
    except: pass
def save():
    try:
        with open(FILE,"w") as f: json.dump({"ENTS":ENTS,"CONFIG":CONFIG},f)
    except: pass
load()
def price(s):
    try:
        r=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
        return float(r["data"]["amount"])
    except: return 0
def get_candles(sym,gran=60,n=20):
    try:
        url=f"https://api.exchange.coinbase.com/products/{sym}-USD/candles?granularity={gran}"
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
        return sorted(r)[-n:]
    except: return []
def send_text(cid,txt):
    try:
        u=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR 100","VENDER"],["GRAF","PRO"],["AUTO ON","AUTO OFF"]],"resize_keyboard":True}
        requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=15)
    except: pass
def checker():
    last_alert={}
    while True:
        try:
            time.sleep(60)
            for sym in list(ENTS.keys()):
                p=price(sym)
                if p<1: continue
                v=ENTS[sym]; pnl=(p/v["entry"]-1)*100
                if CONFIG.get("AUTO"):
                    if pnl<=-SL:
                        send_text(v["chat"],f"🔴 AUTO VENDER {sym} {round(p,4)} {round(pnl,2)}%")
                        del ENTS[sym]; save()
                    elif pnl>=TP2:
                        neto=pnl-0.2
                        send_text(v["chat"],f"🟢 AUTO VENDER {sym} {round(p,4)} NETO {round(neto,2)}% Gane ${round(v['usd']*neto/100,2)}")
                        del ENTS[sym]; save()
                else:
                    # MODO ALERTA SOLO
                    if pnl<=-1.5 and last_alert.get(sym)!=f"down{p}":
                        send_text(v["chat"],f"⚠️ ALERTA BAJADA {sym} {round(p,4)} {round(pnl,2)}% ¿Vendo con VENDER?")
                        last_alert[sym]=f"down{p}"
                    if pnl>=1.5 and last_alert.get(sym)!=f"up{p}":
                        send_text(v["chat"],f"⚠️ ALERTA SUBIDA {sym} {round(p,4)} +{round(pnl,2)}% NETO {round(pnl-0.2,2)}% ¿Vendo con VENDER?")
                        last_alert[sym]=f"up{p}"
            cid=CONFIG.get("LAST_CID")
            if not cid: continue
            if CONFIG.get("AUTO"):
                for sym in ["BTC","ETH","SOL","XRP"]:
                    if sym in ENTS: continue
                    candles=get_candles(sym,60,20)
                    if len(candles)<15: continue
                    p_now=candles[-1][4]; p_old=candles[-10][4]
                    drop=(p_now/p_old-1)*100
                    if drop<=-DROP_AUTO:
                        ENTS[sym]={"entry":p_now,"chat":cid,"usd":100}; save()
                        send_text(cid,f"🤖 AUTO COMPRAR {sym} {round(p_now,4)} caida {round(drop,2)}%")
            else:
                # ALERTAS DE OPORTUNIDAD EN OFF
                for sym in ["BTC","ETH","SOL","XRP"]:
                    if sym in ENTS: continue
                    candles=get_candles(sym,60,20)
                    if len(candles)<15: continue
                    p_now=candles[-1][4]; p_old=candles[-10][4]
                    drop=(p_now/p_old-1)*100
                    key=f"opp{sym}"
                    if drop<=-DROP_AUTO and last_alert.get(key)!=round(p_now,2):
                        send_text(cid,f"⚠️ OPORTUNIDAD BAJADA {sym} {round(p_now,4)} {round(drop,2)}% ¿Compro con COMPRAR 100?")
                        last_alert[key]=round(p_now,2)
        except: time.sleep(10)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home(): return "V81 ALERTA OK",200
@app.route("/webhook",methods=["POST"])
def wh():
    global SEL
    d=request.get_json(force=True,silent=True)
    if not d or "message" not in d: return "ok",200
    cid=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
    CONFIG["LAST_CID"]=cid; save()
    if "AUTO ON" in t: CONFIG["AUTO"]=True; save(); send_text(cid,"🤖 V81 AUTO ON - Compro y vendo solo"); return "ok",200
    if "AUTO OFF" in t: CONFIG["AUTO"]=False; save(); send_text(cid,"🔕 V81 AUTO OFF - Solo te alertaré subidas y bajadas, no compro solo"); return "ok",200
    for s in ["BTC","ETH","SOL","XRP"]:
        if s in t: SEL=s
    if t in ["BTC","ETH","SOL","XRP"]: SEL=t
    p=price(SEL) or (ENTS[SEL]["entry"] if SEL in ENTS else 0)
    if "GRAF" in t:
        # graf rapido
        from PIL import Image, ImageDraw
        candles=get_candles(SEL,60,50); W=900;H=520
        img=Image.new("RGB",(W,H),"#0b0e14"); dr=ImageDraw.Draw(img)
        mn=mx=p
        if candles:
            lows=[c[1] for c in candles];highs=[c[2] for c in candles]
            mn=min(min(lows),p)*0.9995;mx=max(max(highs),p)*1.0005
        def yf(v): return H-70-(v-mn)/(mx-mn)*(H-110) if mx!=mn else H//2
        def xf(i): return 20+i*(W-40)//50
        if candles:
            for i,c in enumerate(candles):
                x=xf(i); col="#00ff88" if c[4]>=c[3] else "#ff4444"
                dr.line([x+3,yf(c[1]),x+3,yf(c[2])],fill=col,width=1)
                dr.rectangle([x,yf(max(c[3],c[4])),x+6,yf(min(c[3],c[4]))],fill=col)
        dr.text((10,10),f"V81 {SEL} {round(p,4)} {'AUTO ON' if CONFIG['AUTO'] else 'SOLO ALERTAS'}",fill="white")
        bio=io.BytesIO(); bio.name="graf.png"; img.save(bio,"PNG"); bio.seek(0)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",data={"chat_id":cid},files={"photo":bio},timeout=
