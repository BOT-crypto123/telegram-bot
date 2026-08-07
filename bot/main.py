import os
from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "BOT ON V39.6.15", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("Puerto " + str(port))
    app.run(host="0.0.0.0", port=port)
