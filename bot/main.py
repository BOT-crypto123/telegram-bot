import os,requests,io,json,time,threading as th
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP";E={};O=False;C=0;LC={}
def p(s):
 try:
  d=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(d["data"]["amount"])
 except: return 0
def q(s):
 try:
  d=requests.get("https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json()
  return
