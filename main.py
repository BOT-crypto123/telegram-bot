@app.route("/")
def home():
    tot, flot = totals()
    btc1h = get_btc_1h()
    pos_normal = [p for p in data['pos'] if not p.get('es_dual')]
    pos_e1 = [p for p in data['pos'] if p.get('es_dual')==1]
    pos_e2 = [p for p in data['pos'] if p.get('es_dual')==2]
    
    html = f"""
    <html><head><meta name='viewport' content='width=device-width'><meta http-equiv='refresh' content='15'>
    <style>
    body{{background:#0a0a0a;color:#fff;font-family:Arial;padding:10px}}
    .top{{border:2px solid #ffcc00;border-radius:15px;padding:12px;background:#1a1500;margin-bottom:10px}}
    .card{{background:#1a1a1a;border-radius:15px;padding:12px;margin:8px 0;border-left:4px solid #555}}
    .card.vivo{{border-left-color:#00ff88;background:#0f1f15}}
    .card.e1{{border-left-color:#a855f7;background:#1a102a}}
    .card.e2{{border-left-color:#ff3b3b;background:#2a1010}}
    .desglose{{background:#222;border:1px solid #ffcc00;border-radius:12px;padding:12px;margin:10px 0}}
    .graf{{background:#ffcc00;color:#000;width:100%;padding:10px;border-radius:10px;margin-top:8px;display:block;text-align:center;text-decoration:none;font-weight:bold}}
    .live{{background:#00ff88;color:#000;padding:2px 6px;border-radius:6px;font-size:10px}}
    </style></head><body>
    <div class='top'><b>🔥 V32.3 PRESAS VIVAS 🔥</b><br>🟢 CAZANDO {len(data['pos'])}/10 | Total ${tot:.2f} | Flot {flot:+.2f}$ | BTC 1h {btc1h:+.2f}%<br>Saldo ${data['b']:.2f} | Hoy ${data['gan_hoy']:.2f}</div>
    <div class='desglose'><b>💰 DESGLOSE $5000 MXN:</b><br>
    Motor PRO: ${sum([p['monto'] for p in pos_normal]):.2f} ({len(pos_normal)})<br>
    E1 AUTO $1750: ${sum([p['monto'] for p in pos_e1]):.2f} ({len(pos_e1)})<br>
    E2 $1750: ${sum([p['monto'] for p in pos_e2]):.2f} ({len(pos_e2)})<br>
    Saldo Libre: ${data['b']:.2f}</div>
    """

    # 1. PRIMERO LAS 3 QUE ESTAN EN ENTRADA
    if data['pos']:
        html += "<h3>🎯 EN ENTRADA AHORA:</h3>"
        for p in data['pos']:
            try:
                price = P(p['sym'])
                if price==0: price=p['precio_entry']
                gan_pct = (price-p['precio_entry'])/p['precio_entry']*100
                gan_usd = p.get('gan',0)
                tipo = "E1 AUTO" if p.get('es_dual')==1 else "E2 LIQ" if p.get('es_dual')==2 else "PRO RSI"
                color = "e1" if p.get('es_dual')==1 else "e2" if p.get('es_dual')==2 else "vivo"
                html += f"<div class='card {color}'><b>🎯 {p['sym']} - {tipo} <span class='live'>VIVO ENTRADA</span></b><br>Entrada ${p['precio_entry']:.4f} → Ahora ${price:.4f}<br>Gan {gan_pct:+.2f}% = ${gan_usd:+.2f} | Monto ${p['monto']}<br><a class='graf' href='/chart/{p['sym']}'>📈 VER GRAFICA VIVA</a></div>"
            except:
                html += f"<div class='card vivo'><b>{p['sym']} ENTRADA</b></div>"
    else:
        html += "<div class='card'>Sin presas, cazando...</div>"

    # 2. LUEGO EL RESTO CAZANDO
    html += "<h3>👀 CAZANDO (sin entrada):</h3>"
    for sym in ALL_COINS:
        if any(p['sym']==sym for p in data['pos']): continue
        try:
            rsi,price,ema,_=AN(sym)
            html+=f"<div class='card'><b>{sym} ${price:.4f}</b> RSI {rsi:.1f} EMA ${ema:.2f}<br><a class='graf' href='/chart/{sym}'>VER GRAFICA</a></div>"
        except:
            html+=f"<div class='card'><b>{sym} consultando...</b></div>"
    
    html+="</body></html>"
    return html
