import os,requests,threading,time
from flask import Flask,request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=5.0;TP=10.0
ENTS={};LAST={};CHATS=set();ABUY={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def get_hist(s):
 try:
  url="https://api.coingecko.com/api/v3/coins/"+s.lower()+"/market_chart?vs_currency=usd&days=1"
  if s=="XRP": s="ripple"
  if s=="BTC": url="https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1"
  if s=="ETH": url="https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1"
  if s=="SOL": url="https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=1"
  if s=="XRP": url="https://api.coingecko.com/api/v3/coins/ripple/market_chart?vs_currency=usd&days=1"
  r=requests.get(url,timeout=10).json()
  ps=[x[1] for x in r["prices"]]
  return ps
