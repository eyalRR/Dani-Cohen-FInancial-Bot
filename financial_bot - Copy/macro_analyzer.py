# macro_analyzer.py
from openai import OpenAI
from anthropic import Anthropic
from config import Settings
import logging

logger = logging.getLogger(__name__)

class MacroAnalyzer:
    def __init__(self):
        self.perplexity = OpenAI(
            api_key=Settings.PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )
        self.anthropic = Anthropic(api_key=Settings.ANTHROPIC_API_KEY)

    async def get_macro_analysis(self, system_prompt, user_prompt):
        """Get macro economic analysis using Perplexity."""
        try:
            response = self.perplexity.chat.completions.create(
                model="llama-3.1-sonar-small-128k-online",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            logger.info("Successfully got macro analysis from Perplexity")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in macro analysis: {e}")
            return None

    def fix_hebrew_text(self, text: str, character_description: str) -> str:
        """Fix Hebrew text formatting using Claude."""
        try:
            message = self.anthropic.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                temperature=0,
                system=character_description,
                messages=[
                    {
                        "role": "user",
                        "content": self._create_hebrew_prompt(text)
                    }
                ]
            )
            
            logger.info("Successfully formatted Hebrew text")
            return message.content[0].text.strip()
        except Exception as e:
            logger.error(f"Error fixing Hebrew text: {e}")
            return None

    @staticmethod
    def _create_hebrew_prompt(text: str) -> str:
        """Create a prompt for fixing Hebrew text formatting."""
        return f"""
        מצורף פוסט שלך עם שגיאות בעברית, ערוך אותו שיהיה מוכן לחלוטין ללא כותרות מוזרות באופן אותנטי ומקצועי,
        .אין צורך להציג את עצמך מחדש, אך משפט פתיחה השואל לשלומם של האנשים הטובים בקבוצה שלך בקשר לנושא יהיה נחמד,
        נסה לשלב משל או מוסר השכל קצר בהקשר החודשי בסוף הפוסט.
        :

        {text}
        
        FORMAT RULES (MANDATORY):
        - Add one emoji in a strategic point
        - Start with one personal opening line
        - Present exactly 5 key points
        - NO numbers, bullet points, hashtags or special characters 
        - Separate points with exactly one blank line
        - Each point: up to 4 lines maximum
        - Write naturally in first person
        - NO formatting symbols anywhere
        - NO self-introduction
        """