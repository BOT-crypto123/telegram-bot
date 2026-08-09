import os,json,httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
a=FastAPI();T=os.getenv("TELEGRAM_TOKEN","");B=f"https://api.telegram.org/bot{T}";F="/tmp/b.json";N=chr(10)
def L():
 try:return json.load(open(F))
 except:return{"b":1000,"h":[],"v":[]}
def S(s):json.dump(s,open(F,"w"))
async def P(m):
 try:
  async with httpx.AsyncClient() as c:return float((await c.get(f"https://api.coin
