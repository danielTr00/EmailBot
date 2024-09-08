import logging
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from typing import List, Dict, Callable, Optional
import asyncio
from pydantic import BaseModel, Field
from aiohttp import ClientSession
import aiofiles

# Pydantic Models to manage message history and active chats
class MessageHistory(BaseModel):
    message_id: int
    from_user: str = Field(default="Bot")
    text: str

class ActiveChat(BaseModel):
    chat_id: int
    username: str

# TelegramBot class to manage all bot operations
class TelegramBot:
    def __init__(self, token: str, dispatcher: Optional[Dispatcher] = None, router: Optional[Router] = None):
        """
        Initializes the TelegramBot with the provided token and sets up the bot, dispatcher, and router.

        :param token: The token to connect the bot with the Telegram API. Must be exactly 46 characters long.
        :param dispatcher: Optional custom dispatcher to handle events.
        :param router: Optional custom router to register message and command handlers.
        """
        if len(token) != 46:
            raise ValueError("Invalid Telegram token. It must be exactly 46 characters long.")
        
        self.bot = Bot(token=token)
        self.dp = dispatcher if dispatcher else Dispatcher()
        self.router = router if router else Router()
        self.dp.include_router(self.router)

        # Dictionary to store chat histories
        self.chat_histories: Dict[int, List[MessageHistory]] = {}
        
        # Register default commands (/start and /stop)
        self.register_default_commands()

        # Event loop for asynchronous operations
        self.loop = asyncio.get_event_loop()

        # Directory for saving files received from users
        self.file_directory = "files"
        if not os.path.exists(self.file_directory):
            os.makedirs(self.file_directory)

    def register_default_commands(self):
        """
        Registers default commands like /start and /stop.
        """
        self.add_command("start", self.handle_start)
        self.add_command("stop", self.handle_stop)

    def add_command(self, command_name: str, command_handler: Callable, description: str = None):
        """
        Adds a new command to the bot and registers it.

        :param command_name: Name of the command (e.g., 'start', 'help').
        :param command_handler: The function that handles the command.
        :param description: Optional description for the command.
        """
        if description:
            logging.info(f"Registering command /{command_name}: {description}")
        else:
            logging.info(f"Registering command /{command_name}")
        
        self.router.message.register(command_handler, Command(commands=[command_name]))

    async def handle_start(self, message: Message):
        """
        Handles the /start command and sends a welcome message back.
        """
        await self.send_message(message.chat.id, "Willkommen! Der Bot ist jetzt aktiv.")
        self.save_message_to_history(message)

    async def handle_stop(self, message: Message):
        """
        Handles the /stop command and sends a goodbye message back.
        """
        await self.send_message(message.chat.id, "Der Bot wird jetzt deaktiviert. Bis zum nächsten Mal!")
        self.save_message_to_history(message)

    async def send_message(self, chat_id: int, text: str):
        """
        Sends a message to a specific chat.

        :param chat_id: ID of the chat to send the message to.
        :param text: The text content of the message.
        """
        try:
            message = await self.bot.send_message(chat_id, text)
            logging.info(f"Message sent to {chat_id}: {text}")
            self.save_message_to_history(message)
        except ClientSession as e:
            logging.error(f"Connection error when sending message to {chat_id}: {e}")
        except Exception as e:
            logging.error(f"Failed to send message to {chat_id}: {e}")

    async def send_file(self, chat_id: int, file_path: str, caption: Optional[str] = None):
        """
        Sends a file to a specific chat.

        :param chat_id: ID of the chat to send the file to.
        :param file_path: Path to the file to send.
        :param caption: Optional caption for the file.
        """
        try:
            file_to_send = FSInputFile(file_path)
            file_extension = os.path.splitext(file_path)[1].lower()

            # Send the file based on its type
            if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
                await self.bot.send_photo(chat_id, photo=file_to_send, caption=caption)
                logging.info(f"Photo sent to {chat_id}: {file_path}")
            elif file_extension in [".mp4", ".mov", ".avi", ".mkv"]:
                await self.bot.send_video(chat_id, video=file_to_send, caption=caption)
                logging.info(f"Video sent to {chat_id}: {file_path}")
            elif file_extension in [".mp3", ".wav", ".aac"]:
                await self.bot.send_audio(chat_id, audio=file_to_send, caption=caption)
                logging.info(f"Audio sent to {chat_id}: {file_path}")
            else:
                await self.bot.send_document(chat_id, document=file_to_send, caption=caption)
                logging.info(f"Document sent to {chat_id}: {file_path}")

        except Exception as e:
            logging.error(f"Failed to send file to {chat_id}: {e}")

    async def receive_and_save_file(self, message: Message, file_directory: Optional[str] = None, file_name: Optional[str] = None) -> str:
        """
        Receives any file from a message and saves it in the specified directory.

        :param message: The Telegram message containing the file (photo or document).
        :param file_directory: The directory where the file should be saved. Defaults to 'self.file_directory'.
        :param file_name: The desired name of the file (including extension). If not provided, a default name will be used.
        :return: The full path to the saved file.
        """
        file_id = None
        default_file_name = None

        # Check if it's a photo or a document and get the relevant file info
        if message.photo:
            file_id = message.photo[-1].file_id
            default_file_name = f"{file_id}.jpg"
        elif message.document:
            file_id = message.document.file_id
            default_file_name = message.document.file_name

        if file_id is None:
            logging.info("No file in the message.")
            return None

        # Set the directory and file name if not provided
        file_directory = file_directory or self.file_directory
        file_name = file_name or default_file_name

        # Construct the full path to save the file
        file_path = os.path.join(file_directory, file_name)

        # Ensure the directory exists
        if not os.path.exists(file_directory):
            os.makedirs(file_directory)

        try:
            # Get file info and download
            file_info = await self.bot.get_file(file_id)
            async with aiofiles.open(file_path, 'wb') as f:
                file_data = await self.bot.download_file(file_info.file_path)
                await f.write(file_data.read())
            logging.info(f"File saved to {file_path}")
            return file_path

        except Exception as e:
            logging.error(f"Failed to receive and save file: {e}")
            return None

    def save_message_to_history(self, message: Message):
        """
        Saves the incoming message to the chat history.
        """
        chat_id = message.chat.id
        if chat_id not in self.chat_histories:
            self.chat_histories[chat_id] = []

        self.chat_histories[chat_id].append(MessageHistory(
            message_id=message.message_id,
            from_user=message.from_user.username if message.from_user else "Bot",
            text=message.text or "[File]"
        ))

    async def start(self):
        """
        Starts the bot and dispatcher in asynchronous mode to respond to new updates.
        """
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)

    async def stop(self):
        """
        Stops the bot and closes all open connections gracefully.
        """
        print("Stopping the bot...")
        self.dp.shutdown()
        await self.bot.session.close()
        print("Bot stopped successfully.")

    async def __aenter__(self):
        """
        Asynchronous context manager enter method.
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Asynchronous context manager exit method.
        Ensures the bot stops and cleans up resources when used in a 'with' statement.
        """
        await self.stop()

    def get_chat_history(self, chat_id: int, limit: int = 100) -> List[MessageHistory]:
        """
        Returns the chat history for a given chat.

        :param chat_id: The ID of the chat to retrieve history from.
        :param limit: The maximum number of messages to retrieve.
        :return: A list of MessageHistory objects.
        """
        if chat_id not in self.chat_histories:
            return []
        
        return self.chat_histories[chat_id][-limit:]
    
    def get_active_chats(self) -> List[ActiveChat]:
        """
        Returns a list of active chats along with their usernames.
        """
        active_chats = []
        for chat_id, messages in self.chat_histories.items():
            if messages:
                last_message = messages[-1]
                active_chats.append(ActiveChat(chat_id=chat_id, username=last_message.from_user))
        return active_chats