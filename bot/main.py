  return {"ok":True}
 if text=="AUTO OFF":
  s["auto"]=False
  save_state(s)
  await send_menu(chat_id,f"AUTO DESACTIVADO {DASH_URL}")
  return {"ok":True}
 if text in ["ESTADO","PORTAFOLIO","BALANCE"]:
  bal=s["virtual_balance"]
  holds=s.get("holdings",{})
  txt=f"PORTAFOLIO V867\nSaldo: ${bal:.2f}\nAuto: {s.get('auto',False)}\n\n"
  tot=bal
  for k,v in holds.items():
   p,_=await get_data(k)
   val=v["amount"]*p
   gan=((p-v["entry"])/v["entry"]*100) if v["entry"]>0 else 0
   txt+=f"{k}: {v['amount']:.5f} = ${val:.2f} ({gan:+.1f}%)\n"
   tot+=val
  txt+=f"\nTotal: ${tot:.2f}\n{DASH_URL}"
  save_state(s)
  await send_menu(chat_id,txt)
  return {"ok":True}
 save_state(s)
 if text in MONEDAS:
  p,c=await get_data(text)
  await send_msg(chat_id,f"{text}: ${p:,.2f} ({c:+.2f}%) Bal ${s['virtual_balance']:.2f}",text,True)
 else:
  await send_menu(chat_id,f"V867 Bal ${s['virtual_balance']:.2f} {DASH_URL}")
 return {"ok":True}
@app.get("/")
def home():
 return {"V867":DASH_URL}
