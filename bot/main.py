def get_ticker(sym):
    t = yf.Ticker(sym)
    price = float(t.fast_info['last_price'])
    try:
        hist = t.history(period="1mo")
        pct = float((hist['Close'].iloc[-1]/hist['Close'].iloc[-2]-1)*100)
        # RSI fix
        delta = hist['Close'].diff()
        gain = delta.where(delta>0,0).rolling(window=14).mean()
        loss = -delta.where(delta<0,0).rolling(window=14).mean()
        rs = gain / loss
        rsi = float(100-(100/(1+rs.iloc[-1])))
        if rsi != rsi: rsi = 35.0 # si es nan, poner 35
    except:
        pct = 0.0
        rsi = 35.0
    return price, pct, round(rsi,1)
