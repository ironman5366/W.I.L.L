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

#TODO: seperate the server and client code and add an api to communicate between the two

def main(command):
    logging.info("In main function, command is {0}".format(command))
    #Form json request
    logging.info("Forming json request")
    username = config.load_config("username")
    password = keyring.get_password("WILL", username)

    request = {
        "command" : command,
        "username" : username,
        "password" : password,
    }



@atexit.register
def exit_func():
    log.info("Keyboard Interupt detected.  Shutting down.")
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
    plugins.load("plugins/")
    log.info("Debug value is {0}".format(debugval))