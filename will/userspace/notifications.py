# Builtin imports
import logging
import time
import uuid
import datetime
import threading

# External imports
import requests

# Internal imports
from will import tools
from will import transactions

log = logging.getLogger()


class Notification:

    _mail_api = None

    def __init__(self, message, title, trigger_time, scope, graph, user_data, summary=None, uid=None, created=None):
        """
        Create a Notification object

        :param message: The message body of the notification
        :param title: The title of the notification
        :param trigger_time: When the notification should be sent, in epoch time
        :param scope: The scope of the notification
        :param graph: The db
        :param user_data: Information about the user the notification is being sent to
        :param summary: The summary text of the notification
        :param uid: The unique identifier for the notification
        :param created: The datetime object representing when the notification was created
        """
        # Decode the message and the title into ascii for maximum compatibility
        self.title = tools.ascii_encode("W.I.L.L - " + title)
        self.message = tools.ascii_encode(message)
        self.scope = scope
        self.graph = graph
        self._summary = summary
        if created:
            self.created = created
        else:
            self.created = datetime.datetime.now()
        if uid:
            self.uid = uid
        else:
            self.uid = uuid.uuid1()
        self.trigger_time = trigger_time
        self.user_data = user_data

    def send(self):
        """
        Check the scope of the notification and send the notification in the corresponding way
        """
        log.info("Sending notification to user {}".format(self.user_data["username"]))
        # Check the users notification preferences
        not_method = self.scope
        mappings = {
            "email": self.email
        }
        if not_method in mappings.keys():
            not_callable = mappings[not_method]
            not_callable()
        else:
            log.error("Couldn't find a notification method for notification scope {}".format(not_method))

    def email(self):
        """
        Send an email to the user
        """
        mailgun_key, mailgun_url = tools.load_key("mailgun", self.graph, load_url=True)
        email = self.user_data["settings"]["email"]
        first_name = self.user_data["first_name"]
        last_name = self.user_data["last_name"]
        return requests.post(
            mailgun_url,
            auth=("api", mailgun_key),
            data={"from": "will <postmaster@willbeddow.com>",
                  "to": "{0} {1} <{2}>".format(first_name, last_name, email),
                  "subject": self.summary,
                  "text": self.message})

    @property
    def time_reached(self):
        return time.time() >= self.trigger_time

    @property
    def summary(self):
        if not self._summary:
            # Use the first 5 words of the message for a summary
            if " " in self.message:
                message_words = self.message.split(" ")
                if len(message_words) >= 5:
                    self._summary = message_words[0:4]
                else:
                    self._summary = self.message
            else:
                self._summary = self.message
            self._summary = tools.ascii_encode(self._summary)
        return self._summary


class NotificationHandler:
    running = True
    _notifications = {}

    def __init__(self, graph):
        """
        :param graph: The DB instance
        """
        self.graph = graph
        # Pull the notifications from the database
        self._pull_notificatons()
        # Start the notification monitoring thread
        wait_thread = threading.Thread(target=self._wait_notifications)
        wait_thread.start()

    def notify(self, not_object):
        """
        Put a newly created notification in the internal notifications dict, and update the db

        :param not_object: An instantiated Notification class
        """
        not_uid = not_object.uid
        self._notifications.update({not_uid: not_object})
        # If the notification is due for less than 5 minutes, don't bother putting it into the database
        if not_object.trigger_time - time.time() > 300:
            # Pull the necessary information out of the notification and format it accordingly
            not_user = not_object.user_data["username"]
            not_created = not_object.created
            not_created_timestamp = not_created.timestamp()
            # Insert the notification into the db
            with self.graph.session() as session:
                session.write_transaction(
                    transactions.create_notification,
                    not_user,
                    not_object.message,
                    not_object.title,
                    not_object.trigger_time,
                    not_object.scope,
                    not_created_timestamp,
                    not_object.summary,
                    not_object.uid
                    )

    def _pull_notificatons(self):
        """
        Pull all notifications for each user
        """
        session = self.graph.session()
        notifications = session.run("MATCH (u:User)-[:SET]->(n:Notification)"
                                    "return u,n")
        if notifications:
            for notification in notifications:
                user_set = notification["u"]
                not_object = notification["n"]
                datetime_instance = datetime.datetime.fromtimestamp(not_object.created)
                not_class = Notification(
                    not_object.message,
                    not_object.title,
                    not_object.trigger_time,
                    not_object.scope,
                    user_set,
                    not_object.summary,
                    not_object.uid,
                    datetime_instance)
                self._notifications.update({not_object.uid: not_class})
            # Instantiate a `Notification` class for each one
        else:
            log.info("No notifications found from DB")
        session.close()

    def _wait_notifications(self):
        """
        Thread that iterates through queued notifications
        """
        while self.running:
            if self._notifications:
                for not_uid, notification in self._notifications.items():
                    # Check if the notification is ready to send
                    if notification.time_reached:
                        # If it is, send it and remove it from the list
                        log.info("Sending notification for user {}".format(notification.user_data["username"]))
                        try:
                            notification.send()
                        except Exception as e:
                            log.error(
                                "Couldn't send notification to user {0}. Send method raised error with args {1}".format(
                                    notification.user_data["username"], e.args
                            ))
                        del self._notifications[not_uid]
                        # Remove the notification from the database
                        with self.graph.session() as session:
                            session.write_transaction(transactions.delete_notification, notification.uid)
                time.sleep(0.2)
            else:
                time.sleep(1)


