#Builtin imports
import json
import logging

# External imports
import requests

# Internal imports
from will import tools

log = logging.getLogger()

class send_notification():
    """
    Send all necessary notifications
    """
    @staticmethod
    def email(mailgun_key, mailgun_url, email, msg_summary, msg, first_name, last_name):
        """
        Send an email to the user

        :param mailgun_key:
        :param mailgun_url:
        :param email:
        :param msg_summary:
        :param msg:
        :param first_name:
        :param last_name:
        """
        return requests.post(
            mailgun_url,
            auth=("api", mailgun_key),
            data={"from": "will <postmaster@willbeddow.com>",
                  "to": "{0} {1} <{2}>".format(first_name,last_name,email),
                  "subject": msg_summary,
                  "text": msg})
    def __init__(self, notification, db):
        """
        Determine what notifications to send and send them

        :param notification:
        :param db:
        """
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
                msg_summary = "will - "+msg_summary
                user_email = user_table["email"]
                first_name = user_table["first_name"]
                last_name = user_table["last_name"]
                log.info("Sending email with subject {0} to email {1}".format(msg_summary, user_email))
                send_notification.email(mailgun_key, mailgun_url, user_email, msg_summary, msg, first_name, last_name)
                log.debug("Successfully sent email with subject {0} to email {1}".format(msg_summary, user_email))
            #TODO: add options for more notification methods (phone, will-Telegram, etc.)