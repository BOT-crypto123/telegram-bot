def main():
    # Mata cualquier webhook/polling viejo que cause Conflict
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=5)
        print("Webhook viejo borrado", flush=True)
    except: pass
    
    time.sleep(3) # espera a que muera el otro
    threading.Thread(target=run_web, daemon=True).start()
    print("Iniciando bot...", flush=True)
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("btc", cmd_btc))
    application.add_handler(CommandHandler("eth", cmd_eth))
    application.add_handler(CommandHandler("xrp", cmd_xrp))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CallbackQueryHandler(buttons))
    application.job_queue.run_repeating(alerta_inteligente, interval=300, first=30)
    print("Bot polling iniciado - V20.1 LIVE", flush=True)
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
