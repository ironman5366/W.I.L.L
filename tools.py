#Builtin imports
import logging
import json
import os
import uuid
import time

log = logging.getLogger()

session_nums = 0

command_nums = 0

event_types = {
        "notification": "NOT",
        "url": "URL",
        "function": "FUN"
    }

def get_event_uid(type):
    '''Get a uid using the session_id and the uid_type'''
    e_type = event_types[type]
    return "{0}:{1}".format(e_type, str(uuid.uuid1()))

def dump_events(events, db):
    #Delete all events from db that should be finished
    events_table = db['events']
    events_table.delete(time < time.time())
    for event in events:
        #Remove one time events that had functions in them
        if event["type"] != "function":
            events_table.upsert(event, ['uid'])

def load_key(key_type, db, load_url=False):
    '''Load and cycle keys from the databse'''
    working_keys = db.query('SELECT * FROM `keys` WHERE type="{0}" and uses <= max_uses'.format(key_type))
    correct_key = sorted(working_keys, key=lambda x: x["num"])[0]
    key_uses = correct_key["uses"]
    key_value = correct_key["value"]
    updated_uses = key_uses+1
    #Assume that keys reset monthly
    db['keys'].update(dict(type=key_type, num=correct_key['num'], uses=updated_uses), ['type', 'num'])
    if load_url:
        return (key_value, correct_key["url"])
    return key_value

def initialize_session_tracking(db):
    '''Set the session increment using the db'''
    vars = db["vars"]
    session_increment = vars.find_one(name="session_incremnet")
    log.debug("Found session increment {0} from server".format(session_increment))
    global session_nums
    session_nums = session_increment

def get_session_id(db):
    '''Incrementing session ids'''
    global session_nums
    session_nums+=1
    session_id = uuid.uuid1()
    session_str = str(session_id)
    log.debug("Generated session_id {0}".format(session_str))
    log.debug("Updating session increment in db")
    data = dict(name="session_id", value=session_nums)
    db['vars'].update(data, ['name'])
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

def get_user_token(username):
    user_uid = uuid.uuid3(uuid.NAMESPACE_DNS, str(username))
    gen_uid = uuid.uuid1()
    return str(gen_uid)+":u:"+str(user_uid)

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