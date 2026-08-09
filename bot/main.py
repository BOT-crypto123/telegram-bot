from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>JOHAN BOT V505 - ONLINE</h1><p>Si ves esto, Render ya funciona.</p><p>Ahora dime y te agrego el dashboard BTC 15min.</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
