if txt in data["coins"]:
    if len(data["pos"])<5 and not any(p['sym']==txt for p in data["pos"]):
        rsi,price,ema20,btc_t=AN(txt)
        # compra manual IGNORA auto_buy
        data["pos"].append({"sym":txt,"monto":50,"gan":0,"precio_entry":price,"max_price":price}); data["b"]-=50; data["trades_hoy"]+=1; save()
        tg(chat,f"✅ {txt} MANUAL ${price:.2f} RSI {rsi:.1f}")
