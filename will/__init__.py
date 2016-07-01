# 3rd party libs
import requests
import keyring

# Builtin libs
import threading
import json
import time
import logging
import atexit

# internals
from will.logger import log
import plugins
import config
import webapi
from will import nlp

session_data = {"command" : False, "username" : False, "password" : False, "session_id" : False}

#TODO: add command and user selection to the nlp
#TODO: add a framework to ask questions back
def main(command):
    log.info("In main function, command is {0}".format(command))
    log.info("Starting plugin parsing")
    plugin_command = plugins.Command(command)
    answer = plugin_command.dispatch_event()
    return answer
@atexit.register
def exit_func():
    #End the session
    logging.info("Ending the session")
    #webapi.session().end(session_data)
    log.info("Shutting down.")
    plugins.unload_all()


def run():
    '''Open logs, check log settings, and start the flask server and slack thread'''
    log.info('''

\                /   |    |              |
 \              /    |    |              |
  \            /     |    |              |
   \    /\    /      |    |              |
    \  /  \  /       |    |              |
     \/    \/        |    ------------   ------------
        ''')
    if log.getEffectiveLevel() == logging.DEBUG:
        debugval = True
    else:
        debugval = False
    #Load the plugins
    plugins.load("plugins/")
    log.info("Debug value is {0}".format(debugval))