# 3rd party libs
import requests
import keyring
from pydispatch import dispatcher

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
def main(command):
    log.info("In main function, command is {0}".format(command))
    if isinstance(command,dict):
        return_type = command["return_type"]
        return_action = command["return_action"]
        return_args = command["return_args"]
        if return_type.lower() == "python":
            try:
                return_module = command["return_module"]
                module_import = __import__("{0}.{1}".format(return_module,return_action))
                if return_args:
                    dispatcher.send(module_import, dispatcher.Any, return_args)
                else:
                    dispatcher.send(module_import,dispatcher.Any)
            except Exception as python_exception:
                error_string = "Error {0},{1} occurred while trying to run {2} with args {3}".format(python_exception.message, python_exception.args, return_action, str(return_args))
                log.info(error_string)
                return error_string
        elif return_type.lower() == "url":
            payload = {}
            if return_args:
                if isinstance(return_args, dict):
                    payload.update(return_args)
                else:
                    log.info("Error, return_type was url but return_args wasn't a dict and wasn't none. It was {0}".format(str(type(return_args))))
                    return "Error, return_args needs to be a dict of url parameters or none if return_type is url"
            try:
                url_request = requests.post(url=return_action,data=payload)
                return url_request.text
            except Exception as url_exception:
                error_string = "Error {0},{1} occurred while trying to fetch url {2} with data {3}".format(url_exception.message,url_exception.args,return_action,str(payload))
                log.info(error_string)
                return error_string
    log.info("Starting plugin parsing")
    plugin_command = plugins.Command(command)
    answer = plugin_command.dispatch_event()
    log.info("Answer is {0}".format(str(answer)))
    answer = answer[0]
    response = {
        "return_type" : None,
        "return_action" : None,
        "text" : None,
    }
    if not isinstance(answer, str):
        log.info("Answer is not a string")
        log.info("Answer is {0} and answer type is {1}".format(str(answer),str(type(answer))))
        if isinstance(answer, dict):
            return_type = answer["return_type"]
            return_action = answer["return_action"]
            query = answer["query"]
            response.update({"return_type":return_type,"text":query,"return_action":return_action})
    else:
        log.info("Answer is a string")
        response.update({"return_type":"answer","text":answer})
        log.info("response is {0}".format(response))
    log.info("Response data is {0}".format(str(response)))
    response_json = json.dumps(response)
    return response_json

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