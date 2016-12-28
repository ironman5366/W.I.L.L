# Builtin imports
import logging
import sys
# External imports
import dataset
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, Job, CallbackQueryHandler, RegexHandler, ConversationHandler,
    Handler
)

# Internal imports
import parser
import plugin_handler
import main

log = logging.getLogger()

events = {}

nlp = None

help_str = '''
Commands:
/help: Print this string
/start: Start the bot and create a userdata table with your username
/settings: Change user settings
If not given a telegram command, W.I.L.L will try to interpret your command as a personal assistant
'''

# TODO: add a /settings function!

db = dataset.connect('sqlite:///will.db')

# Store the button dictionaries of data here because callback_query has to be a string
data_store = {
    "s_1:1": {"type": "snooze_1", "snooze": True},
    "s_1:2": {"type": "snooze_1", "snooze": False},
    "s_2:1": {"type": "snooze_2", "length": 300},
    "s_2:2": {"type": "snooze_2", "length": 900},
    "s_2:3": {"type": "snooze_2", "length": 3600},
    "s_2:4": {"type": "snooze_2", "length": 21600},
    "s_2:5": {"type": "snooze_2", "length": 86400}
}

def help(bot, update):
    '''Print help message'''
    update.message.reply_text(help_str)


def send_message(bot, chat_id, message_text):
    '''Send a text message'''
    bot.sendMessage(chat_id, message_text)


def check_plugin(plugins, event):
    '''Check which plugin the user wants to run'''
    # Use the in place button conversation handler
    keyboard = []

    def add_to_keyboard(plugin):
        keyboard.append(
            InlineKeyboardButton(plugin["name"], callback_data=
            {"type": "plugin_selection", "event": event, "plugin_function": plugin["function"], "name": plugin["name"]})
        )

    # Add all the possible plugins to an inline keyboard
    map(add_to_keyboard, plugins)
    plugin_choice_inline = InlineKeyboardMarkup(keyboard)
    event["bot"].sendMessage(event["update"].message.chat.id, text="Please select a plugin to run",
                             reply_markup=plugin_choice_inline)


def alarm(bot, job):
    """Function to send the alarm message"""
    alarm_text = job.context["alarm_text"]
    chat_id = job.context["chat_id"]
    log.info("Activating job with alarm text {0} to chat id {1}".format(alarm_text, chat_id))
    keyboard = [
        [InlineKeyboardButton("Snooze", callback_data="s_1:1"),
         InlineKeyboardButton("Dismiss", callback_data="s_1:2")]]
    snooze_inline = InlineKeyboardMarkup(keyboard)
    bot.sendMessage(chat_id, text=alarm_text, reply_markup=snooze_inline)


def set_job(update, due, job_queue, chat_data, alarm_text, response_text=None):
    '''Adds a job to the job queue'''
    chat_id = update.message.chat_id
    # Time for the timer in seconds
    assert type(due) == int
    # Put relevant alarm data in context and set the alarm
    chat_data["chat_id"] = chat_id
    chat_data["alarm_text"] = alarm_text
    job = Job(alarm, due, repeat=False, context=chat_data)
    chat_data['job'] = job
    job_queue.put(job)
    if response_text:
        update.message.reply_text(response_text)


