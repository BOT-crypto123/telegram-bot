import os
import requests
import io
import json
import time
import threading as th
from flask import Flask, request

T = os.getenv("TELE_TOKEN") or ""
A = Flask(__name__)
S = "XRP"
E = {}
O = False
C = 0
LC = {}

def p(s):
    try:
        u = f"https://api.coinbase.com/v2/prices/{s}-USD/spot"
        j = requests.get(u, timeout=8).json()
        return float(j["data"]["amount"])
    except:
        return 0

def q(s):
    try:
        u = f"https://api.exchange.coinbase.com/products/{s}-USD/candles?granularity=60"
        j = requests.get(u, timeout=10).json()
        if not isinstance(j, list):
            return []
        o = []
        for c in j:
            try:
                float(c[4])
                o.append(c)
            except:
                continue
        return sorted(o)[-60:]
    except:
        return []

def rsi(a):
    if len(a) < 15:
        return 50
    g = 0
    l = 0
    for i in range(1, 15):
        d = a[i] - a[i-1]
        if d > 0:
            g += d
        else:
            l += -d
    if l == 0:
        return 88
    return 100 - 100 / (1 + g / l)

def em(a, n):
    if len(a) < n:
        return a[-1]
    k = 2 / (n +
