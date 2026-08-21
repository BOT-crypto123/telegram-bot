import os, requests, threading, time, traceback, random
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter
print('V146 INICIANDO - BASE 500 USD', flush=True)
TOKEN=os.environ.get('TELEGRAM_TOKEN')
URL='https://telegram-bot-cijp.onrender.com'
CONFIG={'BASE_USD':500.0,'BASE_MXN':9750.0,'ACUMULADO_MXN':310.0,'ACUMULADO_USD':15.90,'FEE_ENTRY_PCT':0.10,'FEE_EXIT_PCT':0.10,'TP_PCT':0.30,'AUTO':True,'BOLAS_MAX':6,'RATE_MXN':19.50}
MONEDAS={'ADA':True,'AVAX':True,'BNB':True,'BTC':False,'DOGE':True,'ETH':True,'SOL':True,'XRP':True}
bolas=[]
historial=[]
PRECIOS={}
def get_rate_mxn():
    try:
        r=requests.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTMXN',timeout=4)
        p=float(r.json()['price'])
        if 10 < p < 30:
            CONFIG['RATE_MXN']=p
            CONFIG['BASE_MXN']=CONFIG['BASE_USD']*p
            return p
    except: pass
    return CONFIG['RATE_MXN']
def get_precio(m):
    try:
        r=requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={m}USDT',timeout=4)
        p=float(r.json()['price']);PRECIOS[m]=p;return p
    except: return PRECIOS.get(m,0)
def get_total_mxn(): return CONFIG['BASE_MXN']+CONFIG['ACUMULADO_MXN']
def get_costo_mxn(): return get_total_mxn()/CONFIG['BOLAS_MAX']
def get_costo_usd(): return get_costo_mxn()/CONFIG['RATE_MXN']
def calc(entrada,salida,costo_usd,rate):
    if not entrada or salida==0: return {}
    pct=((salida-entrada)/entrada)*100
    bruta=costo_usd*(pct/100)
    com=costo_usd*0.001+(costo_usd+bruta)*0.001
    neta=bruta-com
    return {'pct_neto':(neta/costo_usd)*100,'neta_usd':neta,'neta_mxn':neta*rate}
def get_stats():
    rate=get_rate_mxn()
    CONFIG['ACUMULADO_MXN']=CONFIG['ACUMULADO_USD']*rate
    CONFIG['BASE_MXN']=CONFIG['BASE_USD']*rate
    for b in bolas:
        p=get_precio(b['moneda'])
        if p>0: b['actual']=p
        d=calc(b['compra'],b['actual'],b['costo_usd'],rate)
        b.update(d)
    total_mxn=get_total_mxn();total_usd=total_mxn/rate;prog=(datetime.now().day/30)*100
    return total_usd,total_mxn,0,0,prog,rate,get_costo_usd(),get_costo_mxn()
def comprar_bola(moneda):
    if len(bolas)>=CONFIG['BOLAS_MAX']: return None
    for x in bolas:
        if x['moneda']==moneda: return None
    p=get_precio(moneda)
    if p==0: return None
    bolas.append({'id':int(time.time()*1000),'moneda':moneda,'compra':p,'costo_usd':get_costo_usd(),'costo_mxn':get_costo_mxn(),'actual':p})
    return True
def vender_bola(id_bola):
    for b in bolas[:]:
        if str(b['id'])==str(id_bola):
            CONFIG['ACUMULADO_USD']+=b.get('neta_usd',0);CONFIG['ACUMULADO_MXN']+=b.get('neta_mxn',0)
            historial.insert(0,{'fecha':datetime.now().strftime('%d/%m %H:%M'),'moneda':b['moneda'],'neta_mxn':round(b.get('neta_mxn',0),2),'neta_usd':round(b.get('neta_usd',0),4),'pct_neto':round(b.get('pct_neto',0),3)})
            bolas.remove(b);return b
    return None
