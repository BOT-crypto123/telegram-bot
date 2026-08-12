import requests

NPOINT_ID = os.getenv("NPOINT_ID", "")

def load_data():
    # 1. Intenta de la nube gratis
    if NPOINT_ID:
        try:
            r = requests.get(f"https://api.npoint.io/{NPOINT_ID}", timeout=10)
            if r.status_code == 200:
                print("✅ Datos cargados de la nube gratis")
                return r.json()
        except Exception as e:
            print("Error npoint load:", e)
    # 2. Local
    try:
        with open("data.json","r") as f:
            return json.load(f)
    except:
        return {"b":5000,"pos":[],"coins":ALL_COINS,"gan_total":0,"gan_hoy":0,"trades_hoy":0,"auto_buy":True,"alert_users":[],"last_report_date":"","last_apertura":""}

def save_data():
    # 1. Guarda local
    try:
        with open("data.json","w") as f:
            json.dump(data,f)
    except: pass
    # 2. Guarda en la nube gratis
    if NPOINT_ID:
        try:
            requests.post(f"https://api.npoint.io/{NPOINT_ID}", json=data, timeout=10)
            print("✅ Guardado en nube")
        except Exception as e:
            print("Error npoint save:", e)

# Reemplaza tu carga inicial por:
data = load_data()
data["coins"] = ALL_COINS

# Y tu funcion save() vieja por:
def save():
    save_data()
