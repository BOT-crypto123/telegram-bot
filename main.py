import os, json, time, threading, requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
DATA_FILE = "bot_data.json"
FEE = 0.001

default_data = {
 "capital_actual": 500.0, "capital_inicial": 500.0, "usd_mxn": 16.96,
 "gan_acum_total": 0.0, "gan_acum_mxn": 0.0, "gan_mes": 0.0, "pct_mes": 0.0,
 "ganadas": 0, "salidas": 0, "tp": 0.5, "sl_pct": -1.5, "rsi_compra": 35, "rsi_venta": 70,
 "filtro_ema": "OFF", "max_entradas": 3, "auto": True, "pos": [], "historial": [], "capital_history": [],
 "coins_activas": {"BTC":True,"ETH":True,"SOL":True,"BNB":True,"XRP":True,"ADA":True,"AVAX":True,"DOGE":True},
 "rsi_por_moneda": {}, "alert_users": []
}
try:
    with open(DATA_FILE) as f: data=json.load(f)
    for k,v in default_data.items():
        if k not in data: data[k]=v
except: data=default_data.copy()

def save():
    with open(DATA_FILE,"w") as f: json.dump(data,f)

def tg(chat_id, text):
    if not BOT_TOKEN: return
    try:
        base = os.getenv("RENDER_EXTERNAL_URL","https://telegram-bot-cijp.onrender.com")
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id, "text": text,
            "reply_markup": {"inline_keyboard": [[{"text":"📊 VER DASHBOARD","url":f"{base}/dashboard"}]]}
        }, timeout=10)
    except: pass

SYMS = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","ADA/USDT","AVAX/USDT","DOGE/USDT"]

def get_rsi(prices, p=14):
    if len(prices)<p+1: return 50
    gains=0; losses=0
    for i in range(1,p+1):
        d=prices[-i]-prices[-i-1]
        if d>=0: gains+=d
        else: losses+=-d
    if losses==0: return 100
    rs=gains/losses
    return 100 - (100/(1+rs))

def get_prices_data():
    out={}
    for sym in SYMS:
        coin = sym.replace("/USDT","")
        bin_sym = sym.replace("/","")
        try:
            url = f"https://data-api.binance.vision/api/v3/klines?symbol={bin_sym}&interval=1h&limit=100"
            r = requests.get(url, timeout=10)
            klines = r.json()
            if isinstance(klines, dict) and "msg" in klines: raise Exception(klines["msg"])
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            rsi = get_rsi(closes)
            ema = sum(closes[-20:])/20
            p_ema_ok = price > ema if data["filtro_ema"]=="ON" else True
            limite = data["rsi_por_moneda"].get(coin, data["rsi_compra"])
            ok = rsi <= limite and p_ema_ok
            if not p_ema_ok: sug="Espera EMA"; motivo=f"P {price:.2f} < EMA {ema:.2f}"
            elif ok: sug="COMPRA"; motivo=f"RSI {rsi:.1f} <= {limite}"
            else: sug="Espera RSI"; motivo=f"RSI {rsi:.1f} > {limite}"
            out[coin] = {"price":price,"rsi":round(rsi,1),"limite":limite,"p_ema_ok":p_ema_ok,"ok":ok,"sug":sug,"motivo":motivo}
        except Exception as e:
            try:
                url2 = f"https://www.okx.com/api/v5/market/candles?instId={coin}-USDT&bar=1H&limit=100"
                r2 = requests.get(url2, timeout=10).json()
                closes2 = [float(x[4]) for x in reversed(r2["data"])]
                price = closes2[-1]; rsi=get_rsi(closes2); ema=sum(closes2[-20:])/20
                p_ema_ok = price > ema if data["filtro_ema"]=="ON" else True
                limite = data["rsi_por_moneda"].get(coin, data["rsi_compra"])
                ok = rsi <= limite and p_ema_ok
                out[coin] = {"price":price,"rsi":round(rsi,1),"limite":limite,"p_ema_ok":p_ema_ok,"ok":ok,"sug":"COMPRA" if ok else "ESPERA","motivo":f"OKX RSI {rsi:.1f}"}
            except Exception as e2:
                print(f"{coin} error {e} / {e2}")
                out[coin] = {"price":0,"rsi":50,"limite":35,"p_ema_ok":False,"ok":False,"sug":"Error","motivo":str(e)[:90]}
    return out

