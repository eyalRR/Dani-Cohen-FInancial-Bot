# chart_analyzer.py
from anthropic import Anthropic
from config import Settings
import base64
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ChartAnalyzer:
    def __init__(self):
        self.anthropic = Anthropic(api_key=Settings.ANTHROPIC_API_KEY)

    def analyze_chart(self, image_path, character_description, prompt):
        """Analyze chart using Claude Vision."""
        try:
            base64_image = self._encode_image(image_path)
            if not base64_image:
                return None
                
            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0,
                system=character_description,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            return self._format_response(message)
        except Exception as e:
            logger.error(f"Error in chart analysis: {e}")
            return None

    def _encode_image(self, image_path):
        """Encode image to base64."""
        try:
            with Image.open(image_path) as img:
                # Convert to JPEG if it's not already
                if img.format != 'JPEG':
                    rgb_im = img.convert('RGB')
                    jpeg_buffer = io.BytesIO()
                    rgb_im.save(jpeg_buffer, format="JPEG")
                    img_str = base64.b64encode(jpeg_buffer.getvalue()).decode('utf-8')
                else:
                    with open(image_path, "rb") as image_file:
                        img_str = base64.b64encode(image_file.read()).decode('utf-8')
            return img_str
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            return None

    def _format_response(self, result):
        """Format Claude's response."""
        try:
            if result and result.content:
                for content in result.content:
                    if content.type == 'text':
                        return content.text
            return None
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return None