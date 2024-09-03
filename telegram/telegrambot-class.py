import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from typing import List, Dict, Callable, Optional
import asyncio

# Einrichten des Loggings, um Informationen, Warnungen und Fehler zu protokollieren.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramBot:
    def __init__(self, token: str, logging_level: int = logging.INFO):
        """
        Initialisiert den TelegramBot mit dem bereitgestellten Token und richtet
        den Bot, Dispatcher und Router ein.
        
        :param token: Der Token des Telegram-Bots, der von der BotFather-Telegram-Anwendung
                      bereitgestellt wird, um den Bot mit der API zu verbinden.
        :param logging_level: Das Logging-Level, das eingestellt werden soll (Standard: logging.INFO).
        """
        logging.basicConfig(level=logging_level)
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)

        # Hier speichern wir die Nachrichtenverläufe im Speicher.
        self.chat_histories = {}

        # Registrierung von Standardbefehlen wie /start und /stop.
        self.register_default_commands()

        # Registrierung der asynchronen Funktionen für einfacheren externen Aufruf
        self.loop = asyncio.get_event_loop()

    def register_default_commands(self, start_command: str = "start", stop_command: str = "stop"):
        """
        Registriert Standardbefehle wie /start und /stop.

        :param start_command: Der Name des Startbefehls (Standard: "start").
        :param stop_command: Der Name des Stopbefehls (Standard: "stop").
        """
        self.add_command(start_command, self.handle_start)
        self.add_command(stop_command, self.handle_stop)

    def add_command(self, command_name: str, command_handler: Callable):
        """
        Fügt einen neuen Befehl zum Bot hinzu.

        :param command_name: Der Name des Befehls (ohne führendes /).
        :param command_handler: Die Funktion, die ausgeführt werden soll, wenn der Befehl eingegeben wird.
        """
        self.router.message.register(command_handler, Command(commands=[command_name]))

    async def handle_start(self, message: Message, start_message: str = "Willkommen! Der Bot ist jetzt aktiv."):
        """
        Verarbeitet den /start Befehl und sendet eine Begrüßungsnachricht zurück.
        
        :param message: Die empfangene Nachricht vom Benutzer.
        :param start_message: Die Nachricht, die beim Start gesendet wird (Standard: "Willkommen! Der Bot ist jetzt aktiv.").
        """
        logging.info(f"Received /start command from {message.from_user.username}")
        await self.send_message(message.chat.id, start_message)
        self.save_message_to_history(message)

    async def handle_stop(self, message: Message, stop_message: str = "Der Bot wird jetzt deaktiviert. Bis zum nächsten Mal!"):
        """
        Verarbeitet den /stop Befehl und sendet eine Abschiedsmitteilung zurück.
        
        :param message: Die empfangene Nachricht vom Benutzer.
        :param stop_message: Die Nachricht, die beim Stop gesendet wird (Standard: "Der Bot wird jetzt deaktiviert. Bis zum nächsten Mal!").
        """
        logging.info(f"Received /stop command from {message.from_user.username}")
        await self.send_message(message.chat.id, stop_message)
        self.save_message_to_history(message)

    async def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None):
        """
        Sendet eine Nachricht an einen spezifischen Chat.

        :param chat_id: Die ID des Chats, an den die Nachricht gesendet werden soll.
        :param text: Der Inhalt der Nachricht, die gesendet werden soll.
        :param parse_mode: Die Parse-Mode für die Nachricht (z.B. "Markdown", "HTML").
        :param disable_web_page_preview: Deaktiviert die Web-Vorschau für Links (Standard: None).
        :param disable_notification: Sendet die Nachricht ohne Benachrichtigung (Standard: None).
        """
        try:
            message = await self.bot.send_message(chat_id, text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview, disable_notification=disable_notification)
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

    async def get_chat_history_json(self, chat_id: int, limit: int = 100, reverse: bool = False) -> List[Dict]:
        """
        Gibt den Nachrichtenverlauf eines bestimmten Chats im JSON-Format zurück.
        Der Verlauf wird intern im Speicher gehalten und enthält sowohl Nachrichten des Benutzers als auch des Bots.

        :param chat_id: Die ID des Chats, dessen Nachrichtenverlauf abgerufen werden soll.
        :param limit: Die maximale Anzahl der Nachrichten, die abgerufen werden sollen (Standard: 100).
        :param reverse: Gibt den Verlauf in umgekehrter Reihenfolge zurück (Standard: False).
        :return: Eine Liste von Nachrichten im JSON-Format.
        """
        if chat_id in self.chat_histories:
            history = self.chat_histories[chat_id][-limit:]  # Nur die letzten 'limit' Nachrichten
            if reverse:
                history.reverse()
            logging.info(f"Retrieved {len(history)} messages from chat {chat_id}")
            return history
        else:
            logging.info(f"No history found for chat {chat_id}")
            return []

    async def reply_to_message(self, message: Message, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None):
        """
        Antwortet auf eine erhaltene Nachricht.

        :param message: Die empfangene Nachricht, auf die geantwortet werden soll.
        :param text: Der Inhalt der Antwortnachricht.
        :param parse_mode: Die Parse-Mode für die Nachricht (z.B. "Markdown", "HTML").
        :param disable_web_page_preview: Deaktiviert die Web-Vorschau für Links (Standard: None).
        :param disable_notification: Sendet die Antwort ohne Benachrichtigung (Standard: None).
        """
        try:
            reply_message = await message.answer(text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview, disable_notification=disable_notification)
            logging.info(f"Replied to message from {message.from_user.username}: {text}")
            self.save_message_to_history(reply_message)
        except Exception as e:
            logging.error(f"Failed to reply to message: {e}")

        # Nachricht in den Verlauf speichern
        self.save_message_to_history(message)

    async def start(self, drop_pending_updates: bool = True):
        """
        Startet den Bot und den Dispatcher im asynchronen Modus, um auf neue Updates zu reagieren.

        :param drop_pending_updates: Ob ausstehende Updates beim Start des Bots gelöscht werden sollen (Standard: True).
        """
        await self.bot.delete_webhook(drop_pending_updates=drop_pending_updates)
        await self.dp.start_polling(self.bot)

    def get_chat_history(self, chat_id: int, limit: int = 100, reverse: bool = False):
        """
        Synchroner Wrapper für das Abrufen des Nachrichtenverlaufs.
        Dies ermöglicht es, den Nachrichtenverlauf synchron zu abrufen, was die Nutzung vereinfacht.

        :param chat_id: Die ID des Chats, dessen Nachrichtenverlauf abgerufen werden soll.
        :param limit: Die maximale Anzahl der Nachrichten, die abgerufen werden sollen (Standard: 100).
        :param reverse: Gibt den Verlauf in umgekehrter Reihenfolge zurück (Standard: False).
        """
        try:
            return self.loop.run_until_complete(self.get_chat_history_json(chat_id, limit, reverse))
        except Exception as e:
            logging.error(f"Error retrieving chat history: {e}")
            return []

    def send_sync_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None):
        """
        Synchroner Wrapper zum Senden von Nachrichten.
        Erlaubt es Benutzern, Nachrichten zu senden, ohne asynchrone Aufrufe explizit zu handhaben.

        :param chat_id: Die ID des Chats, an den die Nachricht gesendet werden soll.
        :param text: Der Inhalt der Nachricht, die gesendet werden soll.
        :param parse_mode: Die Parse-Mode für die Nachricht (z.B. "Markdown", "HTML").
        :param disable_web_page_preview: Deaktiviert die Web-Vorschau für Links (Standard: None).
        :param disable_notification: Sendet die Nachricht ohne Benachrichtigung (Standard: None).
        """
        self.loop.run_until_complete(self.send_message(chat_id, text, parse_mode, disable_web_page_preview, disable_notification))

    def get_active_chats(self) -> List[Dict[str, str]]:
        """
        Gibt eine Liste aller aktiven Chats zusammen mit den zugehörigen Benutzernamen zurück.

        :return: Eine Liste von Diktaten mit 'chat_id' und 'username'.
        """
        active_chats = []
        for chat_id, messages in self.chat_histories.items():
            if messages:
                last_message = messages[-1]  # Nimm die letzte Nachricht, um den Benutzer zu identifizieren
                active_chats.append({
                    "chat_id": chat_id,
                    "username": last_message.get("from_user", "Unbekannt")
                })
        logging.info(f"Retrieved {len(active_chats)} active chats.")
        return active_chats
