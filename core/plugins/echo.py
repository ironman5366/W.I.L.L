#Basic echo plugin for testing response framework
from core.plugin_handler import subscribe
import core
import logging

log = logging.getLogger()

def gen_response(response_value, event):
    return {"text": response_value, "type": "success", "data": {}}

def check_echo(event):
    return event["command"].lower() == "echo"

@subscribe({"name": "echo", "check": check_echo})
def main(event):
    command_id = event["command_id"]
    log.debug("In echo with command id {0}".format(command_id))
    session_id = event["session"]["id"]
    session_container = core.sessions[session_id]
    commands_container = session_container["commands"]
    for command in commands_container:
        if command["id"] == command_id:
            command_data = command
    command_data.update({
        "event": event,
        "function": gen_response
    })
    return {"type": "success", "text": "What should I say?", "data": {"response": command_id}}