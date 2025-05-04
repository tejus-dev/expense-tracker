import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re
import os


# Logging
logging.basicConfig(level=logging.INFO)

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(os.path.join(os.path.dirname(__file__), "creds.json"), scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Expenses").sheet1

# Categories
CATEGORIES = ["Food", "Travel", "Rent", "Investment", "Lending", "Misc"]

# Temp memory for mapping Telegram user messages
pending_entries = {}

# Extract amount and note from message
def parse_expense(text):
    match = re.search(r"₹?(\d+)\s*(.*)", text)
    if match:
        amount = match.group(1)
        note = match.group(2).strip().capitalize()
        return amount, note if note else "Misc"
    return None, None

# Handle incoming message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    amount, note = parse_expense(text)
    
    if amount:
        # Store temp entry for the user
        pending_entries[user_id] = {"amount": amount, "note": note}

        # Send category selection buttons
        keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Choose a category for ₹{amount} - {note}:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Send expense in format: ₹250 Coffee")

# Handle category button click
async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id in pending_entries:
        entry = pending_entries.pop(user_id)
        category = query.data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, entry["amount"], category, entry["note"]])
        await query.edit_message_text(f"Saved: ₹{entry['amount']} - {category} - {entry['note']}")
    else:
        await query.edit_message_text("No expense found to categorize.")

# Bot token
TOKEN = "YOUR_BOT_TOKEN"  # Make sure to replace this with your bot token

# Run the bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app.add_handler(CallbackQueryHandler(handle_category))

print("Bot is running... Press Ctrl+C to stop.")
app.run_polling()
