#Builtin imports
import logging
import json
import os

log = logging.getLogger()

session_nums = 0

command_nums = 0

def get_session_id():
    '''Incrementing session ids'''
    global session_nums
    session_nums+=1
    session_str = str(session_nums)
    session_len = len(session_str)
    #Generate a 6 number session id
    for i in range(0, 6-session_len):
        session_str = "0"+session_str
    log.debug("Generated session_id {0}".format(session_str))
    return session_str

def get_command_id(session_id):
    '''Incrementing command ids based on the session_id'''
    global command_nums
    command_nums+=1
    command_id = "{0}_{1}".format(
        session_id, command_nums
    )
    log.debug("Generated command id {0}".format(command_id))
    return command_id

def load_configuration():
    '''Load the will.conf file'''
    if os.path.isfile("will.conf"):
        data_string = open("will.conf").read()
        json_data = json.loads(data_string)
        log.info("Loaded will.conf")
        return json_data
    else:
        log.error("Couldn't find will.conf")

def return_json(response):
    '''Render response as json and return it'''
    #Make sure the needed keys are in the response data
    try:
        assert type(response) == dict
        assert "type" in response.keys()
        assert "data" in response.keys()
        assert "text" in response.keys()
        log.debug("Returning response {0}".format(response))
        return json.dumps(response)
    except AssertionError as e:
        log.error("AssertionError {0}, {1} when trying to render response {2}".format(
            e.message, e.args, response
        ))
        return {
            "type": "error",
            "data": None,
            "text": "Server returned malformed response {0}".format(response)
        }