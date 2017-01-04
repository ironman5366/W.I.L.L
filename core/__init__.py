#Builtin modules
import logging
import threading
import time

#Internal modules
import plugin_handler
import parser

log = logging.getLogger()

sessions = {}

class sessions_monitor():
    def command(command_data, session,  db):
        '''Control the processing of the command'''
        # Call the parser
        parse_data = parser.parse(command_data, session)
        log.info("Nlp parsing finished, adding data to event queue")
        response = plugin_handler.subscriptions.process_event(parse_data, db)
        log.debug("Got response {0} from plugin handler".format(response))
        command_id = command_data['id']
        log.info("Setting update for command {0} with response {1}".format(
            command_id, response
        ))
        session_id = session['id']
        #Add the response to the update queue
        global sessions
        sessions[session_id]["updates"].put({command_id:response})

    def monitor(self, db):
        '''Thread that handles the active command sessions'''
        while True:
            time.sleep(0.1)
            for session_id in sessions:
                session = sessions[session_id]
                #Check for new commands in the session command queue
                new_command = session["commands"].get()
                if new_command:
                    log.info("Found command {0} in session {1}, submitting it for parsing".format(
                        new_command, session_id
                    ))
                    self.command(new_command, session,  db)
    def __init__(self, db):
        sessions_thread = threading.Thread(target=self.monitor, args=(db, ))

def initialize(db):
    '''Intialize the core modules of W.I.L.L'''
    log.info("Loading plugins")
    plugin_handler.load("core/plugins", db)