#Builtin imports
import json
import logging
#External imports
import requests
#Internal imports
import tools

log = logging.getLogger()

class send_notification():
    '''Send all necessary notifications given notification object'''
    @staticmethod
    def email(mailgun_key, mailgun_url, email, msg_summary, msg, first_name, last_name):
        return requests.post(
            mailgun_url,
            auth=("api", mailgun_key),
            data={"from": "W.I.L.L <postmaster@sandbox06554aeb16304616ba6c4886d5433bf7.mailgun.org>",
                  "to": "{0} {1} <{2}>".format(first_name,last_name,email),
                  "subject": msg_summary,
                  "text": msg})
    def __init__(self, notification, db):
        '''Determine what notifiications to send and send them'''
        username = notification['username']
        user_table = db['users'].find_one(username=username)
        user_handlers_json = user_table['notifications']
        user_notifications = json.loads(user_handlers_json)
        log.debug("Notifcation handlers for user {0} are {1}".format(
            username, user_notifications
        ))
        for handler in user_notifications:
            if handler == "email":
                log.debug("Emailing user {0} notification {1}".format(
                    username, notification
                ))
                mailgun_key, mailgun_url = tools.load_key('mailgun', db, load_url=True)
                msg = notification["value"]
                if "summary" in notification.keys():
                    msg_summary = notification["summary"]
                else:
                    words = msg.split()
                    words_num = len(words)
                    if words_num >= 5:
                        msg_summary = ' '.join(words[0:5])
                    else:
                        msg_summary = msg
                msg_summary = "W.I.L.L - "+msg_summary
                user_email = user_table["email"]
                first_name = user_table["first_name"]
                last_name = user_table["last_name"]
                send_notification.email(mailgun_key, mailgun_url, user_email, msg_summary, msg, first_name, last_name)
            #TODO: add options for more notification methods (phone, W.I.L.L-Telegram, etc.)