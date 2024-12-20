import os
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure `openai` is imported only if available
try:
    import openai
except ImportError:
    raise ImportError("The 'openai' module is not installed. Install it using 'pip install openai' and try again.")

# Load environment variables
API_KEY = os.getenv("XAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not API_KEY or not TELEGRAM_TOKEN:
    raise EnvironmentError("Required environment variables 'XAI_API_KEY' or 'TELEGRAM_TOKEN' are missing.")

# Initialize OpenAI client
openai.api_key = API_KEY
openai.api_base = "https://api.x.ai/v1"

# Decorator for replying only to group messages
def group_only(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.type not in ['group', 'supergroup']:
            return
        return func(update, context, *args, **kwargs)
    return wrapped

# Memory to track messages the bot has responded to
responded_messages = set()

# Process messages
@group_only
def handle_message(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    user_message = message.text

    # Log the received message for debugging
    logger.info(f"Received message: {user_message} from user {user_id} in chat {chat_id}")

    # Check if the message has already been responded to
    if message.message_id in responded_messages:
        logger.info(f"Already responded to message {message.message_id}, skipping.")
        return

    # Track the message ID to prevent repeated responses
    responded_messages.add(message.message_id)

    # Prepare context from previous messages (e.g., last 5 messages)
    previous_messages = [f"{msg['text']}" for msg in responded_messages][-5:]
    context_string = "\n".join(previous_messages)

    # Generate reply with Grok AI
    try:
        response = openai.ChatCompletion.create(
            model="grok-2-1212",
            messages=[{
                "role": "system", 
                "content": "You are an AI with the personality of a Persian Twitter (X) user: witty, sarcastic, and a bit edgy. "
                           "You have a sense of humor and like to joke around, but you're not too fond of emojis. "
                           "You might throw in a little sarcasm."
                           "You respond with a mix of dry humor and sharp wit, just like a typical Persian Twitter user."
            }, {
                "role": "user", 
                "content": context_string
            }]
        )
        reply = response['choices'][0]['message']['content']
    except Exception as e:
        reply = "مشکلی برای ربات پیش اومده ولی بازم از تو بهترم"
        logger.error(f"Error: {e}")

    # Log the reply that the bot is sending
    logger.info(f"Bot sending message: {reply}")

    # Send the reply
    context.bot.send_message(chat_id=chat_id, text=reply)

@group_only
def handle_reply(update: Update, context: CallbackContext):
    message = update.message
    reply_to_message = message.reply_to_message

    if not reply_to_message:
        return

    parent_message_id = reply_to_message.message_id

    # Check if the message has already been responded to
    if parent_message_id in responded_messages:
        logger.info(f"Already responded to parent message {parent_message_id}, skipping.")
        return

    # Track the message ID to prevent repeated responses
    responded_messages.add(parent_message_id)

    parent_message = reply_to_message.text
    user_message = message.text

    # Log the reply message for debugging
    logger.info(f"Replying to message: {parent_message}, user reply: {user_message}")

    try:
        response = openai.ChatCompletion.create(
            model="grok-2-1212",
            messages=[{
                "role": "system", 
                "content": "You are an AI with the personality of a Persian Twitter (X) user: witty, sarcastic, and a bit edgy. "
                           "You have a sense of humor and like to joke around, but you're not too fond of emojis. "
                           "You might throw in a little sarcasm."
                           "You respond with a mix of dry humor and sharp wit, just like a typical Persian Twitter user."
            }, {
                "role": "user", 
                "content": f"Message: {parent_message}\nReply: {user_message}"
            }]
        )
        reply = response['choices'][0]['message']['content']
    except Exception as e:
        reply = "مشکلی برای ربات پیش اومده ولی بازم از تو بهترم"
        logger.error(f"Error: {e}")

    # Log the reply that the bot is sending
    logger.info(f"Bot sending reply: {reply}")

    # Send the reply
    context.bot.send_message(chat_id=message.chat_id, text=reply)

# Main function to set up the bot
def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Handlers
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.reply & Filters.text & ~Filters.command, handle_reply))

    # Start the bot
    logger.info("Bot is starting...")
    updater.start_polling(timeout=10, clean=True)
    updater.idle()

if __name__ == "__main__":
    main()
