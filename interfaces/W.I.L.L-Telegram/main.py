#Builtin imports
import os
import logging
import json
import time
import threading

#External imports
import telegram
from socketIO_client import SocketIO, LoggingNamespace, BaseNamespace
from telegram.ext import (
Updater, CommandHandler, MessageHandler, Filters
)
import requests
import dataset

CONF_FILE = "will-telegram.conf"

if os.path.isfile('will-telegram.conf'):
    configuration_data = json.loads(open('will-telegram.conf').read())
    SERVER_URL = configuration_data["server_url"]
    TOKEN = configuration_data["bot_token"]
    LOGFILE = configuration_data["logfile"]
    DB_URL = configuration_data["db_url"]


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename=LOGFILE,
                    filemode='w'
                    )

log = logging.getLogger()

db = dataset.connect(DB_URL)

help_str = '''
Welcome to W.I.L.L! If you don't have an account yet, please sign up at http://67.205.186.54/static/signup_page.html.
There are only two commands that you need to learn about for this bot:
/login <username> <password>: login to W.I.L.L and generate a session token.
/help: Print this message
'''

def help(bot, update):
    '''Echo the help string'''
    bot.sendMessage(update.message.chat_id, help_str)

def socket_io_thread(bot,session_id, chat_id ):
    socketIO = SocketIO(SERVER_URL, 80)
    socketIO.on('connect', lambda: socketIO.emit("get_updates", session_id))
    socketIO.on('update', lambda x: bot.sendMessage(chat_id, (x["value"])))
    socketIO.on('disconnect', lambda x: bot.sendMessage(chat_id, "Update server has disconnected"))
    socketIO.on('debug', lambda x: log.info("Got debug message {0} from socketIO".format(x["value"])))
    socketIO.wait()

def login(bot, update):
    '''Login to W.I.L.L and store the session id in the db'''
    message = update.message.text
    message_split = message.split("/login ")[1].split(" ")
    username = message_split[0]
    password = message_split[1]
    log.info("Trying to log into W.I.L.L with username {0}".format(username))
    payload = {"username": username, "password": password}
    response = requests.post(url="{0}/api/start_session".format(SERVER_URL), data=payload).json()
    if response["type"] == "success":
        log.info("Logged in user {0} successfully, putting their session token in the db")
        update.message.reply_text(response["text"]+" Thank you for logging in. For security, please delete the /login" \
                                                    " command in the chat")
        db['telegram'].upsert(dict(
            username=username, chat_id=update.message.chat_id, session_id=response["data"]["session_id"])
            , ['username']
        )
        socket_thread = threading.Thread(target=socket_io_thread, args=(
            bot, response["data"]["session_id"],update.message.chat_id))
        socket_thread.start()
    else:
        log.info("Got error logging in with user {0}. Error text is {1}".format(username, response["text"]))
        update.message.reply_text(response["text"])

def start(bot, update):
    '''Standard /start command'''
    update.message.reply_text("Welcome to W.I.L.L! To get started, please run /login <username> <password>.")

def command(bot, update):
    '''A W.I.L.L command'''
    message = update.message.text
    user = db['telegram'].find_one(chat_id=update.message.chat_id)
    if user:
        session_id = user["session_id"]
        payload = {"session_id": session_id, "command": message}
        try:
            response = requests.post(
            url="{0}/api/command".format(SERVER_URL),
            data=payload
            ).json()
            log.info("Got response {0} from command {1}".format(response, command))
            if response["type"] == "success":
                update.message.reply_text(response["text"])
            else:
                if response["text"] == "Invalid session id":
                    update.message.reply_text(
                        "It looks like W.I.L.L has rebooted. Please run /login <username> <password> "
                        "again to start another session")
                else:
                    update.message.reply_text("Error: " + response["text"])
        except Exception as command_exception:
            log.info("Caught exception {0}, {1} while sending command to W.I.L.L".format(
                command_exception.message,
                command_exception.args
            ))
            update.message.reply_text("Didn't receive a response from the W.I.L.L server, W.I.L.L is most likely down")
    else:
        update.message.reply_text("Couldn't find you in the database. Please run /login <username> <password>")


def error(bot, update, error):
    '''Log an error'''
    log.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("login", login))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(Filters.text, command))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()