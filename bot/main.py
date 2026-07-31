from flask import Flask
import os, threading, time, traceback

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot OK - Live"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Prende el web server en segundo plano
threading.Thread(target=run_web, daemon=True).start()

print("Iniciando bot...")

try:
    from job import job, bot

    def run_bot():
        print("Bot de botones prendido y escuchando...")
        bot.infinity_polling()

    def run_alerts():
        while True:
            try:
                job()
            except Exception as e:
                print(f"Error en job: {e}")
            time.sleep(3600)

    threading.Thread(target=run_alerts, daemon=True).start()
    run_bot()

except Exception as e:
    print("SE TRONO AL INICIAR:")
    traceback.print_exc()
    while True:
        time.sleep(10)
