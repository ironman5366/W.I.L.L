#Internal imports
import config
import log
import global_vars

#Builtin imports
import time

#External imports
from pydispatch import dispatcher

def parse_main(command):
    pass

def command_thread():
    parsing_status = global_vars.STATUS["PARSING"]
    if parsing_status:
        command = global_vars.COMMANDS.get()
        log.info("Parsing command {0} in command thread".format(command))
        assert type(command) == dict
        command_uid = command.keys()[0]
        command_text = command.values()[0]["text"]
        log.info("Command text is {0}".format(command_text))
        log.info("Feeding command into parser")
        command_response = parse_main(command)
        log.info("Command response is {0}".format(command_response)
        global_vars.PARSED.update({command_uid:{command_response:command}})
        log.info("Updated global parsed variable")
        command_thread()

    else:
        log.info("In command thread, parsing status is false")
        if global_vars.STATUS["ACTIVE"]:
            log.info("Parsing is false, but global_vars says W.I.L.L is still active. Sleeping")
            time.sleep(2)
            command_thread()
