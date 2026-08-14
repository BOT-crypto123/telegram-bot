# V50.5 MAQUINA DE HACER DINERO 💰 FIX GRAFICA + NO RESET
# SOLO CAMBIA dash() y graf() por estos:

@app.route('/')
def dash():
    spy_v,spy_c=spy_real()
    html=f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#000;color:#fff;font-family:Arial;padding:10px}}.card{{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:8px 0}}.v{{color:#00ff88}}.n{{color:orange}}.btn{{background:#00ff88;color:#000;padding:10px 18px;border-radius:8px;text-decoration:none;display:inline-block;margin:4px;font-weight:bold}}pre{{white-space:pre-wrap}}</style></head><body><h2>💰 MAQUINA DE HACER DINERO 💰 V50.5 DEMO PAPER</h2><div class="card">SPY REAL: {"🟢" if spy_v else "🔴"} {spy_c:+.2f}% | NY: {datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M")} | 1x día | {demo_stats_text().replace(chr(10),"<br>")}</div>"""
    for s in SYMBOLS:
        try: d=decide(s)
        except: d={"compra":False,"tipo":"CARGANDO...","detalle":"Reintentando","lineas":[],"score":0,"bola":0}
        color="v" if d["compra"] else "n"
        precio=get_price(s)
        html+=f'<div class="card"><b>{s}</b> ${precio:.2f} | <span class="{color}">{d["tipo"]}</span><br><small>{d["detalle"].replace(chr(10),"<br>")}</small><br><a class="btn" href="/graf/{s}">GRAFICA VIVA PRO 📈</a> <a class="btn" href="/forzar/{s}">FORZAR</a></div>'
    # BOTON RESET ELIMINADO - SOLO STATS
    html+=f'<div class="card"><a class="btn" href="/stats">VER STATS 8-13%</a></div></body></html>'
    return html

@app.route('/graf/<s>')
def graf(s):
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        s=s.upper()
        # USA TUS VELAS REALES QUE SI JALAN - NO YAHOO
        opens,highs,lows,closes,vol = get_velas(s)
        if not closes or len(closes)<20:
            return f"<h1 style='background:#000;color:#fff'>Sin datos {s} - Reintenta 10s</h1><a href='/'>VOLVER</a>"
        d=decide(s)
        lineas=d.get("lineas",[])
        # GRAFICA PRO QUE NO CRASHEA
        fig=plt.figure(figsize=(12,6),facecolor='black')
        ax=plt.subplot2grid((4,1),(0,0),rowspan=3,facecolor='black')
        ax2=plt.subplot2grid((4,1),(3,0),facecolor='black')
        n=len(closes)
        for i in range(max(0,n-80), n):
            idx=i
            col='#00ff88' if closes[idx]>=opens[idx] else '#ff4444'
            ax.plot([idx,idx],[lows[idx],highs[idx]],color=col,lw=1)
            ax.plot([idx,idx],[opens[idx],closes[idx]],color=col,lw=3)
        # LINEAS
        for x in lineas[:6]:
            col='#00ff00' if x['rebotes']>=4 else '#ffaa00'
            ax.axhline(x['precio'],color=col,ls='--',lw=1.2,alpha=0.9)
            ax.text(n-75,x['precio'],f" {x['rebotes']}R {x['fuerza']:.0f}%",color=col,fontsize=8,backgroundcolor='black')
        ax.set_xlim(max(0,n-80), n)
        ax.set_title(f'MAQUINA DE HACER DINERO 💰 {s} ${closes[-1]:.2f} {d.get("tipo","")}',color='white',fontsize=10)
        ax.tick_params(colors='white'); ax.grid(True,alpha=0.1)
        # RSI REAL
        rsi_vals=[]
        for i in range(15,len(closes)):
            rsi_vals.append(rsi_calc(closes[:i+1]))
        ax2.plot(range(len(closes)-len(rsi_vals), len(closes)), rsi_vals, color='#00ffff', lw=1.5)
        ax2.axhline(70,color='red',ls='--',alpha=0.4); ax2.axhline(30,color='green',ls='--',alpha=0.4)
        ax2.set_ylim(0,100); ax2.tick_params(colors='white'); ax2.grid(True,alpha=0.1)
        buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf,format='png',facecolor='black',dpi=120); buf.seek(0)
        img=base64.b64encode(buf.read()).decode(); plt.close('all')
        detalle = d.get("detalle","").replace("<","").replace(">","")
        return f'<html style="background:#000;color:#fff;font-family:Arial"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="padding:10px"><h2>💰 MAQUINA DE HACER DINERO 💰 {s} ${closes[-1]:.2f}</h2><pre style="background:#111;padding:12px;border-radius:8px;white-space:pre-wrap">{detalle}</pre><img src="data:image/png;base64,{img}" style="width:100%;border-radius:12px"><br><br><a href="/" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">← VOLVER</a></body></html>'
    except Exception as e:
        import traceback
        return f'<html style="background:#000;color:#fff"><body><h2>Error graf {s}: {e}</h2><pre>{traceback.format_exc()}</pre><a href="/">VOLVER</a></body></html>'

# EN TELEGRAM - QUITA RESET
# Cambia tu handler RESET por esto:
# elif "RESET" in t:
#    bot.send_message(m.chat.id,"❌ RESET DESACTIVADO para proteger tu DEMO 1 MES 8-13%")