@app.route("/", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def webhook():
    if request.method=="GET": return "BOT LIVE - /dashboard OK",200
    d=request.get_json(force=True,silent=True) or {}
    if "message" in d and "chat" in d["message"]:
        chat=d["message"]["chat"]["id"]
        if chat not in data["alert_users"]:
            data["alert_users"].append(chat); save()
        base=os.getenv("RENDER_EXTERNAL_URL","https://telegram-bot-cijp.onrender.com")
        tg(chat, f"500 USD = ${data['usd_mxn']*500:.0f} MXN\nAcum: ${data['gan_acum_total']:.2f} USD / ${data['gan_acum_mxn']:.0f} MXN\n{base}/dashboard")
    return jsonify(ok=True)

@app.route("/dashboard")
def dashboard():
    if os.path.exists("dashboard.html"): return send_from_directory(".","dashboard.html")
    return "No existe dashboard.html - súbelo a GitHub",404

@app.route("/chart/<sym>")
def chart_page(sym): return f"<h1>{sym} - Proximamente</h1><a href='/dashboard'>Volver</a>"

@app.route("/api/prices")
def api_prices(): return jsonify(get_prices_data())

@app.route("/api/state")
def api_state():
    bola = data["capital_actual"]/data["max_entradas"]
    winrate = (data["ganadas"]/data["salidas"]*100) if data["salidas"]>0 else 0
    prices = get_prices_data()
    for p in data["pos"]:
        pr = prices.get(p["sym"],{}).get("price",p["entry"])
        p["ahora"]=pr; gan_b=(pr-p["entry"])/p["entry"]*100; gan_n=gan_b - (FEE*2*100)
        p["gan_neta_pct"]=gan_n; p["gan_neta_mxn"]=p["monto"]*gan_n/100*data["usd_mxn"]; p["debe_vender"]=gan_n >= (data["tp"]-FEE*2*100) or gan_n <= data["sl_pct"]
    return jsonify({"meta_mxn": data["usd_mxn"]*500, "gan_acum": data["gan_acum_total"], "gan_acum_mxn": data["gan_acum_mxn"], "usd_mxn": data["usd_mxn"], "pct_mes": data["pct_mes"], "gan_mes": data["gan_mes"], "ganadas": data["ganadas"], "salidas": data["salidas"], "winrate": winrate, "tp": data["tp"], "fee_total": FEE*2*100, "max_entradas": data["max_entradas"], "rsi_compra": data["rsi_compra"], "sl_pct": data["sl_pct"], "rsi_venta": data["rsi_venta"], "filtro_ema": data["filtro_ema"], "auto": data["auto"], "coins_activas": data["coins_activas"], "bola": bola, "bola_mxn": bola*data["usd_mxn"], "capital": data["capital_actual"], "pos": data["pos"], "historial": data["historial"][-50:], "capital_history": data["capital_history"][-100:]})

@app.route("/api/config", methods=["POST"])
def api_config():
    j=request.json
    if "toggle_coin" in j: data["coins_activas"][j["toggle_coin"]]=not data["coins_activas"].get(j["toggle_coin"],True)
    if "rsi_compra" in j: data["rsi_compra"]=float(j["rsi_compra"])
    if "rsi_coin" in j: data["rsi_por_moneda"][j["rsi_coin"]["sym"]]=float(j["rsi_coin"]["val"])
    if "rsi_coin_reset" in j: data["rsi_por_moneda"].pop(j["rsi_coin_reset"],None)
    if "tp" in j: data["tp"]=float(j["tp"])
    if "sl_pct" in j: data["sl_pct"]=float(j["sl_pct"])
    if "rsi_venta" in j: data["rsi_venta"]=float(j["rsi_venta"])
    if "filtro_ema" in j: data["filtro_ema"]=j["filtro_ema"]
    if "max" in j: data["max_entradas"]=int(j["max"])
    save(); return jsonify(ok=True)

@app.route("/api/buy/<sym>", methods=["POST"])
def buy_sym(sym):
    if len(data["pos"])>=data["max_entradas"]: return jsonify(ok=False)
    prices=get_prices_data()
    if sym not in prices or prices[sym]["price"]==0: return jsonify(ok=False)
    monto=data["capital_actual"]/data["max_entradas"]
    data["pos"].append({"sym":sym,"entry":prices[sym]["price"],"monto":monto,"ahora":prices[sym]["price"],"gan_neta_pct":0,"gan_neta_mxn":0,"debe_vender":False})
    save(); return jsonify(ok=True)

@app.route("/api/sell/<sym>", methods=["POST"])
def sell_sym(sym):
    prices=get_prices_data()
    for p in data["pos"]:
        if p["sym"]==sym:
            pr=prices.get(sym,{}).get("price",p["entry"]); gan_b=(pr-p["entry"])/p["entry"]*100; gan_n=gan_b - FEE*2*100; gan_mxn=p["monto"]*gan_n/100*data["usd_mxn"]
            data["capital_actual"]+=p["monto"]*gan_n/100; data["gan_acum_total"]+=p["monto"]*gan_n/100; data["gan_acum_mxn"]+=gan_mxn; data["salidas"]+=1
            if gan_n>0: data["ganadas"]+=1
            data["historial"].append({"fecha":time.strftime("%m-%d %H:%M"),"sym":sym,"monto":p["monto"],"entry":p["entry"],"exit":pr,"gan_neta_pct":gan_n,"gan_neta_mxn":gan_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
            data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]})
            for uid in data["alert_users"]: tg(uid, f"{'🟢 GANANCIA' if gan_mxn>0 else '🔴 PERDIDA'} {sym} {gan_n:.2f}% = ${gan_mxn:.2f} MXN\nCapital: ${data['capital_actual']:.2f}")
            data["pos"].remove(p); save(); break
    return jsonify(ok=True)

