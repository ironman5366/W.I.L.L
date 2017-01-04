# Builtin imports
import logging
import time
# External imports
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, Job, CallbackQueryHandler, RegexHandler, ConversationHandler,
    Handler
)

# Internal imports
import plugin_handler
import __init__


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

db = None

# Store the button dictionaries of data here because callback_query has to be a string
data_store = {
    "s_1:1": {"type": "snooze_1", "snooze": True},
    "s_1:2": {"type": "snooze_1", "snooze": False},
    "s_2:1": {"type": "snooze_2", "length": 300},
    "s_2:2": {"type": "snooze_2", "length": 900},
    "s_2:3": {"type": "snooze_2", "length": 3600},
    "s_2:4": {"type": "snooze_2", "length": 21600},
    "s_2:5": {"type": "snooze_2", "length": 86400},
    "d_1:1": {"type": "setup_default", "use_search": True},
    "d_1:2": {"type": "setup_default", "use_search": False},
    "c_s:1": {"type": "change_settings", "change_settings": True},
    "c_s:2": {"type": "change_settings", "change_settings": False},
    "s_o:1": {"type": "settings_call", "settings_type": "wolfram"},
    "s_o:2": {"type": "settings_call", "settings_type": "location"},
    "s_o:3": {"type": "settings_call", "settings_type": "default_plugin"},
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
        # TODO: !!!!!! add this callback_data to data_store!
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

def check_user_setup(bot, update):
    '''Check to see if the user has all needed settings.
     If they do, update the db to reflect that'''
    userdata = db["users"]
    user_table = userdata.find_one(chat_id=update.message.chat_id)
    user_setup = (
        user_table["wolfram_key"] and
        user_table["default_plugin"] and
        user_table["location"]
    )
    if user_setup:
        user_table.update(dict(chat_id=update.message.chat_id, user_setup=True), ["chat_id"])


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
    log.debug("Callback query is {0}, commiserate data store is {1}".format(
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
    elif data_type == "setup_default":
        use_search = data["use_search"]
        #If the user wants to use search as the default, set that as the option.
        #If not, get a list of plugins from plugin_handler and supply that as buttons
        chat_id = chat_data["chat_id"]
        if use_search:
            userdata = db["users"]
            user_table = userdata.find_one(chat_id=chat_id)
            data = dict(chat_id=chat_id, default_plugin="search")
            user_table.update(data, ['chat_id'])
        else:
            #Grab the list of plugins from plugin_handler and ask the user which one they'd like as their default
            active_plugins = plugin_handler.plugin_subscriptions
            plugin_keyboard = []
            #For creating the datastore ids
            def create_inline(plugin):
                global data_store
                plugin_name = plugin["name"]
                callback_id = "d_2:{0}".format(plugin_name)
                data_store.update({
                    callback_id: {"type": "custom_default", "name": plugin_name}
                })
                plugin_keyboard.append(InlineKeyboardButton(plugin_name, callback_data=callback_id))
            final_keyboard = []
            final_keyboard.append(plugin_keyboard)
            #Have the user choose which plugin they want to set as their default plugin
            map(create_inline, active_plugins)
            keyboard = InlineKeyboardMarkup(final_keyboard)
            bot.sendMessage(
                update.message.chat_id,
                "Which plugin would you like to set as default?",
                reply_markup=keyboard
            )
    elif data_type == "custom_default":
        #Set the user selected default
        new_default = update.message.text
        username = update.message.from_user.username
        log.info("Setting default plugin for user {0} to {1}".format(
            username, new_default
        ))
        userdata = db["users"]
        chat_id = update.message.chat_id
        user_table = userdata.find_one(chat_id=chat_id)
        data = dict(chat_id=chat_id, default_plugin=new_default)
        user_table.update(data, ['chat_id'])
        ask_more_settings_change(bot, update)
    elif data_type == "change_settings":
        check_user_setup(bot, update)
        if data["change_settings"]:
            settings(bot,update)
        else:
            bot.sendMessage(update.message.chat_id, "Exiting settings.")
    elif data_type == "settings_call":
        setting_selection = data["settings_type"]
        if setting_selection == "wolfram":
            bot.sendMessage(update.message.chat_id, "Please paste in a new wolframalpha key")
        elif setting_selection == "loaction":
            bot.sendMessage(update.message.chat_id, "Please send a new location pin")
        elif setting_selection == "default_plugin":
            choose_default_plugin(bot, update)

def set_wolfram(bot, update):
    '''Collect a wolfram key and wait for it to be pasted in'''
    bot.sendMessage(
        update.message.chat_id,
        "You need a wolframalpha key to use the search functions. If you don't have one, you can get it from" +
        "http://products.wolframalpha.com/api/. Please paste one in now. I'll wait for 15 seconds, but"+
        "you can still paste one in later and I'll recognize it."
    )
    time.sleep(15)



def choose_default_plugin(bot, update):
    '''Have the user select a default plugin'''
    default_plugin_options = [[
        InlineKeyboardButton("Use search (recommended", callback_data="d_1:1"),
        InlineKeyboardButton("Supply your own (experimental)", callback_data="d_1:2")
    ]]
    default_selection = InlineKeyboardMarkup(default_plugin_options)
    bot.sendMessage(update.message.chat_id, "What would you like to do?", reply_markup=default_selection)

def settings(bot, update):
    '''User settings'''
    log.debug("In settings function")
    #Get chat id from update object
    chat_id = update.message.chat_id
    userdata = db["users"]
    #Find the user table from the database usin ghte chat_id
    user_table = userdata.find_one(chat_id=chat_id)
    #Determine whether the user has run the setup process
    user_setup = user_table["user_setup"]
    #If the user has run the setup proces already
    if user_setup:
        settings = [
            InlineKeyboardButton("Change Wolfram Key", callback_data="s_o:1"),
            InlineKeyboardButton("Change Location", callback_data="s_o:2"),
            InlineKeyboardButton("Change Default Plugin", callback_data="s_o:3")
        ]
        settings_keyboard = InlineKeyboardMarkup(settings)
        bot.sendMessage(update.message.chat_id, settings_keyboard)
    else:
        bot.sendMessage(
            chat_id,
            "Welcome to W.I.L.L! Since this is your first time using W.I.L.L, I'll walk you through the setup process"
        )
        set_wolfram(bot, update)
        bot.sendMessage(
            chat_id,
            '''Next, you'll select your default plugin (the plugin that runs when W.I.L.L can't figure out what you
             mean. The recommended plugin for this is "search" a plugin that searches wikipedia, wolframalpha, and
             google for a possible answer to whatever your question is. If you don't want to use search, you can provide
             your own. I'll wait 20 seconds for you to make your choices before continuing
            '''
        )
        choose_default_plugin(bot, update)
        time.sleep(20)
        bot.sendMessage("In order to give W.I.L.L your location, please send a location pin.")
        time.sleep(60)
        check_user_setup(bot, update)



def start(bot, update):
    '''First run commands'''
    log.info("Setting up bot")
    userdata = db['users']
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
        chat_id=update.message.chat_id,
        user_setup=False
    ), ['chat_id'])

    update.message.reply_text(
        "The setting setup function will now be run. If you want to change these at any time, simply run /settings"
    )
    settings(bot, update)

def ask_more_settings_change(bot, update):
    '''Ask the user if they want to change more settings'''
    keyboard = [
        InlineKeyboardButton("Yes", callback_data="c_s:1"),
        InlineKeyboardButton("No", callback_data="c_s:2")
        ]
    markup = InlineKeyboardMarkup(keyboard)
    bot.sendMessage(update.message.chat_id, "Would you like to change more settings?", reply_markup=markup)

def accept_wolfram_key(bot, update):
    '''Store wolfram key given in setup'''
    # If I want to add more steps to setup, add them here
    userdata = db['users']
    data = dict(chat_id=update.message.chat_id, wolfram_key=update.message.text)
    userdata.upsert(data, ['chat_id'])
    log.info("In accept wolfram, table is {0}".format(
        userdata
    ))
    bot.sendMessage(update.message.chat_id, "Thank you! Wolfram key set.")
    ask_more_settings_change(bot, update)

def location_handler(bot, update):
    '''Handle when the user sends a location pin'''
    sender_username = update.message.from_user.username
    #Location object contains longitude and latitude
    location = update.message.location
    #Convert location object to json
    location_json = location.de_json()
    log.debug("Got location {0} from user {1}".format(
        location_json, sender_username
    ))
    chat_id = update.message.chat_id
    user_table = db["users"].find_one(chat_id=chat_id)
    user_table.updsert(dict(chat_id=chat_id, location=location_json), ['chat_id'])
    log.debug("Sent location data from user {0} to db".format(
        sender_username
    ))
    bot.sendMessage("Logged location data")
    check_user_setup(bot, update)


def error(bot, update, error):
    '''Log an error'''
    log.warn('Update "%s" caused error "%s"' % (update, error))

def cancel(bot, update):
    '''Cancel startup conversation'''
    update.message.reply_text("Cancelled.")

def shutdown(bot, update):
    sender_username = update.message.from_user.username
    log.info("Attempted shutdown from user {0}".format(sender_username))
    user_table = db["users"]
    user = user_table.find_one(chat_id=update.message.chat_id)
    if user["admin"]:
        log.info("Shutting down W.I.L.L on command from admin user {0}".format(
            sender_username
        ))
        update.message.reply_text("Shutting down!")
        __init__.shutdown()

    else:
        update.message.reply_text("You need to be an administrator to shutdown W.I.L.L!")

def initialize(bot_token, DB):
    '''Start the bot'''
    global db
    db = DB
    updater = Updater(bot_token)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # Use regex to match strings of text that look like wolfram keys (long alphanumeric strings)

    # on different commands - answer in Telegram
    dp.add_handler(RegexHandler('[\s\S]* [\s\S]*', __init__.command, pass_job_queue=True, pass_chat_data=True))
    # dp.add_handler(MessageHandler(Filters.text, parser.parse, pass_job_queue=True, pass_chat_data=True))
    dp.add_handler(RegexHandler('^[A-Z0-9]{6}-[A-Z0-9]{10}$', accept_wolfram_key))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CallbackQueryHandler(button, pass_chat_data=True, pass_job_queue=True))
    # dp.add_handler(MessageHandler(
    #    Filters.text, parser.parse,pass_job_queue=True,pass_chat_data=True
    # ))
    dp.add_handler(CommandHandler("shutdown", shutdown))
    dp.add_handler(MessageHandler(Filters.location, location_handler))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()