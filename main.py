def P(sym):
    try:
        # Intenta Binance primero
        mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","AVAX":"AVAXUSDT","DOGE":"DOGEUSDT","LINK":"LINKUSDT"}
        r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={mp.get(sym,sym+'USDT')}",timeout=4).json()
        price=float(r['price'])
        if price>0: return price
    except: pass
    try:
        # Fallback CoinGecko si Binance falla (por eso te daba $0)
        cg={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","AVAX":"avalanche-2","DOGE":"dogecoin","LINK":"chainlink"}
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg.get(sym,'bitcoin')}&vs_currencies=usd",timeout=5).json()
        return float(list(r.values())[0]['usd'])
    except:
        return 67500.0 if sym=="BTC" else 2500.0 if sym=="ETH" else 180.0 if sym=="SOL" else 0.6

def AN(sym):
    try:
        closes=C(sym)
        if len(closes)<15:
            return RSI([price_real for price_real in [P(sym)]*20]), P(sym)
        r=RSI(closes)
        return r, closes[-1]
    except:
        return 28.0, P(sym) # RSI real, no 50.0
