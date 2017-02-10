#Builtin imports
import logging
import json
import core
import uuid
import time
try:
    import queue as Queue
except ImportError:
    import Queue
import datetime
import string

valid_chars = set(string.ascii_letters+string.digits)
log = logging.getLogger()

session_nums = 0

command_nums = 0

event_types = {
        "notification": "NOT",
        "url": "URL",
        "function": "FUN"
    }

def gen_session(username, client_type, db):
    """
    :param username:
    :param client:
    :return: session_id
    """
    session_id = get_session_id(db)
    # Start monitoring notifications
    # Register a session id
    core.sessions.update({
        session_id: {
            "username": username,
            "commands": Queue.Queue(),
            "created": datetime.datetime.now(),
            "updates": Queue.Queue(),
            "id": session_id,
            "client": client_type
        }
    })
    return session_id




def get_event_uid(type):
    '''
    Get an event uid using the event type
    :param type:
    :return: Event uid string
    '''
    e_type = event_types[type]
    return "{0}:{1}".format(e_type, str(uuid.uuid1()))

def dump_events(events, db):
    """
    Dump events
    :param events:
    :param db:
    """
    #Delete all events from db that should be finished
    events_table = db['events']
    events_table.delete(time < time.time())
    for event in events:
        #Remove one time events that had functions in them
        if event["type"] != "function":
            events_table.upsert(event, ['uid'])

def load_key(key_type, db, load_url=False):
    """
    Load a key from the database and implement the cycler

    :param key_type:
    :param db:
    :param load_url:
    :return api key:
    """
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
    """
    Deprecated and out of use

    :param db:
    """
    vars = db["vars"]
    session_increment = vars.find_one(name="session_incremnet")
    log.debug("Found session increment {0} from server".format(session_increment))
    global session_nums
    session_nums = session_increment

def get_session_id(db):
    """
    Incrementer for session ids
    :param db:
    """
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
    """
    Incrementing command ids based on the session id

    :param session_id:
    :return command_id:
    """
    global command_nums
    command_nums+=1
    command_id = "{0}_{1}".format(
        session_id, command_nums
    )
    log.debug("Generated command id {0}".format(command_id))
    return command_id

def get_user_token(username):
    """
    Get a customized user token to store encrypted in the cookies

    :param username:
    :return user_token:
    """
    user_uid = uuid.uuid3(uuid.NAMESPACE_DNS, str(username))
    gen_uid = uuid.uuid1()
    return str(gen_uid)+":u:"+str(user_uid)

def return_json(response):
    """
    Render a response object as json, assert that it has all the correct keys, and return it

    :param response:
    :return json string:
    """
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


def fold(string, line_length=120, indent=0, indent_first_line=False, _runs=0):
    """Fold a string into multiple Lines.
    Fold function by Max Ertl (https://github.com/Sirs0ri)

    :param string: The string you want to fold.
    :param line_length: The desired max line length (int)
    :param indent: if you want lines to be indented, you can specify the number of
        spaces here
    :param indent_first_line: if this is True, the first line won't be indented.
    :return formatted string:
    """
    if indent > line_length:
        log.debug("The indentation is higher than the desired line-length and will "
              "therefore be ignored.")

    # Set up the actual line length
    if indent_first_line is False and _runs == 0:
        length = line_length
    else:
        length = line_length - indent

    # The actual folding:
    if len(string) < length:
        # no need to fold
        return (string)
    else:
        s = ""
        i = 0
        # Find the last space that would be in the last 12 chars of the new line
        # The text will be folded here, 12 proved to be a good value in my tests
        for c in string[length:length - 12:-1]:
            if c == " ":
                # Space found, fold here and remove the space
                s += string[0:length - i]
                string = string[length + 1 - i:]
                # Fold the rest of the string recursively
                return "{}\n{}{}".format(s, " " * indent,
                                         fold(string, line_length, indent,
                                              indent_first_line, _runs + 1))
            else:
                # Character is not a space, move to the previous one
                i += 1
        # No space found in the last 12 chars of the new line. Use full length
        s += string[0:length]
        string = string[length:]
        return "{}\n{}{}".format(s, " " * indent,
                                 fold(string, line_length, indent,
                                      indent_first_line, _runs + 1))

def check_string(in_str):
    """
    Sanatize data

    :return boolean:
    """
    filters = (
        in_str.strip() and
        all([x in valid_chars for x in in_str])
    )
    return filters