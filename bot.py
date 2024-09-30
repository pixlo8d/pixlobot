import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import google.generativeai as genai
import re
from telegram.constants import ParseMode
import logging

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up your Telegram Bot Token and Gemini API Key
TELEGRAM_BOT_TOKEN = "8146995903:AAHzYgZzxYBaYU4InukNegK_XEr0zDHDGyM"
GEMINI_API_KEY = "AIzaSyB6qo3acV7fGEacs3cLlwlNg3uu8vgsr-I"

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Store conversation history
conversation_history = {}

# Helper function to get user info
def get_user_info(user: User) -> str:
    info = []
    if user.first_name:
        info.append(f"First Name: {user.first_name}")
    if user.last_name:
        info.append(f"Last Name: {user.last_name}")
    if user.username:
        info.append(f"Username: @{user.username}")
    if user.language_code:
        info.append(f"Language Code: {user.language_code}")
    return "\n".join(info)

# Command handler for /start
async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    conversation_history[user_id] = []
    
    welcome_message = (
        f"Hello {user.first_name}! I'm a chatbot powered by Gemini. "
        f"How can I assist you today?"
    )
    
    keyboard = [
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Command handler for /help
async def help_command(update: Update, context):
    user = update.effective_user
    help_text = (
        f"Hello {user.first_name}! Here are the available commands:\n"
        "/start - Start a new conversation\n"
        "/help - Show this help message\n"
        "/clear - Clear conversation history\n"
        "/info - Show your user information\n"
        "You can also just send me a message and I'll do my best to respond!"
    )
    if update.message:
        await update.message.reply_text(help_text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(help_text)

# Command handler for /clear
async def clear_history(update: Update, context):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("Conversation history cleared!")

# Command handler for /info
async def info_command(update: Update, context):
    user = update.effective_user
    user_info = get_user_info(user)
    await update.message.reply_text(f"Your information:\n{user_info}")

# Message handler for chat interactions
async def chat(update: Update, context):
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text
    
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    conversation_history[user_id].append(f"Human ({user.first_name}): {user_message}")
    context_string = "\n".join(conversation_history[user_id][-5:])  # Last 5 messages for context
    
    try:
        # Generate a response using Gemini
        response = model.generate_content([context_string, f"AI: "])
        ai_response = response.text
        
        conversation_history[user_id].append(f"AI: {ai_response}")
        
        # Process the response to apply text effects
        def format_text(text):
            # Bold
            text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
            # Italic
            text = re.sub(r'_(.*?)_', r'_\1_', text)
            # Underline
            text = re.sub(r'__(.*?)__', r'__\1__', text)
            # Strikethrough
            text = re.sub(r'~(.*?)~', r'~\1~', text)
            # Inline code
            text = re.sub(r'`(.*?)`', r'`\1`', text)
            return text
        
        processed_text = format_text(ai_response)
        
        # Escape special characters for Markdown V2, excluding already formatted text
        def escape_markdown(text):
            escape_chars = r'_*[]()~`>#+-=|{}.!'
            return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
        
        # Split the text into formatted and non-formatted parts
        parts = re.split(r'(\*.*?\*|_.*?_|__.*?__|~.*?~|`.*?`)', processed_text)
        
        # Escape special characters only in non-formatted parts
        escaped_parts = [escape_markdown(part) if i % 2 == 0 else part for i, part in enumerate(parts)]
        
        final_text = ''.join(escaped_parts)
        
        await update.message.reply_text(final_text, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        logger.error(f"Error in chat handler: {error_message}")
        await update.message.reply_text("I'm sorry, but I encountered an error. Please try again later.")

# Callback query handler
async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        await help_command(update, context)

# Error handler
async def error_handler(update: Update, context):
    logger.error(f"Exception while handling an update: {context.error}")
    error_message = "An unexpected error occurred. Please try again later."
    if update.message:
        await update.message.reply_text(error_message)
    elif update.callback_query:
        await update.callback_query.message.reply_text(error_message)

# Set up the application and add handlers
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    application.add_handler(CallbackQueryHandler(button))
    
    # Add the error handler
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == "__main__":
    main()