#Builtin modules
import logging
import threading
import time
import requests

#Internal modules
try:
    import core.plugin_handler as plugin_handler
    import core.parser as parser
except ImportError:
    import plugin_handler
    import parser
import core.notification as notification
import tools

log = logging.getLogger()

sessions = {}

events = []

processed_commands = 0

error_num = 0

success_num = 0

commands = {}

class sessions_monitor():
    @staticmethod
    def command(command_data, session,  db, add_to_updates_queue=True):
        """
        Main command parsing function

        :param command_data:
        :param session:
        :param db:
        :param add_to_updates_queue:
        :return: response object
        """
        global processed_commands
        global error_num
        global success_num
        processed_commands+=1
        # Call the parser
        command_data.update({"db": db})
        parse_data = parser.parse(command_data, session)
        command_id = command_data['id']
        parse_data.update({"command_id": command_data['id']})
        log.info(":{0}:Finished parsing".format(command_id))
        response = plugin_handler.subscriptions().process_event(parse_data, db)
        log.info("Got response {0} with type {1}".format(response, type(response)))
        if response["type"] == "success":
            success_num+=1
        else:
            error_num+=1
        log.debug("Got response {0} from plugin handler".format(response))
        log.info("{0}:Setting update for command with response {1}".format(
            command_id, response
        ))
        session_id = session['id']
        #Add the response to the update queue
        global sessions
        if add_to_updates_queue:
            sessions[session_id]["updates"].put({"command_id": command_id, "response": response})
        if session_id in commands.keys():
            commands[session_id].append([command_data["command"], response["text"]])
        else:
            commands.update({session_id:
                             [[command_data["command"], response["text"]]]})
        return response

    @staticmethod
    def update_sessions(username, update_data):
        """
        :param username:
        :param update_data:

        Puts data into the update queue for the user so the client can serve it to them

        """
        active_sessions = [i for i in sessions if sessions[i]["username"] == username]
        map(lambda s: sessions[s]["updates"].put(update_data), active_sessions)

    def monitor(self, db):
        """
        :param db:

        Thread that continuously handles passive events, like event triggers

        """
        global events
        while True:
            time.sleep(0.1)
            if events:
                for event in events:
                    current_time = time.time()
                    if event["time"] <= current_time:
                        log.debug("Processing event {0}".format(event))
                        event_type = event["type"]
                        if event_type == "notification":
                            username = event["username"]
                            #Active sessions for the user
                            sessions_monitor.update_sessions(username, event)
                            update_data = {"type": "notification", "text": event["value"], "data": event}
                            sessions_monitor.update_sessions(username, update_data)
                            notification_thread = threading.Thread(
                                  target=notification.send_notification, args=(event, db))
                            notification_thread.start()
                        elif event_type == "url":
                            response = requests.get(event["value"]).text
                            update_data = {"type": "event", "text": response, "data": event}
                            username = event["username"]
                            sessions_monitor.update_sessions(username, update_data)
                        elif event_type == "function":
                            response = event["value"]()
                            update_data = {"type": "event", "text": response, "data": event}
                            username = event["username"]
                            sessions_monitor.update_sessions(username, update_data)
                        events.remove(event)


    def __init__(self, db):
        """
        Start the passive thread

        :param db:
        """
        #Pull pending notifications
        db.query('delete from `events` where time <= {0}'.format(time.time()))
        for i in db['events'].all():
            events.append(i)
        sessions_thread = threading.Thread(target=self.monitor, args=(db,))
        sessions_thread.start()

def initialize(db):
    """
    Run the plugin loader

    :param db:
    """
    log.info("Loading plugins")
    plugin_handler.load("core/plugins", db)