#Builtin modules
import logging
import threading
import time
import urllib2

#Internal modules
import plugin_handler
import parser
import core.notification as notification
import tools

log = logging.getLogger()

sessions = {}

events = []

processed_commands = 0

class sessions_monitor():
    @staticmethod
    def command(command_data, session,  db, add_to_updates_queue=True):
        '''Control the processing of the command'''
        global processed_commands
        global successfully_run
        global errored
        processed_commands+=1
        # Call the parser
        command_data.update({"db": db})
        parse_data = parser.parse(command_data, session)
        log.info(":{0}:nlp parsing finished, adding data to event queue".format(session["id"]))
        response = plugin_handler.subscriptions().process_event(parse_data, db)
        log.debug("Got response {0} from plugin handler".format(response))
        command_id = command_data['id']
        log.info("{0}:Setting update for command with response {1}".format(
            command_id, response
        ))
        session_id = session['id']
        #Add the response to the update queue
        global sessions
        if add_to_updates_queue:
            sessions[session_id]["updates"].put({"command_id": command_id, "response": response})
        #TODO: make it so that plugin_handler can send an error
        #TODO: accept a dict
        return response

    @staticmethod
    def update_sessions(username, update_data):
        active_sessions = [i for i in sessions if sessions[i]["username"] == username]
        map(lambda s: sessions[s]["updates"].put(update_data), active_sessions)

    def monitor(self, db):
        '''Thread that handles the passive command sessions'''
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
                            response = urllib2.urlopen(event["value"]).read()
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
        #Pull pending notifications
        db["events"].delete(time <= time.time())
        for i in db['events'].all():
            events.append(i)
        sessions_thread = threading.Thread(target=self.monitor, args=(db,))
        sessions_thread.start()

def initialize(db):
    '''Intialize the core modules of W.I.L.L'''
    log.info("Loading plugins")
    plugin_handler.load("core/plugins", db)