def button(bot, update, job_queue, chat_data):
    '''Button response'''
    query = update.callback_query.data
    data = data_store[query]
    log.debug("Callback queyr is {0}, commiserate data store is {1}".format(
        query, data
    ))
    data_type = data["type"]
    if data_type == "snooze_1":
        snooze = data["snooze"]
        if snooze:
            keyboard = [[InlineKeyboardButton("5 minutes", callback_data="s_2:1"),
                         InlineKeyboardButton("15 minutes", callback_data="s_2:2"),
                         InlineKeyboardButton("1 hour", callback_data="s_2:3"),
                         InlineKeyboardButton("6 hours", callback_data="s_2:4"),
                         InlineKeyboardButton("1 day", callback_data="s_2:5")
                         ]]
            snooze_inline = InlineKeyboardMarkup(keyboard)
            bot.sendMessage(chat_data["chat_id"], text="How long would you like to snooze?",
                            reply_markup=snooze_inline)
        else:
            bot.sendMessage(chat_data["chat_id"], "Dismissed.")
    elif data_type == "snooze_2":
        due = data["length"]
        job = Job(alarm, due, repeat=False, context=chat_data)
        chat_data["job"] = job
        job_queue.put(job)
        bot.sendMessage(chat_data["chat_id"], text="Snoozed")
    elif data_type == "plugin_selection":
        event_data = data['event']
        plugin_function = data["function"]
        log.info("Calling plugin {0}".format(
            data["plugin_name"]
        ))
        # Call the plugin
        plugin_handler.subscriptions().call_plugin(plugin_function, event_data)


def start(bot, update):
    '''First run commands'''
    log.info("Setting up bot")
    db = dataset.connect('sqlite:///will.db')
    userdata = db['userdata']
    admin_username = "willbeddow"
    log.info("Admin username is {0}".format(admin_username))
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name
    chat_id = update.message.chat_id
    # Determine whether the user is the admin user
    user_is_admin = username == admin_username
    log.info("User data is as follows: username is {0}, first_name is {1}, user_is_admin is {2}, chat_id is {3}".format(
        username, first_name, user_is_admin, chat_id
    ))
    userdata.upsert(dict(
        first_name=update.message.from_user.first_name,
        username=update.message.from_user.username,
        admin=user_is_admin,
        default_plugin="search"
    ), ['username'])
    update.message.reply_text(
        "In order to use the search functions, you need a wolframalpha api key. Please paste one in:"
    )


def accept_wolfram_key(bot, update):
    '''Store wolfram key given in setup'''
    # If I want to add more steps to setup, add them here
    username = update.message.from_user.username
    db = dataset.connect('sqlite:///will.db')
    userdata = db['userdata']
    data = dict(username=username, wolfram_key=update.message.text)
    userdata.upsert(data, ['username'])
    log.info("In accept wolfram, table is {0}".format(
        userdata
    ))


def error(bot, update, error):
    '''Log an error'''
    log.warn('Update "%s" caused error "%s"' % (update, error))

def cancel(bot, update):
    '''Cancel startup conversation'''
    update.message.reply_text("Cancelled.")

def shutdown(bot, update):
    sender_username = update.message.from_user.username
    log.info("Attempted shutdown from user {0}".format(sender_username))
    db = dataset.connect('sqlite:///will.db')
    user_table = db["userdata"]
    user = user_table.find_one(username=sender_username)
    if user["admin"]:
        log.info("Shutting down W.I.L.L on command from admin user {0}".format(
            sender_username
        ))
        update.message.reply_text("Shutting down!")
        main.shutdown()

    else:
        update.message.reply_text("You need to be an administrator to shutdown W.I.L.L!")
def initialize(bot_token):
    '''Start the bot'''
    updater = Updater(bot_token)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # Use regex to match strings of text that look like wolfram keys (long alphanumeric strings)

    # on different commands - answer in Telegram
    dp.add_handler(RegexHandler('[\s\S]* [\s\S]*', parser.parse, pass_job_queue=True, pass_chat_data=True))
    # dp.add_handler(MessageHandler(Filters.text, parser.parse, pass_job_queue=True, pass_chat_data=True))
    dp.add_handler(RegexHandler('^[A-Z0-9]{6}-[A-Z0-9]{10}$', accept_wolfram_key))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CallbackQueryHandler(button, pass_chat_data=True, pass_job_queue=True))
    # dp.add_handler(MessageHandler(
    #    Filters.text, parser.parse,pass_job_queue=True,pass_chat_data=True
    # ))
    dp.add_handler(CommandHandler("shutdown", shutdown))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()