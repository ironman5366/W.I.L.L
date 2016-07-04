#Internal libs
import will
import will.config as config
from will.logger import log

#Builtin libs
import json
import sys

#External libs
import telebot

log.info("Running will")
will.run()
log.info("Loading telegram config")
telegram_config = config.load_config("telegram")
if telegram_config:
    log.info("Telegram configuration was found. Configuration data is {0}".format(str(telegram_config)))
    bot_key = telegram_config["key"]
    allowed_users = telegram_config["allowed_users"]
    log.info("Starting telegram bot with key {0}".format(bot_key))
    bot = telebot.TeleBot(bot_key)
else:
    log.info("Error: telgram config not found, shutting down")
    sys.exit()

def user_check(message):
    sender = message.from_user
    user = sender.username
    log.info("Message sender is {0}".format(sender))
    return user in allowed_users

def action_return(message, answer_json):
    response = {}
    answer_action = answer_json["return_action"]
    answer_type = answer_json["return_type"]
    response.update({"response_args": message.teext, "response_type": answer_type, "return_action": answer_action})
    for key in answer_json.keys():
        if not response[key]:
            response.update({key: answer_json[key]})
    returned = will.main(response)
    return_json = json.dumps(returned)
    return_type = return_json["return_type"]
    return_text = answer_json["text"]
    if return_type == "text":
        bot.reply_to(message, return_text)
    else:
        return_message = bot.reply_to(message, return_text)
        bot.register_next_step_handler(return_message, return_json)

@bot.message_handler(commands=["help"])
def help(message):
    bot.reply_to(message, "help command recognized")

@bot.message_handler(content_types=["text"])
def command(message):
    '''Setup basic information and get started'''
    log.info("In setup with message {0}".format(str(message)))
    if user_check(message):
        command = message.text
        log.info("Command is {0}".format(str(command)))
        answer = will.main(str(command))
        answer_json = json.loads(answer)
        answer_text = answer_json["text"]
        answer_type = answer_json["return_type"]
        if answer_type == "text":
            bot.reply_to(message, answer_text)
        else:
            return_message = bot.reply_to(message, answer_text)
            bot.register_next_step_handler(return_message, answer_json)

log.info("Starting bot")
bot.polling()