# instagram_service.py
import replicate
from anthropic import Anthropic
import logging
from PIL import Image, ImageDraw, ImageFont
from config import Settings
import requests
from io import BytesIO
import time
import os
# from instabot import Bot
from characters_and_prompts import instagram_system_prompt

logger = logging.getLogger(__name__)

class InstagramService:
    def __init__(self):
        # Initialize clients
        self.anthropic = Anthropic(api_key=Settings.ANTHROPIC_API_KEY)
        self.replicate_client = replicate.Client(api_token=Settings.REPLICATE_API_TOKEN)
        self.instagram_bot = Bot()
        
        # Image settings
        self.font_path = "arial.ttf"  # Make sure this font exists in your system
        self.font_size = 60
        self.image_size = (1080, 1080)  # Instagram square format
        
        # Login to Instagram
        self._instagram_login()

    def _instagram_login(self):
        """Login to Instagram."""
        try:
            self.instagram_bot.login(
                username=Settings.INSTAGRAM_USERNAME,
                password=Settings.INSTAGRAM_PASSWORD
            )
            logger.info("Successfully logged in to Instagram")
        except Exception as e:
            logger.error(f"Instagram login failed: {e}")

    async def generate_and_post_motivation(self, theme=None):
        """Main method to generate and post motivational content."""
        try:
            # Generate content
            content = await self._generate_motivation_content(theme)
            if not content:
                logger.error("Failed to generate motivation content")
                return False

            # Process image with text overlay
            final_image_path = self._process_image(
                content['image_path'], 
                content['text']
            )
            if not final_image_path:
                logger.error("Failed to process image")
                return False

            # Post to Instagram
            success = await self._post_to_instagram(
                final_image_path, 
                content['text']
            )

            # Cleanup temporary files
            self._cleanup_files([content['image_path'], final_image_path])
            
            return success

        except Exception as e:
            logger.error(f"Error in generate_and_post_motivation: {e}")
            return False

    async def _generate_motivation_content(self, theme=None):
        """Generate motivational text and image."""
        try:
            # Generate text
            text = await self._generate_text(theme)
            if not text:
                return None

            # Generate image
            image_path = await self._generate_image(text)
            if not image_path:
                return None

            return {
                'text': text,
                'image_path': image_path
            }

        except Exception as e:
            logger.error(f"Error generating motivation content: {e}")
            return None

    async def _generate_text(self, theme=None):
        """Generate motivational text using Claude."""
        try:
            theme_context = f" about {theme}" if theme else ""
            message = self.anthropic.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=300,
                temperature=0.7,
                system=instagram_system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"Create a short, powerful motivational quote{theme_context} for Instagram. "
                              "Make it original, memorable, and under 100 characters."
                }]
            )
            
            for content in message.content:
                if content.type == 'text':
                    return content.text.strip()
            return None

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return None

    async def _generate_image(self, text):
        """Generate image using Replicate's SDXL model."""
        try:
            output = self.replicate_client.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": f"Motivational image representing: {text}. "
                             "Professional photography, inspirational, Instagram-worthy, "
                             "high quality, modern, clean aesthetic",
                    "negative_prompt": "text, words, letters, logos, watermarks, people, faces, hands",
                    "width": self.image_size[0],
                    "height": self.image_size[1],
                }
            )

            if output and isinstance(output, list) and output[0]:
                # Download the image
                response = requests.get(output[0])
                if response.status_code == 200:
                    # Save the image
                    image_path = f"motivation_{int(time.time())}.png"
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    return image_path

            return None

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None

    def _process_image(self, image_path, text):
        """Add text overlay to image."""
        try:
            with Image.open(image_path) as img:
                # Ensure image is RGB
                img = img.convert('RGB')
                
                # Create draw object
                draw = ImageDraw.Draw(img)
                font = ImageFont.truetype(self.font_path, self.font_size)

                # Calculate text position (centered)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                x = (img.width - text_width) / 2
                y = (img.height - text_height) / 2

                # Add text shadow
                shadow_offset = 3
                draw.text(
                    (x + shadow_offset, y + shadow_offset),
                    text,
                    font=font,
                    fill='black'
                )

                # Add main text
                draw.text(
                    (x, y),
                    text,
                    font=font,
                    fill='white'
                )

                # Save processed image
                output_path = f"processed_{os.path.basename(image_path)}"
                img.save(output_path, quality=95)
                return output_path

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None

    async def _post_to_instagram(self, image_path, caption):
        """Post content to Instagram."""
        try:
            if self.instagram_bot.upload_photo(image_path, caption=caption):
                logger.info("Successfully posted to Instagram")
                return True
            return False
        except Exception as e:
            logger.error(f"Error posting to Instagram: {e}")
            return False

    def _cleanup_files(self, file_paths):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error cleaning up file {file_path}: {e}")