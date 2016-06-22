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

session_data = {"username" : False, "password" : False, "session_id" : False}

def main(command):
    log.info("In main function, command is {0}".format(command))
    #Form json request
    log.info("Forming json request")
    username = config.load_config("username")
    session_data["username"] = username
    password = keyring.get_password("WILL", username)
    session_data["password"] = password
    log.info("Starting the session")
    #Start the session
    session_id = webapi.session().start({"username":username,"password":password})
    session_data["session_id"] = session_id
    #Start the nlp parser for the session
    log.info("session_id is {0}".format(session_id))
    log.info("Starting plugin parsing")

@atexit.register
def exit_func():
    #End the session
    logging.info("Ending the session")
    webapi.session().end(session_data)
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