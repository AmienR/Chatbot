import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from functools import wraps

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

# Memory to track messages and responses
message_memory = {}

# Process messages
@group_only
def handle_message(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    user_message = message.text

    # Track conversation in memory
    message_memory[message.message_id] = {
        "user_id": user_id,
        "text": user_message,
    }

    # Print the received message for debugging
    print(f"Received message: {user_message} from user {user_id} in chat {chat_id}")

    # Prepare context from previous messages (e.g., last 10 messages)
    previous_messages = [f"{msg['text']}" for mid, msg in message_memory.items()][-10:]
    context_string = "\n".join(previous_messages)

    # Generate reply with Grok AI
    try:
        response = openai.ChatCompletion.create(
            model="grok-2-1212",
            messages=[{
                "role": "system", 
                "content": "You are a funny and mean AI that speaks Persian."
            }, {
                "role": "user", 
                "content": context_string
            }]
        )
        reply = response['choices'][0]['message']['content']
    except Exception as e:
        reply = "مشکلی برای ربات پیش اومده ولی بازم از تو بهترم"
        print(f"Error: {e}")

    # Print the reply that the bot is sending for debugging
    print(f"Bot sending message: {reply}")

    # Send the reply
    context.bot.send_message(chat_id=chat_id, text=reply)

@group_only
def handle_reply(update: Update, context: CallbackContext):
    message = update.message
    reply_to_message = message.reply_to_message

    if not reply_to_message:
        return

    parent_message_id = reply_to_message.message_id
    if parent_message_id in message_memory:
        # If the reply references a bot message, respond
        parent_message = message_memory[parent_message_id]['text']
        user_message = message.text

        print(f"Replying to message: {parent_message}, user reply: {user_message}")  # Debugging output

        try:
            response = openai.ChatCompletion.create(
                model="grok-2-1212",
                messages=[{
                    "role": "system", 
                    "content": "You are a funny and slightly mean AI that speaks Persian."
                }, {
                    "role": "user", 
                    "content": f"Message: {parent_message}\nReply: {user_message}"
                }]
            )
            reply = response['choices'][0]['message']['content']
        except Exception as e:
            reply = "مشکلی برای ربات پیش اومده ولی بازم از تو بهترم"
            print(f"Error: {e}")

        # Print the reply that the bot is sending for debugging
        print(f"Bot sending reply: {reply}")

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
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