def resumen_total():
    if not historial: return {'total_entradas':0,'ganadas':0,'perdidas':0,'total_mxn':0,'mas_entradas':'-','mejor_moneda':'-'}
    total_mxn=sum(h['neta_mxn'] for h in historial)
    ganadas=len([h for h in historial if h['neta_mxn']>0])
    perdidas=len([h for h in historial if h['neta_mxn']<=0])
    conteo=Counter(h['moneda'] for h in historial)
    mas=conteo.most_common(1)[0][0] if conteo else '-'
    return {'total_entradas':len(historial),'ganadas':ganadas,'perdidas':perdidas,'total_mxn':total_mxn,'mas_entradas':mas}
def tabla_por_moneda():
    stats=defaultdict(lambda: {'entradas':0,'ganadas':0,'total_mxn':0.0})
    for h in historial:
        m=h['moneda'];stats[m]['entradas']+=1
        if h['neta_mxn']>0: stats[m]['ganadas']+=1
        stats[m]['total_mxn']+=h['neta_mxn']
    for b in bolas: stats[b['moneda']]['entradas']+=1
    return stats
def loop_auto():
    while True:
        try:
            if CONFIG['AUTO']:
                get_stats()
                for b in bolas[:]:
                    if b.get('pct_neto',0)>=CONFIG['TP_PCT']: vender_bola(b['id'])
                if len(bolas)<CONFIG['BOLAS_MAX']:
                    disp=[m for m,on in MONEDAS.items() if on and all(x['moneda']!=m for x in bolas)]
                    if disp: comprar_bola(random.choice(disp))
        except: print(traceback.format_exc(),flush=True)
        time.sleep(10)
