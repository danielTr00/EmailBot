import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from typing import List, Dict, Callable, Optional
import asyncio

# Einrichten des Loggings, um Informationen, Warnungen und Fehler zu protokollieren.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class MessageHistory(BaseModel):
    message_id: int
    from_user: str = Field(default="Bot")
    text: str

class ActiveChat(BaseModel):
    chat_id: int
    username: str


class TelegramBot:
    def __init__(self, token: str, logging_level: int = logging.INFO):
        """
        Initializes the TelegramBot with the provided token and sets up the bot, dispatcher, and router.

        :param token: The token of the Telegram bot provided by the BotFather to connect the bot with the API.
        :param logging_level: The logging level to be set (default: logging.INFO).
        """
        logging.basicConfig(level=logging_level)
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)

        # Here we store the chat histories in memory.
        self.chat_histories: Dict[int, List[MessageHistory]] = {}

        # Register default commands like /start and /stop.
        self.register_default_commands()

        # Register async functions for easier external invocation
        self.loop = asyncio.get_event_loop()

    def register_default_commands(self, start_command: str = "start", stop_command: str = "stop"):
        """
        Registers default commands like /start and /stop.

        :param start_command: The name of the start command (default: "start").
        :param stop_command: The name of the stop command (default: "stop").
        """
        self.add_command(start_command, self.handle_start)
        self.add_command(stop_command, self.handle_stop)

    def add_command(self, command_name: str, command_handler: Callable):
        """
        Adds a new command to the bot.

        :param command_name: The name of the command (without leading /).
        :param command_handler: The function to be executed when the command is entered.
        """
        self.router.message.register(command_handler, Command(commands=[command_name]))

    async def handle_start(self, message: Message, start_message: str = "Willkommen! Der Bot ist jetzt aktiv."):
        """
        Handles the /start command and sends a welcome message back.

        :param message: The received message from the user.
        :param start_message: The message to be sent on start (default: "Willkommen! Der Bot ist jetzt aktiv.").
        """
        logging.info(f"Received /start command from {message.from_user.username}")
        await self.send_message(message.chat.id, start_message)
        self.save_message_to_history(message)

    async def handle_stop(self, message: Message, stop_message: str = "Der Bot wird jetzt deaktiviert. Bis zum nächsten Mal!"):
        """
        Handles the /stop command and sends a goodbye message back.

        :param message: The received message from the user.
        :param stop_message: The message to be sent on stop (default: "Der Bot wird jetzt deaktiviert. Bis zum nächsten Mal!").
        """
        logging.info(f"Received /stop command from {message.from_user.username}")
        await self.send_message(message.chat.id, stop_message)
        self.save_message_to_history(message)

    async def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None):
        """
        Sends a message to a specific chat.

        :param chat_id: The ID of the chat to send the message to.
        :param text: The content of the message to be sent.
        :param parse_mode: The parse mode for the message (e.g., "Markdown", "HTML").
        :param disable_web_page_preview: Disables web preview for links (default: None).
        :param disable_notification: Sends the message without notification (default: None).
        """
        try:
            message = await self.bot.send_message(chat_id, text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview, disable_notification=disable_notification)
            logging.info(f"Message sent to {chat_id}: {text}")
            self.save_message_to_history(message)
        except Exception as e:
            logging.error(f"Failed to send message to {chat_id}: {e}")

    def save_message_to_history(self, message: Message):
        """
        Saves the incoming message to the chat history.

        :param message: The message to be saved.
        """
        chat_id = message.chat.id
        if chat_id not in self.chat_histories:
            self.chat_histories[chat_id] = []

        # Save the message
        self.chat_histories[chat_id].append(MessageHistory(
            message_id=message.message_id,
            from_user=message.from_user.username if message.from_user else "Bot",
            text=message.text
        ))

    async def get_chat_history_json(self, chat_id: int, limit: int = 100, reverse: bool = False) -> List[MessageHistory]:
        """
        Returns the chat history of a specific chat in JSON format.
        The history is held internally in memory and contains both user and bot messages.

        :param chat_id: The ID of the chat whose message history should be retrieved.
        :param limit: The maximum number of messages to retrieve (default: 100).
        :param reverse: Returns the history in reverse order (default: False).
        :return: A list of messages in JSON format.
        """
        if chat_id in self.chat_histories:
            history = self.chat_histories[chat_id][-limit:]  # Only the last 'limit' messages
            if reverse:
                history.reverse()
            logging.info(f"Retrieved {len(history)} messages from chat {chat_id}")
            return history
        else:
            logging.info(f"No history found for chat {chat_id}")
            return []

    async def reply_to_message(self, message: Message, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None):
        """
        Replies to a received message.

        :param message: The received message to reply to.
        :param text: The content of the reply message.
        :param parse_mode: The parse mode for the message (e.g., "Markdown", "HTML").
        :param disable_web_page_preview: Disables web preview for links (default: None).
        :param disable_notification: Sends the reply without notification (default: None).
        """
        try:
            reply_message = await message.answer(text, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview, disable_notification=disable_notification)
            logging.info(f"Replied to message from {message.from_user.username}: {text}")
            self.save_message_to_history(reply_message)
        except Exception as e:
            logging.error(f"Failed to reply to message: {e}")

        # Save the message to history
        self.save_message_to_history(message)

    async def start(self, drop_pending_updates: bool = True):
        """
        Starts the bot and dispatcher in asynchronous mode to respond to new updates.

        :param drop_pending_updates: Whether to drop pending updates when the bot starts (default: True).
        """
        await self.bot.delete_webhook(drop_pending_updates=drop_pending_updates)
        await self.dp.start_polling(self.bot)

    def get_chat_history(self, chat_id: int, limit: int = 100, reverse: bool = False) -> List[MessageHistory]:
        """
        Synchronous wrapper for retrieving chat history.
        This allows the chat history to be retrieved synchronously, simplifying usage.

        :param chat_id: The ID of the chat whose message history should be retrieved.
        :param limit: The maximum number of messages to retrieve (default: 100).
        :param reverse: Returns the history in reverse order (default: False).
        :return: A list of messages in JSON format.
        """
        try:
            return self.loop.run_until_complete(self.get_chat_history_json(chat_id, limit, reverse))
        except Exception as e:
            logging.error(f"Error retrieving chat history: {e}")
            return []

    def send_sync_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None, disable_notification: Optional[bool] = None):
        """
        Synchronous wrapper for sending messages.
        Allows users to send messages without explicitly handling asynchronous calls.

        :param chat_id: The ID of the chat to send the message to.
        :param text: The content of the message to be sent.
        :param parse_mode: The parse mode for the message (e.g., "Markdown", "HTML").
        :param disable_web_page_preview: Disables web preview for links (default: None).
        :param disable_notification: Sends the message without notification (default: None).
        """
        self.loop.run_until_complete(self.send_message(chat_id, text, parse_mode, disable_web_page_preview, disable_notification))

    def get_active_chats(self) -> List[ActiveChat]:
        """
        Returns a list of all active chats along with the associated usernames.

        :return: A list of dictionaries with 'chat_id' and 'username'.
        """
        active_chats = []
        for chat_id, messages in self.chat_histories.items():
            if messages:
                last_message = messages[-1]  # Take the last message to identify the user
                active_chats.append(ActiveChat(
                    chat_id=chat_id,
                    username=last_message.from_user
                ))
        logging.info(f"Retrieved {len(active_chats)} active chats.")
        return active_chats
