from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackContext,
)
import os
from dotenv import load_dotenv
import openai
import requests
from bs4 import BeautifulSoup

# Load API keys from .env file
load_dotenv()
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Conversation states
INDUSTRY, OBJECTIVE, WEBSITE, SOCIAL_MEDIA, PPC, AUDIENCE, LOCATION = range(7)

# Send welcome message directly when the bot starts
async def send_welcome_message(application):
    updates = await application.bot.get_updates()  # Await the updates coroutine
    for update in updates:
        await application.bot.send_message(
            chat_id=update.message.chat.id,
            text=(
                "Welcome to the Business Assistant Bot! I can help you with finding trendy keywords based on the answers you give me. "
                "Be ready, I will ask you questions below one by one.\n\n"
                "Here are the commands you can use:\n"
                "- To start, use: /start\n"
                "- To know the trends in PPC and more: /trends\n"
                "- To ask business-related questions: /faq\n\n"
                "Let’s get started!"
            )
        )

# Start command
async def start(update: Update, context) -> int:
    await update.message.reply_text("What industry is your business in?")
    return INDUSTRY

# Collect industry input
async def industry(update: Update, context) -> int:
    context.user_data['industry'] = update.message.text
    await update.message.reply_text("What is your business objective (e.g., lead generation, sales)?")
    return OBJECTIVE

# Collect objective input
async def objective(update: Update, context) -> int:
    context.user_data['objective'] = update.message.text
    await update.message.reply_text("Do you have a website? If yes, please share the URL.")
    return WEBSITE

# Collect website input
async def website(update: Update, context) -> int:
    context.user_data['website'] = update.message.text
    await update.message.reply_text("Do you have any social media platforms? If yes, please share the URL(s).")
    return SOCIAL_MEDIA

# Collect social media input
async def social_media(update: Update, context) -> int:
    context.user_data['social_media'] = update.message.text
    await update.message.reply_text("Do you use PPC campaigns? (yes/no)")
    return PPC

# Collect PPC input
async def ppc(update: Update, context) -> int:
    context.user_data['ppc'] = update.message.text
    await update.message.reply_text("Who are you trying to reach? (e.g., young adults, professionals, etc.)")
    return AUDIENCE

# Collect audience input
async def audience(update: Update, context) -> int:
    context.user_data['audience'] = update.message.text
    await update.message.reply_text("What location(s) would you like to target?")
    return LOCATION

# Collect location input and generate keywords
async def location(update: Update, context) -> int:
    context.user_data['location'] = update.message.text

    # Collect all user inputs
    industry = context.user_data['industry']
    objective = context.user_data['objective']
    website = context.user_data.get('website', "No website provided")
    social_media = context.user_data.get('social_media', "No social media provided")
    ppc = context.user_data.get('ppc', "No PPC campaigns")
    audience = context.user_data['audience']
    location = context.user_data['location']

    # Generate keywords using GPT
    prompt = (
        f"Generate a list of trending and relevant keywords for a {industry} business with the following details:\n"
        f"- Objective: {objective}\n"
        f"- Website: {website}\n"
        f"- Social Media: {social_media}\n"
        f"- PPC Campaigns: {ppc}\n"
        f"- Target Audience: {audience}\n"
        f"- Target Location(s): {location}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in digital marketing."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        keywords = response.choices[0].message['content'].strip()
        await update.message.reply_text(f"Here are the trending keywords for your business:\n{keywords}")
    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't generate keywords. Please try again later.")
        print(f"Error: {e}")

    return ConversationHandler.END

# Fetch PPC data
async def fetch_ppc_data():
    url = "https://databox.com/ppc-industry-benchmarks"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Example: Simplify this based on actual HTML structure
    data = soup.find_all("table")
    return "Parsed PPC data (example)"  # Replace with actual parsed data

# Send PPC trends
async def trends(update: Update, context: CallbackContext):
    try:
        data = await fetch_ppc_data()
        await update.message.reply_text(f"Here are the latest PPC trends:\n{data}")
    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't fetch the trends at the moment.")
        print(f"Error: {e}")

# Handle FAQ command
async def faq(update: Update, context: CallbackContext):
    user_question = update.message.text.replace("/faq", "").strip()
    if not user_question:
        await update.message.reply_text("Please ask a question after the /faq command, like this:\n/faq How do I improve my ad performance?")
        return

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a digital marketing assistant."},
                {"role": "user", "content": user_question}
            ],
            max_tokens=150,
            temperature=0.7
        )
        ai_response = response.choices[0].message['content'].strip()
        await update.message.reply_text(ai_response)
    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't process your question. Please try again later.")
        print(f"Error: {e}")

# Cancel conversation
async def cancel(update: Update, context) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# Main function
def main():
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_API_KEY).build()

    # Send welcome message as the bot starts
    application.bot.send_message(
        chat_id="@AI-Keywords-Bot",  # Set your default chat ID here
        text="Welcome to the Business Assistant Bot! Let's get started!"
    )

    # Conversation handler for generating keywords
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            INDUSTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, industry)],
            OBJECTIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, objective)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, website)],
            SOCIAL_MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, social_media)],
            PPC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ppc)],
            AUDIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, audience)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("trends", trends))    # Add trends handler
    application.add_handler(CommandHandler("faq", faq))          # Add FAQ handler
    application.add_handler(conv_handler)

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
