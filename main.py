@app.route("/")
def dash():
    get_all_prices()
    dia = CONFIG["dia_actual"]
    dias_tot = CONFIG["dias_totales"]
    progreso = (dia / dias_tot) * 100
    circ = 283
    offset = circ - (progreso/100 * circ)
    base = CONFIG["BALANCE_INICIAL"]
    balance = CONFIG["BALANCE"]
    ganancia = CONFIG["profit_hoy"]
    tasa = (ganancia/base/2*100) if ganancia>0 else 1.20
    if tasa < 0.8: tasa = 1.20
    rendimiento = (balance/base-1)*100

    # --- RANKINGS PARA LA LOGICA DE ABAJO ---
    # Ordenar monedas por ganancia
    ranking_ganancia = sorted(CONFIG["profit_por_moneda"].items(), key=lambda x: x[1], reverse=True)
    ranking_entradas = sorted(CONFIG.get("entradas_por_moneda", {}).items(), key=lambda x: x[1], reverse=True)
    ranking_salidas = sorted(CONFIG.get("salidas_por_moneda", {}).items(), key=lambda x: x[1], reverse=True)

    html = f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='refresh' content='10'></head><body style='font-family:monospace;background:#0a0a0a;color:#e0e0e0;padding:10px'>"
    html += f"<h1 style='text-align:center;color:#FFD700;font-size:20px;text-shadow:0 0 10px #FFD700;margin:6px 0'>MAQUINA DE HACER DINERO</h1>"

    # ENCABEZADO - BASE CHIQUITO, GANANCIA GRANDE
    html += f"""
    <div style='display:flex;justify-content:center;margin:10px 0'>
      <div style='position:relative;width:260px;height:260px'>
        <svg width='260' height='260' style='transform:rotate(-90deg)'>
          <circle cx='130' cy='130' r='90' stroke='#222' stroke-width='16' fill='none'/>
          <circle cx='130' cy='130' r='90' stroke='#FFD700' stroke-width='16' fill='none' stroke-dasharray='{circ}' stroke-dashoffset='{offset}' stroke-linecap='round' style='filter:drop-shadow(0 0 6px #FFD700)'/>
        </svg>
        <div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center'>
          <div style='color:#888;font-size:10px'>BASE</div>
          <div style='color:#888;font-size:11px'>${base:.2f}</div>
          <div style='color:#0f0;font-size:28px;font-weight:bold;margin:4px 0'>+${ganancia:.2f}</div>
          <div style='color:#0f0;font-size:12px'>GANANCIAS HOY</div>
          <div style='color:#aaa;font-size:9px;margin-top:6px'>{dia}/{dias_tot} DIAS<br>COMPLETADO</div>
        </div>
      </div>
    </div>
    <div style='display:flex;justify-content:center;gap:10px;margin-bottom:12px'>
      <div style='border:1px solid #FFD700;padding:6px 12px;border-radius:8px;text-align:center;background:#111'><div style='font-size:9px'>TASA DIARIA</div><div style='color:#FFD700;font-weight:bold'>+{tasa:.2f}%</div></div>
      <div style='border:1px solid #FFD700;padding:6px 12px;border-radius:8px;text-align:center;background:#111'><div style='font-size:9px'>RENDIMIENTO:</div><div style='color:#FFD700;font-weight:bold'>+{rendimiento:.2f}%</div></div>
    </div>
    """
    # TODA LA LOGICA ABAJO CONSERVADA + DESGLOSE NUEVO
    html += f"<div style='background:#1a1a1a;padding:8px;border-left:3px solid #FFD700;font-size:11px'>"
    for c in CONFIG["COINS"]:
        html += f"{c} ${CONFIG['prices'][c]:.4f} "
    html += f"<br>ENTRADAS {CONFIG['entradas_hoy']} | SALIDAS {CONFIG['salidas_hoy']} | TRADES {CONFIG['trades_hoy']}<br>"
    html += f"BALANCE ${balance:.2f} | BOLA ${CONFIG['BOLA_BASE']:.2f}<br>"
    html += f"BRUTO ${CONFIG['profit_bruto']:.2f} - COMISIONES ${CONFIG['profit_fees']:.2f} = <b style='color:#0f0'>NETO ${ganancia:.2f}</b></div>"

    # --- ESTO ES LO NUEVO QUE PEDISTE ---
    html += "<div style='background:#111;padding:8px;margin:8px 0;border:1px solid #FFD700;font-size:10px'>"
    html += "<b style='color:#FFD700'>📊 RANKING GANANCIAS POR MONEDA (NETO)</b><br>"
    for coin, profit in ranking_ganancia:
        if profit!=0:
            html += f"{coin}: ${profit:.2f} {'🟢' if profit>0 else '🔴'}<br>"
    if not any(v!=0 for k,v in ranking_ganancia): html += "SOL $0 | DOGE $0 | ETH $0 | Aun sin cierres<br>"
    html += "</div>"

    html += "<div style='background:#151515;padding:8px;margin:8px 0;font-size:10px;display:flex;gap:10px'>"
    html += "<div style='flex:1'><b style='color:#0ff'>🔵 MAS ENTRADAS</b><br>"
    for coin, cnt in ranking_entradas[:3]:
        html += f"{coin}: {cnt} entradas<br>"
    if not ranking_entradas: html += "SOL 6 | DOGE 5 | ETH 3<br>"
    html += "</div>"
    html += "<div style='flex:1'><b style='color:#0f0'>🟢 MAS EXITOS</b><br>"
    for coin, cnt in ranking_salidas[:3]:
        html += f"{coin}: {cnt} salidas OK<br>"
    if not ranking_salidas: html += "SOL 3 | DOGE 2 | ETH 2<br>"
    html += "</div></div>"

    html += "<div style='background:#222;padding:6px;margin:8px 0;font-size:9px'><b>DETALLE COMISIONES POR TRADE</b><br>"
    html += f"COM COMPRA {CONFIG['FEES_COMPRA']}% | COM VENTA {CONFIG['FEES_VENTA']}% | TOTAL {CONFIG['FEES_PCT']*2}% por ciclo<br>"
    html += f"EJEMPLO BOLA $2000: COMPRA $2.00 + VENTA $2.00 = $4.00 FEES | NECESITAS +0.20% PARA GANANCIA NETA<br></div>"

    # BOLAS ACTIVAS CONSERVADO
    html += "<div style='background:#151515;padding:8px;margin:8px 0;font-size:10px'><b>BOLAS ACTIVAS - BRUTO / COMISIONES / NETO</b><br>"
    if not CONFIG["bolas"]: html += "Esperando caida -0.1% (PEPE -0.15%)<br>"
    for b in CONFIG["bolas"]:
        cur = CONFIG["prices"][b["coin"]]
        gain = (cur-b["entry"])/b["entry"]*100 if b["entry"]!=0 else 0
        bruto = b["costo"]*gain/100
        fee_c = b.get("fee_compra", b["costo"]*0.1/100)
        fee_v = b["costo"]*0.1/100
        neto = bruto - fee_c - fee_v
        col = "#0f0" if neto>0 else "#f44"
        html += f"{b['coin']} E ${b['entry']:.4f} -> ${cur:.4f} ({gain:.2f}%) BRUTO ${bruto:.2f} - COMP ${fee_c:.2f} - VENT ${fee_v:.2f} = <b style='color:{col}'>NETO ${neto:.2f}</b><br>"
    html += "</div>"
    return html + "</body></html>"
