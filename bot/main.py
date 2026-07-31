from job import job, bot
import threading
import time

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
    threading.Thread(target=run_alerts, daemon=True).start()
    run_bot()
