#Builtin modules
import logging
import threading
import time
import Queue

#Internal modules
import plugin_handler
import parser
import core.notification as notification

log = logging.getLogger()

sessions = {}

notifications_queue = Queue.Queue()

class sessions_monitor():
    @staticmethod
    def command(command_data, session,  db, add_to_updates_queue=True):
        '''Control the processing of the command'''
        # Call the parser
        command_data.update({"db": db})
        parse_data = parser.parse(command_data, session)
        log.info("Nlp parsing finished, adding data to event queue")
        response = plugin_handler.subscriptions().process_event(parse_data, db)
        log.debug("Got response {0} from plugin handler".format(response))
        command_id = command_data['id']
        log.info("Setting update for command {0} with response {1}".format(
            command_id, response
        ))
        session_id = session['id']
        #Add the response to the update queue
        global sessions
        if add_to_updates_queue:
            sessions[session_id]["updates"].put({"command_id": command_id, "response": response})
        return response

    def monitor(self, db):
        '''Thread that handles the passive command sessions'''
        while True:
            time.sleep(0.1)
            if not notifications_queue.empty():
                notification = notifications_queue.get()
                #See if the notification specified a handler function
                notification_handler = notification['handler']
                if notification_handler:
                    notification_handler(notification)
                else:
                    username = notification["user"]
                    #Active sessions for the user
                    active_sessions = [i for i in sessions if sessions["i"]["username"] == username]
                    map(lambda s: sessions[s]["updates"].put(notification), active_sessions)
                    notification_thread = threading.Thread(
                        target=notification.send_notification, args=(notification, db))
                    notification_thread.start()

    def __init__(self, db):
        sessions_thread = threading.Thread(target=self.monitor, args=(db, ))
        sessions_thread.start()

def initialize(db):
    '''Intialize the core modules of W.I.L.L'''
    log.info("Loading plugins")
    plugin_handler.load("core/plugins", db)