threading.Thread(target=loop_auto,daemon=True).start()
app=Flask(__name__)
HTML_BYTES=[]
HTML_BYTES.extend([60, 33, 68, 79, 67, 84, 89, 80, 69, 32, 104, 116, 109, 108, 62, 60, 104, 116, 109, 108, 62, 60, 104, 101, 97])
HTML_BYTES.extend([100, 62, 60, 109, 101, 116, 97, 32, 110, 97, 109, 101, 61, 118, 105, 101, 119, 112, 111, 114, 116, 32, 99, 111, 110])
HTML_BYTES.extend([116, 101, 110, 116, 61, 39, 119, 105, 100, 116, 104, 61, 100, 101, 118, 105, 99, 101, 45, 119, 105, 100, 116, 104, 44])
HTML_BYTES.extend([32, 105, 110, 105, 116, 105, 97, 108, 45, 115, 99, 97, 108, 101, 61, 49, 39, 62, 60, 116, 105, 116, 108, 101, 62])
HTML_BYTES.extend([77, 65, 81, 85, 73, 78, 65, 32, 86, 49, 52, 54, 60, 47, 116, 105, 116, 108, 101, 62, 60, 47, 104, 101, 97])
HTML_BYTES.extend([100, 62, 60, 98, 111, 100, 121, 62, 60, 104, 49, 62, 77, 65, 81, 85, 73, 78, 65, 32, 66, 65, 83, 69, 32])
HTML_BYTES.extend([53, 48, 32, 85, 83, 68, 32, 45, 32, 86, 49, 52, 54, 32, 79, 75, 60, 47, 104, 49, 62, 60, 100, 105])
HTML_BYTES.extend([118, 32, 105, 100, 61, 98, 97, 115, 101, 62, 60, 47, 100, 105, 118, 62, 60, 100, 105, 118, 32, 105, 100, 61, 97])
HTML_BYTES.extend([99, 117, 109, 62, 60, 47, 100, 105, 118, 62, 60, 100, 105, 118, 32, 105, 100, 61, 99, 111, 115, 116, 111, 62, 60])
HTML_BYTES.extend([47, 100, 105, 118, 62, 60, 100, 105, 118, 32, 105, 100, 61, 109, 111, 110, 115, 62, 60, 47, 100, 105, 118, 62, 60])
HTML_BYTES.extend([100, 105, 118, 32, 105, 100, 61, 98, 111, 108, 97, 115, 62, 60, 47, 100, 105, 118, 62, 60, 100, 105, 118, 32, 105])
HTML_BYTES.extend([100, 61, 114, 101, 115, 117, 109, 101, 110, 62, 60, 47, 100, 105, 118, 62, 60, 115, 99, 114, 105, 112, 116, 62, 97])
HTML_BYTES.extend([115, 121, 110, 99, 32, 102, 117, 110, 99, 116, 105, 111, 110, 32, 108, 111, 97, 100, 40, 41, 123, 108, 101, 116, 32])
HTML_BYTES.extend([114, 61, 97, 119, 97, 105, 116, 32, 102, 101, 116, 99, 104, 40, 39, 47, 97, 112, 105, 47, 100, 97, 116, 97, 39])
HTML_BYTES.extend([41, 59, 108, 101, 116, 32, 100, 61, 97, 119, 97, 105, 116, 32, 114, 46, 106, 115, 111, 110, 40, 41, 59, 100, 111])
HTML_BYTES.extend([99, 117, 109, 101, 110, 116, 46, 103, 101, 116, 69, 108, 101, 109, 101, 110, 116, 66, 121, 73, 100, 40, 39, 98, 97])
HTML_BYTES.extend([115, 101, 39, 41, 46, 105, 110, 110, 101, 114, 84, 101, 120, 116, 61, 39, 84, 79, 84, 65, 76, 32, 36, 39, 43])
HTML_BYTES.extend([100, 46, 116, 111, 116, 97, 108, 95, 109, 120, 110, 46, 116, 111, 70, 105, 120, 101, 100, 40, 50, 41, 43, 39, 32])
HTML_BYTES.extend([77, 88, 78, 32, 66, 65, 83, 69, 32, 36, 39, 43, 100, 46, 99, 111, 110, 102, 105, 103, 46, 66, 65, 83, 69])
HTML_BYTES.extend([95, 77, 88, 78, 46, 116, 111, 70, 105, 120, 101, 100, 40, 48, 41, 43, 39, 32, 82, 65, 84, 69, 32, 36, 39])
HTML_BYTES.extend([43, 100, 46, 114, 97, 116, 101, 46, 116, 111, 70, 105, 120, 101, 100, 40, 50, 41, 59, 100, 111, 99, 117, 109, 101])
HTML_BYTES.extend([110, 116, 46, 103, 101, 116, 69, 108, 101, 109, 101, 110, 116, 66, 121, 73, 100, 40, 39, 97, 99, 117, 109, 39, 41])
HTML_BYTES.extend([46, 105, 110, 110, 101, 114, 84, 101, 120, 116, 61, 39, 65, 67, 85, 77, 32, 36, 39, 43, 100, 46, 99, 111, 110])
HTML_BYTES.extend([102, 105, 103, 46, 65, 67, 85, 77, 85, 76, 65, 68, 79, 95, 77, 88, 78, 46, 116, 111, 70, 105, 120, 101, 100])
HTML_BYTES.extend([40, 50, 41, 59, 100, 111, 99, 117, 109, 101, 110, 116, 46, 103, 101, 116, 69, 108, 101, 109, 101, 110, 116, 66, 121])
HTML_BYTES.extend([73, 100, 40, 39, 99, 111, 115, 116, 111, 39, 41, 46, 105, 110, 110, 101, 114, 84, 101, 120, 116, 61, 39, 67, 79])
HTML_BYTES.extend([83, 84, 79, 32, 36, 39, 43, 100, 46, 99, 111, 115, 116, 111, 95, 109, 120, 110, 46, 116, 111, 70, 105, 120, 101])
HTML_BYTES.extend([100, 40, 48, 41, 43, 39, 32, 84, 80, 32, 39, 43, 100, 46, 99, 111, 110, 102, 105, 103, 46, 84, 80, 95, 80])
HTML_BYTES.extend([67, 84, 43, 39, 37, 39, 59, 108, 101, 116, 32, 109, 61, 39, 39, 59, 102, 111, 114, 40, 108, 101, 116, 32, 107])
HTML_BYTES.extend([32, 105, 110, 32, 100, 46, 109, 111, 110, 101, 100, 97, 115, 41, 123, 108, 101, 116, 32, 99, 108, 115, 61, 100, 46])
HTML_BYTES.extend([109, 111, 110, 101, 100, 97, 115, 91, 107, 93, 63, 39, 111, 110, 39, 58, 39, 111, 102, 102, 39, 59, 109, 43, 61])
HTML_BYTES.extend([39, 60, 98
