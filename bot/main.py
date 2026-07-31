from flask import Flask
import os
import sys

print("INICIANDO BOT...", flush=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot OK - Live"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Corriendo en puerto {port}", flush=True)
    app.run(host="0.0.0.0", port=port)
