import os
import logging
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from webscout.AIutel import sanitize_stream

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://tender-taxes-sniff.loca.lt/v1')
AI_API_KEY = os.getenv('AI_API_KEY', 'token-abc123')
AI_MODEL = os.getenv('AI_MODEL', 'HelpingAI/Dhanishtha-2.0-preview')

class AIBot:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }

    async def get_ai_response(self, user_message: str) -> str:
        """Get response from AI API"""
        data = {
            "model": AI_MODEL,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "stream": True
        }

        try:
            response = requests.post(
                f"{AI_BASE_URL}/chat/completions", 
                headers=self.headers, 
                json=data, 
                verify=False, 
                stream=True,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return "Sorry, I'm having trouble connecting to the AI service."

            full_response = ""

            def extract_content(chunk):
                try:
                    return chunk["choices"][0]["delta"].get("content")
                except Exception:
                    return None

            for content in sanitize_stream(
                response.iter_lines(),
                intro_value="data:",
                to_json=True,
                skip_markers=["[DONE]", ""],
                content_extractor=extract_content,
                yield_raw_on_error=False,
            ):
                if content:
                    full_response += content

            return full_response.strip() if full_response else "I couldn't generate a response."

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return "Sorry, I'm having trouble connecting to the AI service."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "Sorry, something went wrong while processing your request."

# Initialize AI bot
ai_bot = AIBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I\'m an AI assistant bot. Send me any message and I\'ll respond using AI!\n\n'
        'Commands:\n'
        '/start - Show this message\n'
        '/help - Show help information'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        'I\'m an AI assistant bot powered by advanced language models.\n\n'
        'Just send me any message and I\'ll respond intelligently!\n\n'
        'You can ask me questions, have conversations, or request help with various topics.'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    user_message = update.message.text
    user_name = update.effective_user.first_name

    logger.info(f"Received message from {user_name}: {user_message}")

    # Send typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # Get AI response
    ai_response = await ai_bot.get_ai_response(user_message)

    # Send response
    await update.message.reply_text(ai_response)

    logger.info(f"Sent response to {user_name}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        return

    logger.info("Starting AI Telegram Bot...")

    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
