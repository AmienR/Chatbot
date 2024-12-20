import os
import logging
import time
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from functools import wraps
from collections import deque

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

# Set up logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger()

# Decorator for replying only to group messages
def group_only(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.type not in ['group', 'supergroup']:
            return
        return func(update, context, *args, **kwargs)
    return wrapped

# Memory to track messages and responses (as a deque to maintain a "queue")
message_memory = deque(maxlen=10)  # Store only the last 10 messages

# Process messages
@group_only
def handle_message(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    user_message = message.text

    # Track conversation in memory
    message_memory.append({
        "message_id": message.message_id,
        "user_id": user_id,
        "text": user_message,
        "timestamp": time.time(),  # Track the time of the message
    })

    # Log the received message for debugging
    logger.info(f"Received message: {user_message} from user {user_id} in chat {chat_id}")

    # If there are enough messages (e.g., 5 messages in the last 10), analyze them
    if len(message_memory) >= 5:
        # Analyze the last few messages (in this case, the last 5)
        context_string = "\n".join([msg['text'] for msg in message_memory])

        # Generate reply with Grok AI
        try:
            response = openai.ChatCompletion.create(
                model="grok-2-1212",
                messages=[{
                    "role": "system", 
                    "content": "You are a funny AI that enjoys making clever, light-hearted jokes, and always stays friendly."
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
    if parent_message_id in [msg['message_id'] for msg in message_memory]:
        # If the reply references a bot message, respond specifically to that message
        parent_message = next(msg for msg in message_memory if msg['message_id'] == parent_message_id)['text']
        user_message = message.text

        logger.info(f"Replying to message: {parent_message}, user reply: {user_message}")

        try:
            response = openai.ChatCompletion.create(
                model="grok-2-1212",
                messages=[{
                    "role": "system", 
                    "content": "You are a funny AI that loves light-hearted humor and enjoys friendly banter."
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
    # Check if the script is running and logging is working
    logger.info("Bot is starting...")

    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Handlers
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.reply & Filters.text & ~Filters.command, handle_reply))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
