# telegram_bot.py
import logging
from telegram import Bot
from telegram.error import TelegramError
from config import Settings

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=Settings.TELEGRAM_BOT_TOKEN)
    
    async def send_image(self, image_path):
        """Send an image to the private channel."""
        try:
            logger.info(f"Attempting to send image: {image_path}")
            with open(image_path, 'rb') as image_file:
                await self.bot.send_photo(
                    chat_id=Settings.CHANNEL_ID_PRIVATE, 
                    photo=image_file
                )
            logger.info("Image sent successfully")
        except Exception as e:
            logger.error(f"Error sending image: {e}")
    
    async def send_text(self, text):
        """Send a text message to the private channel."""
        try:
            logger.info("Attempting to send text message")
            await self.bot.send_message(
                chat_id=Settings.CHANNEL_ID_PRIVATE, 
                text=text
            )
            logger.info("Message sent successfully")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def send_public_message(self, text):
        """Send a text message to the public channel."""
        try:
            logger.info("Attempting to send public message")
            await self.bot.send_message(
                chat_id=Settings.CHANNEL_ID_PUBLIC, 
                text=text
            )
            logger.info("Public message sent successfully")
        except Exception as e:
            logger.error(f"Error sending public message: {e}")

    async def send_public_image(self, image_path):
        """Send an image to the public channel."""
        try:
            logger.info(f"Attempting to send public image: {image_path}")
            with open(image_path, 'rb') as image_file:
                await self.bot.send_photo(
                    chat_id=Settings.CHANNEL_ID_PUBLIC, 
                    photo=image_file
                )
            logger.info("Public image sent successfully")
        except Exception as e:
            logger.error(f"Error sending public image: {e}")