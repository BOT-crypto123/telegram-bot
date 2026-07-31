from job import job, bot
import threading
import time
import os
from flask import Flask

# Servidor falso para Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot de botones prendido..."

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    print("Bot de botones prendido...")
    bot.infinity_polling()

def run_alerts():
    while True:
        try:
            job()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=run_alerts, daemon=True).start()
    run_bot()
