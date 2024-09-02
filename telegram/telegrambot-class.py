import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from typing import List, Dict, Callable


# Einrichten des Loggings, um Informationen, Warnungen und Fehler zu protokollieren.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramBot:
    def __init__(self, token: str):
        """
        Initialisiert den TelegramBot mit dem bereitgestellten Token und richtet
        den Bot, Dispatcher und Router ein.
        
        :param token: Der Token des Telegram-Bots, der von der BotFather-Telegram-Anwendung
                      bereitgestellt wird, um den Bot mit der API zu verbinden.
        """
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)

        # Hier speichern wir die Nachrichtenverläufe im Speicher.
        self.chat_histories = {}

        # Registrierung von Standardbefehlen wie /start und /stop.
        self.register_default_commands()

    def register_default_commands(self):
        """
        Registriert Standardbefehle wie /start und /stop.
        """
        self.add_command("default_start", self.handle_start)
        self.add_command("default_stop", self.handle_stop)

    def add_command(self, command_name: str, command_handler: Callable):
        """
        Fügt einen neuen Befehl zum Bot hinzu.

        :param command_name: Der Name des Befehls (ohne führendes /).
        :param command_handler: Die Funktion, die ausgeführt werden soll, wenn der Befehl eingegeben wird.
        """
        self.router.message.register(command_handler, Command(commands=[command_name]))

    async def handle_start(self, message: Message):
        """
        Verarbeitet den /start Befehl und sendet eine Begrüßungsnachricht zurück.
        
        :param message: Die empfangene Nachricht vom Benutzer.
        """
        logging.info(f"Received /start command from {message.from_user.username}")
        await self.send_message(message.chat.id, "Willkommen! Der Bot ist jetzt aktiv.")

    async def handle_stop(self, message: Message):
        """
        Verarbeitet den /stop Befehl und sendet eine Abschiedsmitteilung zurück.
        
        :param message: Die empfangene Nachricht vom Benutzer.
        """
        logging.info(f"Received /stop command from {message.from_user.username}")
        await self.send_message(message.chat.id, "Der Bot wird jetzt deaktiviert. Bis zum nächsten Mal!")

    async def send_message(self, chat_id: int, text: str):
        """
        Sendet eine Nachricht an einen spezifischen Chat.

        :param chat_id: Die ID des Chats, an den die Nachricht gesendet werden soll.
        :param text: Der Inhalt der Nachricht, die gesendet werden soll.
        """
        try:
            message = await self.bot.send_message(chat_id, text)
            logging.info(f"Message sent to {chat_id}: {text}")
            self.save_message_to_history(message)
        except Exception as e:
            logging.error(f"Failed to send message to {chat_id}: {e}")

    def save_message_to_history(self, message: Message):
        """
        Speichert die eingehende Nachricht im Verlauf des Chats.

        :param message: Die Nachricht, die gespeichert werden soll.
        """
        chat_id = message.chat.id
        if chat_id not in self.chat_histories:
            self.chat_histories[chat_id] = []

        # Nachricht speichern
        self.chat_histories[chat_id].append({
            "message_id": message.message_id,
            "from_user": message.from_user.username if message.from_user else "Bot",
            "text": message.text
        })

    async def get_chat_history_json(self, chat_id: int, limit: int = 100) -> List[Dict]:
        """
        Gibt den Nachrichtenverlauf eines bestimmten Chats im JSON-Format zurück.
        Der Verlauf wird intern im Speicher gehalten und enthält sowohl Nachrichten des Benutzers als auch des Bots.

        :param chat_id: Die ID des Chats, dessen Nachrichtenverlauf abgerufen werden soll.
        :param limit: Die maximale Anzahl der Nachrichten, die abgerufen werden sollen.
        :return: Eine Liste von Nachrichten im JSON-Format.
        """
        # Abrufen des Verlaufs aus dem Speicher
        if chat_id in self.chat_histories:
            history = self.chat_histories[chat_id][-limit:]  # Nur die letzten 'limit' Nachrichten
            logging.info(f"Retrieved {len(history)} messages from chat {chat_id}")
            return history
        else:
            logging.info(f"No history found for chat {chat_id}")
            return []


    async def reply_to_message(self, message: Message, text: str):
        """
        Antwortet auf eine erhaltene Nachricht.

        :param message: Die empfangene Nachricht, auf die geantwortet werden soll.
        :param text: Der Inhalt der Antwortnachricht.
        """
        try:
            reply_message = await message.answer(text)
            logging.info(f"Replied to message from {message.from_user.username}: {text}")
            self.save_message_to_history(reply_message)
        except Exception as e:
            logging.error(f"Failed to reply to message: {e}")
        

        # Nachricht in den Verlauf speichern
        self.save_message_to_history(message)

    async def start(self):
        """
        Startet den Bot und den Dispatcher im asynchronen Modus, um auf neue Updates zu reagieren.
        """
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)
