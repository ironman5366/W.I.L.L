#Basic echo plugin for testing response framework
import logging

from will.core.plugin_handler import *
from will.core import arguments

log = logging.getLogger()

@subscribe
class Echo(Plugin):
    name = "echo"
    arguments = [arguments.CommandObject]

    def check(self, command_obj):
        return command_obj.text.lower() == "echo"

    def exec(self, **kwargs):
        command_obj = kwargs["CommandObject"]
        command_obj.allow_response = True
        return {
            "data":
                {
                    "type": "response",
                    "text": "What should I say?",
                    "id": "ECHO_PLUGIN_RESPONSE"
                }
        }

    def response(self, **kwargs):
        command_obj = kwargs["CommandObject"]
        return {
            "data":
                {
                    "text": command_obj.text,
                    "type": "success",
                    "id": "ECHO_PLUGIN_SUCCESS"
                }
        }