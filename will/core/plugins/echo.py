#Basic echo plugin for testing response framework
import logging

from will.core.plugin_handler import *
from will.core import arguments
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

@subscribe
class EchoResponse(ResponsePlugin):

    name = "echoresponse"
    arguments = [arguments.CommandText]

    def exec(self, **kwargs):
        command = kwargs["CommandText"]
        return {
            "data":
                {
                    "type": "success",
                    "text": command,
                    "id": "ECHO_SUCCESSFUL"
                }
        }

# TODO: specific response objects

@subscribe
class Echo(Plugin):
    name = "echo"
    arguments = [arguments.CommandObject, arguments.ResponseFunction]

    def check(self, command_obj):
        return command_obj.text.lower() == "echo"

    def exec(self, **kwargs):
        response_setter = kwargs["ResponseFunction"]
        command_obj = kwargs["CommandObj"]
        response_setter(command_obj.uid, EchoResponse())
        response_setter()