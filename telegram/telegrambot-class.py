import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram import Router
from aiogram import Dispatcher
from aiogram import Bot
from aiogram import Router
from aiogram.types import Message


from typing import List

# Einrichten des Loggings, um Informationen, Warnungen und Fehler zu protokollieren.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramBot:
    def __init__(self, token: str):
        """
        Initialisiert den TelegramBot mit dem bereitgestellten Token und richtet
        den Bot und Dispatcher ein.

        :param token: Der Token des Telegram-Bots, der von der BotFather-Telegram-Anwendung
                      bereitgestellt wird, um den Bot mit der API zu verbinden.
        """
        # Initialisieren des Bot-Objekts mit dem angegebenen Token.
        self.bot = Bot(token=token)
        
        # Dispatcher verwaltet die Verarbeitung von eingehenden Updates (Nachrichten, Befehle, etc.).
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)

        # Registrierung von Handlers, die auf bestimmte Updates reagieren.
        self.register_handlers()

    def register_handlers(self):
        """
        Registriert die Handler für verschiedene Arten von Updates, die der Bot
        verarbeiten soll. In diesem Fall wird ein einfacher Nachrichten-Handler
        registriert.
        """
        # Registriert einen Nachrichten-Handler, der alle eingehenden Nachrichten verarbeitet.
        self.router.message.register(self.handle_message)

    async def handle_message(self, message: Message):
        """
        Verarbeitet eingehende Nachrichten, protokolliert sie und sendet eine
        Echo-Antwort zurück.

        :param message: Die empfangene Nachricht vom Benutzer, die verarbeitet werden soll.
        """
        # Loggen der eingehenden Nachricht, einschließlich des Benutzernamens und des Inhalts.
        logging.info(f"Received message from {message.from_user.username}: {message.text}")
        
        # Senden einer Echo-Antwort an den Absender der Nachricht.
        await message.answer(f"Echo: {message.text}")

    async def send_message(self, chat_id: int, text: str):
        """
        Sendet eine Nachricht an einen spezifischen Chat. 

        :param chat_id: Die ID des Chats, an den die Nachricht gesendet werden soll.
        :param text: Der Inhalt der Nachricht, die gesendet werden soll.
        """
        try:
            # Senden der Nachricht an den angegebenen Chat.
            await self.bot.send_message(chat_id, text)
            
            # Loggen der erfolgreichen Zustellung der Nachricht.
            logging.info(f"Message sent to {chat_id}: {text}")
        except Exception as e:
            # Loggen eines Fehlers, falls das Senden der Nachricht fehlschlägt.
            logging.error(f"Failed to send message to {chat_id}: {e}")

    async def get_chat_history(self, chat_id: int, limit: int = 100) -> List[Message]:
        """
        Ruft die letzten Nachrichten eines bestimmten Chats ab.

        :param chat_id: Die ID des Chats, dessen Nachrichten abgerufen werden sollen.
        :param limit: Die maximale Anzahl der Nachrichten, die abgerufen werden sollen (Standard: 100).
        :return: Eine Liste der abgerufenen Nachrichten.
        """
        try:
            # Abrufen der letzten 'limit' Nachrichten aus dem angegebenen Chat.
            messages = await self.bot.get_chat_history(chat_id, limit=limit)
            
            # Loggen der Anzahl der abgerufenen Nachrichten.
            logging.info(f"Retrieved {len(messages)} messages from chat {chat_id}")
            
            # Rückgabe der abgerufenen Nachrichten.
            return messages
        except Exception as e:
            # Loggen eines Fehlers, falls das Abrufen der Chat-Historie fehlschlägt.
            logging.error(f"Failed to retrieve chat history from {chat_id}: {e}")
            return []

    async def start(self):
        """
        Startet den Bot und den Dispatcher im asynchronen Modus, um auf neue Updates zu reagieren.
        """
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    import os
    import asyncio
    from dotenv import load_dotenv

    # Laden von Umgebungsvariablen aus einer .env-Datei (z.B. Bot-Token).
    load_dotenv()

    # Abrufen des Telegram-Bot-Tokens aus den Umgebungsvariablen.
    TOKEN = "7234456200:AAHa_WVjYC3aGsDcHVT6Sfwk2xkmXN8Xkzw"

    # Überprüfen, ob der Bot-Token erfolgreich geladen wurde.
    if TOKEN is None:
        # Loggen eines Fehlers, falls der Token nicht gefunden wurde.
        logging.error("Telegram bot token not found in environment variables")
    else:
        # Initialisieren und Starten des Bots mit dem geladenen Token.
        bot = TelegramBot(token=TOKEN)
        
        # Starten des Bots und des Event Loops.
        asyncio.run(bot.start())

