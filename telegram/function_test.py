import os
import logging
import json
from telegrambot.telegrambot2 import TelegramBot
from dotenv import load_dotenv
from aiogram.types import Message

from aiogram.types import Chat, User
from datetime import datetime

def main():
    load_dotenv()

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if TOKEN is None:
        logging.critical("Telegram bot token not found in environment variables")
        return

    bot = TelegramBot(token=TOKEN)

    def run_tests():
        # Angenommen, wir haben einen Chat-ID, auf dem die Tests ausgeführt werden sollen
        test_chat_id = 749002085  # Diese ID sollte durch die tatsächliche Chat-ID ersetzt werden

        logging.info("Starting tests with the optimized TelegramBot class...")

        try:
            # Test 1: Senden einer Nachricht
            logging.debug("Test 1: Senden einer Nachricht...")
            bot.send_sync_message(test_chat_id, "Dies ist eine Testnachricht.")
            logging.info("Test 1 erfolgreich: Nachricht gesendet.")

            # Test 2: Ausführen der /start- und /stop-Befehle
            logging.debug("Test 2: Ausführen von /start und /stop Befehlen...")

            # Erstellen eines User- und Chat-Objekts, wie es in einer echten Nachricht vorkommen würde
            user = User(id=123456789, is_bot=False, first_name="Test", username="test_user")
            chat = Chat(id=test_chat_id, type="private")

            # Erstellen einer gefälschten Nachricht mit allen erforderlichen Feldern
            fake_start_message = Message(message_id=1, from_user=user, chat=chat, 
                                         date=datetime.now(), text="/start")
            fake_stop_message = Message(message_id=2, from_user=user, chat=chat, 
                                        date=datetime.now(), text="/stop")

            bot.loop.run_until_complete(bot.handle_start(fake_start_message))
            logging.info("Test 2.1 erfolgreich: /start Befehl ausgeführt.")

            bot.loop.run_until_complete(bot.handle_stop(fake_stop_message))
            logging.info("Test 2.2 erfolgreich: /stop Befehl ausgeführt.")

            # Test 3: Abrufen des Nachrichtenverlaufs
            logging.debug("Test 3: Abrufen des Nachrichtenverlaufs...")
            history = bot.get_chat_history(test_chat_id, limit=10)
            logging.info(f"Test 3 erfolgreich: {len(history)} Nachrichten im Verlauf gefunden.")
            logging.debug(f"Abgerufene Nachrichten:\n{history}")
            print(history)

            # Test 4: Abrufen aller aktiven Chats
            logging.debug("Test 4: Abrufen aller aktiven Chats...")
            active_chats = bot.get_active_chats()
            logging.info(f"Test 4 erfolgreich: {len(active_chats)} aktive Chats gefunden.")
            logging.debug(f"Aktive Chats:\n{json.dumps(active_chats, indent=4)}")
            print(active_chats)

            logging.info("Alle Tests erfolgreich abgeschlossen.")


        except Exception as e:
            logging.error(f"Fehler während des Testens: {e}")


    run_tests()

if __name__ == "__main__":
    main()
