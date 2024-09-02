import os
import asyncio
import logging
import json
from telegrambot.telegrambot2 import TelegramBot
from dotenv import load_dotenv
from aiogram.types import Message
from aiogram.filters import Command

# Erweiterte Log-Formatierung
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    load_dotenv()

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if TOKEN is None:
        logging.critical("Telegram bot token not found in environment variables")
        return

    bot = TelegramBot(token=TOKEN)

    async def handle_first_message(message: Message):
        test_chat_id = message.chat.id
        logging.info(f"Testing initiated by user: {message.from_user.username} in chat {test_chat_id}")

        try:
            # Test 1: Senden einer Nachricht
            logging.debug("Starting Test 1: Senden einer Nachricht...")
            await bot.send_message(test_chat_id, "Dies ist eine Testnachricht.")
            logging.info("Test 1: Nachricht erfolgreich gesendet.")

            # Test 2: Antworten auf die eingegangene Nachricht
            logging.debug("Starting Test 2: Antworten auf die Nachricht...")
            await bot.reply_to_message(message, "Dies ist eine Testantwort auf deine Nachricht.")
            logging.info("Test 2: Antwort auf Nachricht erfolgreich gesendet.")

            # Test 3: Abrufen des Nachrichtenverlaufs
            logging.debug("Starting Test 3: Abrufen des Nachrichtenverlaufs...")
            history = await bot.get_chat_history_json(test_chat_id, limit=10)
            logging.info(f"Test 3: Nachrichtenverlauf erfolgreich abgerufen: {len(history)} Nachrichten gefunden.")
            logging.debug(f"Abgerufene Nachrichten:\n{json.dumps(history, indent=4)}")

            # Test 4: Ausführen der /start- und /stop-Befehle
            logging.debug("Starting Test 4: Ausführen von /start und /stop Befehlen...")
            fake_start_message = Message(message_id=2, from_user=message.from_user, 
                                         chat=message.chat, date=message.date, text="/start")
            await bot.handle_start(fake_start_message)
            logging.info("Test 4: /start Befehl erfolgreich ausgeführt.")

            fake_stop_message = Message(message_id=3, from_user=message.from_user, 
                                        chat=message.chat, date=message.date, text="/stop")
            await bot.handle_stop(fake_stop_message)
            logging.info("Test 4: /stop Befehl erfolgreich ausgeführt.")

            logging.info("Alle Tests erfolgreich abgeschlossen.")

        except Exception as e:
            logging.error(f"Fehler während des Testens: {e}")

    def register_test_handler():
        logging.debug("Registrieren des Test-Handlers.")
        bot.router.message.register(handle_first_message)

    async def start_bot():
        register_test_handler()
        logging.info("Bot wird gestartet...")
        await bot.start()

    asyncio.run(start_bot())

if __name__ == "__main__":
    main()
