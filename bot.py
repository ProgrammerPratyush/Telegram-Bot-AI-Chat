import os
import sqlite3
import pdfplumber
from dotenv import load_dotenv
import openai
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackContext,
)
import random

# Load API keys from .env file
load_dotenv()
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Conversation states
INDUSTRY, OBJECTIVE, WEBSITE, SOCIAL_MEDIA, PPC, AUDIENCE, LOCATION, UPLOAD_DOC = range(8)

# Function to extract text from uploaded document
def extract_text_from_pdf(pdf_file_path):
    extracted_text = ""
    with pdfplumber.open(pdf_file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
    return extracted_text

# Start command
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("What industry is your business in?")
    return INDUSTRY

# Collect industry input
async def industry(update: Update, context: CallbackContext) -> int:
    context.user_data['industry'] = update.message.text
    await update.message.reply_text("What is your business objective (e.g., lead generation, sales)?")
    return OBJECTIVE

# Collect objective input
async def objective(update: Update, context: CallbackContext) -> int:
    context.user_data['objective'] = update.message.text
    await update.message.reply_text("Do you have a website? If yes, please share the URL.")
    return WEBSITE

# Collect website input
async def website(update: Update, context: CallbackContext) -> int:
    context.user_data['website'] = update.message.text
    await update.message.reply_text("Do you have any social media platforms? If yes, please share the URL(s).")
    return SOCIAL_MEDIA

# Collect social media input
async def social_media(update: Update, context: CallbackContext) -> int:
    context.user_data['social_media'] = update.message.text
    await update.message.reply_text("Do you use PPC campaigns? (yes/no)")
    return PPC

# Collect PPC input
async def ppc(update: Update, context: CallbackContext) -> int:
    context.user_data['ppc'] = update.message.text
    await update.message.reply_text("Who are you trying to reach? (e.g., young adults, professionals, etc.)")
    return AUDIENCE

# Collect audience input
async def audience(update: Update, context: CallbackContext) -> int:
    context.user_data['audience'] = update.message.text
    await update.message.reply_text("What location(s) would you like to target?")
    return LOCATION

# Collect location input and generate keywords
async def location(update: Update, context: CallbackContext) -> int:
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
        random_keywords = random.sample(keywords.split("\n"), min(5, len(keywords.split("\n"))))
        await update.message.reply_text(f"Here are some random keywords for your business:\n{', '.join(random_keywords)}")
    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't generate keywords. Please try again later.")
        print(f"Error: {e}")

    await update.message.reply_text("Do you want to upload a document to refine these keywords? (yes/no)")
    return UPLOAD_DOC

# Handle document upload or exit
async def upload_doc(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.lower()
    if user_response == "yes":
        await update.message.reply_text("Please upload your document (PDF only).")
        return UPLOAD_DOC
    elif user_response == "no":
        await update.message.reply_text("Thank you for using the Business Assistant Bot!")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Please respond with 'yes' or 'no'.")
        return UPLOAD_DOC

# Process uploaded document and regenerate keywords
async def process_document(update: Update, context: CallbackContext) -> int:
    if update.message.document and update.message.document.mime_type == "application/pdf":
        document = update.message.document

        try:
            # Download the file to a local path
            file = await context.bot.get_file(document.file_id)
            file_path = f"{document.file_name}"
            await file.download_to_drive(file_path)

            # Extract text from the PDF
            extracted_text = extract_text_from_pdf(file_path)

            # Generate keywords using GPT
            prompt = f"Generate a list of keywords based on the following document content:\n\n{extracted_text}"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert in digital marketing."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )
            keywords = response.choices[0].message['content'].strip()
            await update.message.reply_text(f"Here are the refined keywords:\n{keywords}")

        except Exception as e:
            await update.message.reply_text("Sorry, I couldn't process the document. Please try again later.")
            print(f"Error: {e}")

    else:
        await update.message.reply_text("Please upload a valid PDF document.")

    return ConversationHandler.END


# Cancel command
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def fetch_ppc_data():
    url = "https://databox.com/ppc-industry-benchmarks"
    try:
        # Fetch the page content with SSL verification disabled
        response = requests.get(url, verify=False)  # Disable SSL verification
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the main content from the 'content-column' class
        content = soup.find("div", class_="content-column")
        if not content:
            return "Could not find the relevant content on the website."

        # Extract and clean text from the content container
        text_data = content.get_text(separator="\n", strip=True)
        return text_data

    except Exception as e:
        print(f"Error fetching PPC data: {e}")
        return "An error occurred while fetching PPC data."

# Function to split text into chunks
def split_text_into_chunks(text, max_length=4000):
    """Split the text into chunks to fit Telegram's message limit."""
    lines = text.split("\n")
    chunks = []
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line + "\n"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

# Send PPC trends
async def trends(update: Update, context: CallbackContext):
    try:
        # Fetch and extract PPC data
        data = await fetch_ppc_data()

        # Split the data into manageable chunks
        chunks = split_text_into_chunks(data)

        # Send each chunk as a separate message
        for chunk in chunks:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't fetch the trends at the moment.")
        print(f"Error in /fetch-ppc-data: {e}")

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
# async def cancel(update: Update, context) -> int:
#     await update.message.reply_text("Operation cancelled.")
#     return ConversationHandler.END


# Main function
def main():
    application = Application.builder().token(TELEGRAM_BOT_API_KEY).build()

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
            UPLOAD_DOC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, upload_doc),
                MessageHandler(filters.Document.PDF, process_document),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("trends", trends))  # Add trends handler
    application.add_handler(CommandHandler("faq", faq))  # Add FAQ handler
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
