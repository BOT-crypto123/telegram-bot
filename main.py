# ... deja todo lo de arriba igual hasta la función AN() ...

@app.route('/chart/<sym>')
def chart(sym):
    sym=sym.upper()
    pos_entry = 0
    for p in data['pos']:
        if p['sym']==sym:
            pos_entry = p.get('precio_entry',0)
            break
    return f"""
<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>body{{background:#080808;color:#fff;font-family:Arial;margin:0;padding:0}} #chart{{width:100%;height:70vh}} .top{{padding:12px;background:#111;display:flex;justify-content:space-between}} .btn{{padding:8px 16px;border-radius:8px;border:none;font-weight:bold}} </style>
</head><body>
<div class=top><b>{sym} - Entradas y Salidas</b><a href="/dashboard"><button class=btn style=background:#00ff88>⬅ Volver</button></a></div>
<div style=padding:8px><small>Verde = tu entrada | Rojo = salida RSI>70 | Amarilla EMA20 | Azul EMA50</small></div>
<div id=chart></div>
<script>
async function load(){{
  const sym='{sym}';
  const entry={pos_entry};
  const map={{'BTC':'BTCUSDT','ETH':'ETHUSDT','SOL':'SOLUSDT','XRP':'XRPUSDT','DOGE':'DOGEUSDT','AVAX':'AVAXUSDT','LINK':'LINKUSDT','ADA':'ADAUSDT'}};
  let data=[];
  try{{
    let r=await fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${{map[sym]}}&interval=1h&limit=150`);
    let kl=await r.json();
    data=kl.map(k=>({{time:k[0]/1000,open:parseFloat(k[1]),high:parseFloat(k[2]),low:parseFloat(k[3]),close:parseFloat(k[4])}}));
  }}catch(e){{
    // fallback si bloquea
    data=[];
  }}
  const chart=LightweightCharts.createChart(document.getElementById('chart'),{{layout:{{background:{{type:'solid',color:'#080808'}},textColor:'#fff'}},grid:{{vertLines:{{color:'#222'}},horzLines:{{color:'#222'}}} }});
  const candle=chart.addCandlestickSeries();
  candle.setData(data);
  
  // EMA 20 amarilla
  if(data.length>20){{
    const ema20=chart.addLineSeries({{color:'#ffcc00',lineWidth:2}});
    let emaData=[];
    let sum=0;
    for(let i=0;i<data.length;i++){{
      sum+=data[i].close;
      if(i>=20){{
        sum-=data[i-20].close;
        emaData.push({{time:data[i].time,value:sum/20}});
      }}
    }}
    ema20.setData(emaData);
  }}
  // EMA 50 azul como tu foto
  if(data.length>50){{
    const ema50=chart.addLineSeries({{color:'#00ccff',lineWidth:2}});
    let emaData=[];
    let sum=0;
    for(let i=0;i<data.length;i++){{
      sum+=data[i].close;
      if(i>=50){{
        sum-=data[i-50].close;
        emaData.push({{time:data[i].time,value:sum/50}});
      }}
    }}
    ema50.setData(emaData);
  }}
  // LINEA DE ENTRADA
  if(entry>0){{
    const line=chart.addLineSeries({{color:'#00ff88',lineWidth:2,lineStyle:2}});
    line.setData(data.map(d=>({{time:d.time,value:entry}})));
    // marcador
    candle.setMarkers([{{time:data[data.length-1].time,position:'belowBar',color:'#00ff88',shape:'arrowUp',text:`Entrada ${{entry}}`}}]);
  }}
  chart.timeScale().fitContent();
}}
load();
</script>
</body></html>
"""

@app.route('/')
@app.route('/dashboard')
def dash():
    total=totals()
    html=f"""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{{background:#080808;color:#fff;font-family:Arial;margin:0;padding:8px}}.top{{display:flex;justify-content:space-between;background:#111;padding:12px;border-radius:16px;border:1px solid #00ff88;margin-bottom:8px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.card{{background:#151515;border:2px solid #ffcc00;border-radius:18px;padding:10px;cursor:pointer}}.card.green{{border-color:#00ff88}}.card.red{{border-color:#ff4444}}.score{{float:right;background:#111;border:2px solid #ffcc00;border-radius:12px;padding:6px 14px;font-size:22px;font-weight:bold;color:#ffcc00}}.btn{{width:100%;padding:10px;border-radius:10px;border:none;font-weight:bold;margin-top:6px}}.btn.g{{background:#00ff88}}.btn.r{{background:#ff3344;color:#fff}}.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:bold}}.badge.y{{background:#ffcc00;color:#000}}.badge.g{{background:#00ff88;color:#000}}.pos{{background:#111;border-radius:16px;padding:12px;margin-top:10px;border:1px solid #333}}</style></head><body>
<div class=top><b style=color:#00ff88>V1002.23 CHARTS</b><div><span style=background:#ffeb3b;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold>${total:.0f}</span> <span style=background:#00ff88;color:#000;padding:6px 12px;border-radius:20px;font-weight:bold>ON</span></div></div>
<div style=background:#151515;padding:8px;border-radius:12px;margin-bottom:8px;text-align:center><small>👆 TOCA CUALQUIER MONEDA PARA VER GRÁFICA CON ENTRADAS/SALIDAS</small></div>
<div class=grid>"""
    for sym in data['coins']:
        rsi,price=AN(sym)
        score=int(100-rsi) if rsi<50 else 100-int(rsi)
        score=max(20,min(85,score))
        border="green" if rsi<32 else "red" if rsi>70 else ""
        action="COMPRAR" if rsi<32 else "VENDER" if rsi>70 else "SOSTENER"
        badge="g" if rsi<32 else "y"
        holding=any(p['sym']==sym for p in data['pos'])
        btn_t="VENDER" if holding else "COMPRAR"
        btn_c="r" if holding else "g"
        # AHORA LA TARJETA ES CLICKEABLE A LA GRAFICA
        html+=f"""<div class="card {border}" onclick="window.location='/chart/{sym}'"><b>{sym} ${price:.2f}</b> <span class=score>{score}</span><br><small>PUNTUACIÓN {score} • RSI {rsi:.1f}</small><br><span class="badge {badge}">{action}</span><div style=height:40px;background:linear-gradient(0deg,#ffcc0033,transparent);margin:8px 0;border-radius:8px"></div><div style=display:flex;gap:4px><a href="/buy/{sym}" style=flex:1 onclick="event.stopPropagation()"><button class="btn {btn_c}" style=width:100%>{btn_t}</button></a></div></div>"""
    pos_rows=""
    for p in data['pos']:
        pr=P(p['sym'])
        col="#00ff88" if p.get('gan',0)>=0 else "#ff4444"
        pos_rows+=f"<div style=display:flex;justify-content:space-between;padding:6px;border-bottom:1px solid #222><span onclick=\"window.location='/chart/{p['sym']}'\" style=cursor:pointer>{p['sym']} <span style=color:{col}>{p.get('gan',0):.2f}%</span> Entry ${p.get('precio_entry',0):.2f} 👁️ Ver gráfica</span><a href='/sell/{p['sym']}' style=background:#ff3344;color:#fff;padding:2px 8px;border-radius:6px;text-decoration:none;font-size:11px>VENDEDOR</a></div>"
    html+=f"</div><div class=pos><b>Posiciones abiertas ({len(data['pos'])}/5)</b><br><br>{pos_rows}<br><small>TOCÁ la tarjeta para ver gráfica con líneas como tu foto</small></div></body></html>"
    return html

# ... deja el resto buy/sell/webhook/auto_loop igual que V1002.22 ...