@app.route("/api/toggle", methods=["POST"])
def toggle(): data["auto"]=not data["auto"]; save(); return jsonify(ok=True)

def auto_loop():
    while True:
        try:
            if data["auto"]:
                prices=get_prices_data()
                for p in list(data["pos"]):
                    pr=prices.get(p["sym"],{}).get("price",p["entry"]); gan_b=(pr-p["entry"])/p["entry"]*100; gan_n=gan_b - FEE*2*100; rsi_v = prices.get(p["sym"],{}).get("rsi",100)
                    debe = gan_n >= (data["tp"]-FEE*2*100) or gan_n <= data["sl_pct"] or rsi_v >= data["rsi_venta"]
                    if debe:
                        gan_mxn=p["monto"]*gan_n/100*data["usd_mxn"]; data["capital_actual"]+=p["monto"]*gan_n/100; data["gan_acum_total"]+=p["monto"]*gan_n/100; data["gan_acum_mxn"]+=gan_mxn; data["salidas"]+=1
                        if gan_n>0: data["ganadas"]+=1
                        data["historial"].append({"fecha":time.strftime("%m-%d %H:%M"),"sym":p["sym"],"monto":p["monto"],"entry":p["entry"],"exit":pr,"gan_neta_pct":gan_n,"gan_neta_mxn":gan_mxn,"capital_despues":data["capital_actual"],"bola_despues":data["capital_actual"]/data["max_entradas"]})
                        data["capital_history"].append({"t":int(time.time()*1000),"cap":data["capital_actual"]})
                        for uid in data["alert_users"]: tg(uid, f"{'🟢 GANANCIA' if gan_mxn>0 else '🔴 PERDIDA'} {p['sym']} {gan_n:.2f}% = ${gan_mxn:.2f} MXN\nCapital: ${data['capital_actual']:.2f}")
                        data["pos"].remove(p); save()
                if len(data["pos"])<data["max_entradas"]:
                    for sym,info in prices.items():
                        if info["price"]>0 and info["ok"] and data["coins_activas"].get(sym,True) and not any(x["sym"]==sym for x in data["pos"]):
                            if len(data["pos"])>=data["max_entradas"]: break
                            monto=data["capital_actual"]/data["max_entradas"]; data["pos"].append({"sym":sym,"entry":info["price"],"monto":monto,"ahora":info["price"],"gan_neta_pct":0,"gan_neta_mxn":0,"debe_vender":False}); save()
                            for uid in data["alert_users"]: tg(uid, f"🔵 COMPRA {sym} ${info['price']:.2f} RSI {info['rsi']}")
                            break
        except Exception as e: print("AUTO ERROR",e)
        time.sleep(60)

threading.Thread(target=auto_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
