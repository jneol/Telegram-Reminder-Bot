import logging
import telegram
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext, ConversationHandler
from datetime import datetime
import os
import pytz
import csv
import time
from telegram.ext.dispatcher import run_async
import config
PORT = int(os.environ.get('PORT', 5000))

bot = telegram.Bot(token=config.telegram_token)


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

STARTING, TASKNAME, DEADLINE1, DEADLINE2, REMIND = range(5)

def help_command(update, context):
    update.message.reply_text('<u>A couple of things to take note of</u>:\n1. The <b>Date & Time</b> format has to be entered precisely according to the examples provided. Please re-enter your reminder from scratch if you messed up somewhere.\n2. The bot currently only supports the <b>Asia/Singapore (GMT+8)</b> timezone.\n3. Please dm the creator should there be any bugs/suggestions!', parse_mode="HTML")

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /newreminder is issued."""
    user = update.effective_user
    update.message.reply_markdown_v2(fr'Hi {user.mention_markdown_v2()} \! 👋')
    keyboard = [
        [
            InlineKeyboardButton("New Task/Reminder", callback_data='1'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('What would you like to do today?', reply_markup=reply_markup)
    return TASKNAME

def task_name(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user = update.effective_user
    f = open("new" + str(user['id']) + ".txt", "w+")
    f.write(str(update.message.chat.id) + "\n" + text + "\n")
    f.close()
    update.message.reply_text(f"Your reminder is <b>{text}</b>. Please input the deadline for this task/reminder <i>(E.g. 25/12/2021)</i>.\nEnter <i>Today</i> for today's date.", parse_mode="HTML", reply_markup=ForceReply(selective=True))
    return DEADLINE1

def deadline1(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if len(text) != 10 and text.lower() != "today":
        bot.sendMessage(chat_id=update.message.chat.id,text="Invalid input. Please try again.")
        return -1
    if text.lower() == "today":
        text = str(datetime.now(pytz.timezone('Asia/Singapore')).strftime("%d/%m/%Y"))
    try:
        valid_date_test = datetime.strptime(text, "%d/%m/%Y").strftime("%d/%m/%Y")
        user = update.effective_user
        f = open("new" + str(user['id']) + ".txt", "a+")
        f.write(text + "\n")
        f.close()
        update.message.reply_text(f"Please input the time for this reminder <i>(E.g. 2355)</i>", parse_mode="HTML", reply_markup=ForceReply(selective=True))
        return DEADLINE2
    except IndexError:
        bot.sendMessage(chat_id=update.message.chat.id,text="Invalid input. Please try again.")
        return -1
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat.id,text="Invalid input. Please try again.")
        return -1    

def deadline2(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if len(text) != 4:
        bot.sendMessage(chat_id=update.message.chat.id,text="Invalid input. Please try again.")
        return -1
    try:
        valid_time_test = datetime.strptime(text, "%H%M").strftime("%H%M")
        user = update.effective_user
        username = str(user['username'])
        firstname = str(user['first_name'])
        lastname = str(user['last_name'])           
        f = open("new" + str(user['id']) + ".txt", "a+")
        f.write(text + "\n")
        f.close()
        
        with open("new" + str(user['id']) + ".txt", "r", newline="") as r:
            with open("reminders.csv", "a+", newline="") as f:
                csvwriter = csv.writer(f, escapechar=' ', quoting=csv.QUOTE_NONE)
                entry = str(user['id']), r.readline().split("\r\n")[0], r.readline().split("\r\n")[0], r.readline().split("\r\n")[0]
                csvwriter.writerow(entry)
            
        with open("new" + str(user['id']) + ".txt", "r", newline="") as r:
            r.readline().strip("\r\n")
            update.message.reply_text("Your reminder <b>{}</b> is due on <b>{}</b> at <b>{}</b>. A reminder will be sent when the time comes.".format(r.readline().strip("\r\n"), r.readline().strip("\r\n"), r.readline().strip("\r\n")), parse_mode="HTML")
        with open("new" + str(user['id']) + ".txt", "r", newline="") as r:    
            send_reminder1(r.readline().strip("\r\n"), r.readline().strip("\r\n"), r.readline().strip("\r\n"), r.readline().strip("\r\n"), username, firstname, lastname)
        return -1
    except IndexError:
        bot.sendMessage(chat_id=update.message.chat.id,text="Invalid input. Please try again.")
        return -1
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat.id,text="Invalid input. Please try again.")
        return -1

@run_async
def send_reminder1(uid, taskname, date, time0, username, firstname, lastname):
    date1 = int(date.split("/")[0])
    month = int(date.split("/")[1])
    year = int(date.split("/")[2])
    hour = int(time0[0:2])
    minute = int(time0[2:4])
    send_time = pytz.timezone('Asia/Singapore').localize(datetime(year, month,  date1, hour, minute))
    print(send_time)
    time.sleep(send_time.timestamp() - time.time())
    send_reminder2(uid, taskname)
    print("Reminder sent! [@{} | {} {}]".format(username, firstname, lastname))
    return -1

@run_async
def send_reminder2(uid, taskname):
    bot.sendMessage(chat_id=uid,text="🚨 Your reminder <b>{}</b> is now due. 🚨".format(taskname), parse_mode="HTML")
    return -1

def button(update: Update, context: CallbackContext) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    query.edit_message_text(text=f"Please enter the name of the reminder:")
    return TASKNAME

def done(update: Update, context: CallbackContext) -> int:
    """Display the gathered info and end the conversation."""
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(config.telegram_token, workers = 32)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CallbackQueryHandler(button))

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('newreminder', start, run_async=True)],
        states={
            TASKNAME: [
                MessageHandler(
                    Filters.regex(''), task_name
                )
            ],
            DEADLINE1: [
                MessageHandler(
                    Filters.regex(''), deadline1
                )
            ],
            DEADLINE2: [
                MessageHandler(
                    Filters.regex(''), deadline2
                )
            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.

if __name__ == '__main__':
    main()


