if "BTC"in t:S="BTC"
if "ETH"in t:S="ETH"
if "SOL"in t:S="SOL"
if "XRP"in t:S="XRP"
if "AUTO"in t:
 O=not O;C=i
 m(i,"AUTO ON" if O else "AUTO OFF")
 return "ok",200
