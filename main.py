# SOLO CAMBIA ESTAS 2 FUNCIONES EN TU CODIGO:

@app.route('/')
def dash():
    ny=is_ny(); fb=0; fn=0; ffees=0; cards=""; tb=sum(t["bola"] for t in ESTADO["open_trades"])
    for tr in ESTADO["open_trades"]:
        pa=get_price(tr["simbolo"])
        br=(pa-tr["entrada_real"])/tr["entrada_real"]*100
        gb=tr["bola"]*br/100
        fee=tr["bola"]*FEE_RT
        ne=br-FEE_RT*100
        gn=tr["bola"]*ne/100
        fb+=gb; fn+=gn; ffees+=fee
        cards+=f'''<div style="background:#001a0a;border:1px solid #00ff88;padding:10px;margin:8px 0;border-radius:10px">
        <b>{tr["simbolo"]}</b> ${tr["bola"]} - Entrada {tr["entrada_real"]:.2f} -> Ahora {pa:.2f}<br>
        BRUTA: {br:+.2f}% = ${gb:+.2f}<br>
        FEE RT (0.82%): -${fee:.2f}<br>
        <b>NETA REAL: {ne:+.2f}% = ${gn:+.2f}</b><br>
        MAX NETA: {tr.get("max_neto",ne):+.2f}% | TRAIL: 1.2%
        </div>'''
    pat=ESTADO["demo_balance"]+tb+fn
    h=f'''<html><head><meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="20"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.titulo{{background:#111;border:3px solid #FFD700;border-radius:16px;padding:18px;text-align:center}}.card{{background:#111;border:1px solid #222;border-radius:14px;padding:14px;margin:10px 0}}.flot{{background:#002200;border:2px solid #00ff88;border-radius:14px;padding:14px;margin:10px 0}}</style></head><body>
    <div class="titulo"><h1>💰 V55.2 FLOT + DESGLOSE REAL 💰</h1></div>
    <div class="flot">
    <b>💳 EFECTIVO:</b> ${ESTADO["demo_balance"]:.2f}<br>
    <b>📦 EN BOLAS:</b> ${tb:.2f}<br>
    <b>📈 FLOT BRUTO (sin fees):</b> ${fb:+.2f}<br>
    <b>💸 FEES POR PAGAR SI VENDES:</b> -${ffees:.2f}<br>
    <b>💰 FLOT NETO REAL (ya con fees):</b> ${fn:+.2f}<br>
    <hr>
    <b>🏦 PATRIMONIO TOTAL REAL:</b> ${pat:.2f}<br>
    <b>📊 UTILIDAD REAL TOTAL:</b> ${pat-10000:+.2f} ({(pat-10000)/100:.2f}%)<br>
    <b>💸 FEES ACUMULADOS HISTORICOS:</b> ${ESTADO["fees"]:.2f}<br>
    HOY {ESTADO["trades_hoy_count"]} trades | {"🟢 NY" if ny else "🌙 NOCHE"}
    </div><div>{cards}</div>'''
    for s in SYMBOLS:
        d=decidir(s); h+=f'<div class="card"><b>{s}</b> ${get_price(s):.2f} - {d["tipo"]}<br><small>{d["det"].replace(chr(10),"<br>")}</small><br><br><a href="/graf/{s}" style="background:#00ff88;color:#000;padding:8px 14px;border-radius:8px;text-decoration:none">GRAFICA</a></div>'
    return h+"</body></html>"

# Y EN TELEGRAM:

@bot.message_handler(func=lambda m: True)
def all_msg(m):
    t=m.text.strip().upper()
    if "DASHBOARD" in t or t=="DASH":
        url=os.getenv("RENDER_EXTERNAL_URL") or ""
        if url and not url.startswith("http"): url="https://"+url
        if not url: url="Tu link de Render.onrender.com"
        bot.send_message(m.chat.id, f"🌐 DASHBOARD V55.2:\n{url}"); return
    if "BALANCE" in t or "FLOT" in t or "DESGLOSE" in t:
        tb=0; fb=0; fn=0; ffees=0; detalle=""
        for tr in ESTADO["open_trades"]:
            pa=get_price(tr["simbolo"])
            br=(pa-tr["entrada_real"])/tr["entrada_real"]*100
            gb=tr["bola"]*br/100
            fee=tr["bola"]*FEE_RT
            ne=br-FEE_RT*100
            gn=tr["bola"]*ne/100
            tb+=tr["bola"]; fb+=gb; fn+=gn; ffees+=fee
            detalle+=f"\n{tr['simbolo']} ${tr['bola']}:\n  Bruta {br:+.2f}% = ${gb:+.2f}\n  Fee -${fee:.2f}\n  NETA {ne:+.2f}% = ${gn:+.2f}\n"
        pat=ESTADO["demo_balance"]+tb+fn
        msg=f'''💰 V55.2 DESGLOSE REAL COMPLETO
💳 EFECTIVO: ${ESTADO["demo_balance"]:.2f}
📦 EN BOLAS: ${tb:.2f}

📈 FLOT BRUTO: ${fb:+.2f}
💸 FEES SI VENDES AHORA: -${ffees:.2f}
💰 FLOT NETO REAL: ${fn:+.2f}
{detalle}
---
🏦 PAT TOTAL REAL: ${pat:.2f}
📊 UTILIDAD REAL: ${pat-10000:+.2f} ({(pat-10000)/100:+.2f}%)
💸 FEES HISTORICOS PAGADOS: ${ESTADO["fees"]:.2f}

Cada trade ya trae 0.82% de fee real descontado we.
'''
        bot.send_message(m.chat.id, msg); return
    if t in SYMBOLS: d=decidir(t); bot.send_message(m.chat.id,f"💰 {t} ${get_price(t):.2f}\n{d['det']}\n{d['tipo']}")
    else: bot.send_message(m.chat.id,"Comandos:\n/balance = desglose real\n/flot = flotante\nDASHBOARD = link")
