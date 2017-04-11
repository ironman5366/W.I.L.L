#Basic echo plugin for testing response framework
import logging

from will.core.plugin_handler import subscribe

from will import tools

log = logging.getLogger()

def gen_response(response_value, event):
    return {"text": response_value, "type": "success", "data": {}}

def check_echo(event):
    return event["command"].lower() == "echo"

@subscribe(name="echo", check=check_echo)
def main(event):
    command_id = event["command_id"]
    log.debug("In echo with command id {0}".format(command_id))
    session_id = event["session"]["id"]
    tools.set_response(session_id, command_id, event, gen_response)
    return {"type": "success", "text": "What should I say?", "data": {"response": command_id}}