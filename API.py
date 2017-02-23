from flask import Blueprint, request, session, redirect, render_template
import core
import tools
import logging
import bcrypt
import json
import traceback
import sys
try:
    import queue as Queue
except ImportError:
    import Queue

db = None
configuration_data = None

log = logging.getLogger()

api = Blueprint('api', __name__, template_folder='templates')

@api.route('/new_user', methods=["GET","POST"])
def new_user():
    '''
    Create new user in the database

    :param: username
    :param: password
    :param: first_name
    :param: email
    :param: city
    :param: country
    :param: state
    '''
    log.info(":API:/api/new_user")
    response = {"type": None, "data": {}, "text": None}
    try:
        if request.is_json:
            request_data = request.get_json()
        else:
            request_data = request.form
        username = str(request_data["username"])
        log.debug("Username is {0}".format(username))
        password = str(request_data["password"])
        first_name = str(request_data["first_name"])
        last_name = str(request_data["last_name"])
        email = str(request_data["email"])
        city = str(request_data["city"])
        country = str(request_data["country"])
        state = str(request_data["state"])
        check_list = [username, password, first_name, last_name, email, city, country, state]
        passed = tools.check_string(check_list)
        if passed:
            log.debug("Attempting to create new user with username {0} and email {1}".format(username, email))
            # Check to see if the username exists
            users = db["users"]
            if users.find_one(username=username):
                # If that username is already taken
                taken_message = "Username {0} is already taken".format(username)
                log.debug(taken_message)
                response["type"] = "error"
                response["text"] = taken_message
            else:
                # Add the new user to the database
                log.info(":{0}:Adding a new user to the database".format(username))
                db.begin()
                # Hash the password
                log.debug("Hashing password")
                hashed = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                log.debug("Hashed password is {0}".format(hashed))
                is_admin = username in configuration_data["admins"]
                try:
                    db['users'].insert({
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "password": hashed,
                        "admin": is_admin,
                        "default_plugin": "search",
                        "notifications": json.dumps(["email"]),
                        "ip": request.environ["REMOTE_ADDR"],
                        "news_site": "http://reuters.com",
                        "city": city,
                        "country": country,
                        "state": state,
                        "temp_unit": "fahrenheit"
                    })
                    db.commit()
                    response["type"] = "success"
                    response["text"] = "Thank you {0}, you are now registered for W.I.L.L".format(first_name)
                except:
                    db.rollback()
        else:
            log.warning(":{0}:Failed SQL evaluation".format(username))
            response["type"] = "error"
            response["text"] = "Invalid input, valid chars are {0}".format(tools.valid_chars)

    except KeyError:
        log.error("Needed data not found in new user request")
        response["type"] = "error"
        response["text"] = "Couldn't find required data in request. " \
                           "To create a new user, a username, password, first name, last name," \
                           "and email is required"
    return tools.return_json(response)


@api.route("/settings", methods=["POST"])
def settings():
    """
    :param username:
    :param password:
    :param Optional - setting to be changed:
    Change the users settings

    :return:
    """
    log.info(":API:/api/settings")
    response = {"type": None, "text": None, "data": {}}
    if request.is_json:
        request_data = request.get_json()
    else:
        request_data = request.form
    if "username" in request_data.keys() and "password" in request_data.keys():
        username = request_data["username"]
        password = request_data["password"]
        if tools.check_string(request_data.values()):
            user_table = db["users"].find_one(username=username)
            if user_table:
                db_hash = user_table["password"]
                if bcrypt.checkpw(password.encode('utf8'), db_hash.encode('utf8')):
                    #TODO: write a framework that allows changing of notifications
                    immutable_settings = ["username", "admin", "id", "user_token", "notifications", "password"]
                    db.begin()
                    log.info(":{0}:Changing settings for user".format(username))
                    try:
                        for setting in request_data.keys():
                            if setting not in immutable_settings:
                                db["users"].upsert({"username": username, setting: request.form[setting]}, ['username'])
                        db.commit()
                        response["type"] = "success"
                        response["text"] = "Updated settings"
                    except Exception as db_error:
                        log.debug("Exception {0}, {1} occurred while trying to commit changes to the database".format(
                            db_error.message, db_error.args
                        ))
                        response["type"] = "error"
                        response["text"] = "Error encountered while trying to update db, changes not committed"
                        db.rollback()
            else:
                response["type"] = "error"
                response["text"] = "User {0} doesn't exist".format(username)
        else:
            response["type"] = "error"
            response["text"] = "Invalid input"

    else:
        response["type"] = "error"
        response["text"] = "Couldn't find username or password in request data"
    return tools.return_json(response)

@api.route('/get_sessions', methods=["GET", "POST"])
def get_sessions():
    """
    Return list of active sessions for user
    :param: username
    :param: password
    :return: list of sessions
    """
    log.info(":API:/api/get_sessions")
    response = {"type": None, "data": {}, "text": None}
    sessions = core.sessions
    if request.is_json:
        request_data = request.get_json()
    else:
        request_data = request.form
    try:
        username = request_data["username"]
        password = request_data["password"]
        if tools.check_string(request_data.values()):
            db_hash = db['users'].find_one(username=username)["password"]
            user_auth = bcrypt.checkpw(password.encode('utf8'), db_hash.encode('utf8'))
            if user_auth:
                response["data"].update({"sessions":[]})
                for user_session in sessions:
                    if sessions[user_session]["username"] == username:
                        response["data"]["sessions"].append(session)
                response["type"] = "success"
                response["text"] = "Fetched active sessions"
            else:
                response["type"] = "error"
                response["text"] = "Invalid username/password combination"
        else:
            response["type"] = "error"
            response["text"] = "One of the submitted parameters contained an invalid character. " \
                               "Valid characters are {0}".format(tools.valid_chars)
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find username and password in request"
    return tools.return_json(response)


@api.route('/start_session', methods=["GET","POST"])
def start_session():
    '''
    :param: username
    :param: password
    Generate a session id and start a new session

    :return:
    '''
    log.info(":API:/api/start_session")
    # Check the information that the user has submitted
    response = {"type": None, "data": {}, "text": None}
    if request.is_json:
        request_data = request.get_json()
    else:
        request_data = request.form
    try:
        if request.method == "POST":
            username = request_data["username"]
            password = request_data["password"]
            client = "API-POST"
        elif request.method == "GET":
            username = request.args.get("username", "")
            password = request.args.get("password", "")
            client = "API-GET"
            if not (username and password):
                raise KeyError()
        if tools.check_string([username, password]):
            log.info(":{0}:Checking password".format(username))
            users = db["users"]
            user_data = users.find_one(username=username)
            if user_data:
                user_data = db["users"].find_one(username=username)
                # Check the password
                db_hash = user_data["password"]
                user_auth = bcrypt.checkpw(password.encode('utf8'), db_hash.encode('utf8'))
                if user_auth:
                    log.info(":{0}:Authentication successful".format(username))
                    # Return the session id to the user
                    session_id = tools.gen_session(username, client, db)
                    if session_id:
                        response["type"] = "success"
                        response["text"] = "Authentication successful"
                        response["data"].update({"session_id": session_id})
                    else:
                        response["type"] = "error"
                        response["text"] = "Invalid username/password"
            else:
                response["type"] = "error"
                response["text"] = "Couldn't find user with username {0}".format(username)
        else:
            response["type"] = "error"
            response["text"] = "Invalid input"
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find username and password in request data"
    # Render the response as json
    if request.method == "GET":
        session.update({"session_data": response})
        if response["type"] == "success":
            return redirect("/")
        log.debug("Rendering command template")
        return render_template("command.html")
    else:
        return tools.return_json(response)


@api.route('/end_session', methods=["GET", "POST"])
def end_session():
    """
    End a session

    :param  session_id:
    :return End the session:
    """
    log.info(":API:/api/end_session")
    response = {"type": None, "data": {}, "text": None}
    if request.is_json:
        request_data = request.get_json()
    else:
        request_data = request.form
    try:
        session_id = request_data["session_id"]
        # Check for the session id in the core.sessions dictionary
        if session_id in core.sessions.keys():
            log.info(":{0}:Ending session".format(session_id))
            del core.sessions[session_id]
            response["type"] = "success"
            response["text"] = "Ended session"
        else:
            response["type"] = "error"
            response["text"] = "Session id {0} wasn't found in core.sessions".format(session_id)
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find session id in request data"
    # Render the response as json
    return tools.return_json(response)

@api.route('/check_session', methods=["GET", "POST"])
def check_session():
    """
    Check if a session is valid
    :param: session_id
    :return:
    """
    log.info(":API:/api/check_session")
    response = {"type": None, "text": None, "data": {}}
    if request.is_json:
        request_data = request.get_json()
    else:
        request_data = request.form
    try:
        session_id = request_data["session_id"]
        session_valid = (session_id in core.sessions.keys())
        response["data"].update({"valid": session_valid})
        response["type"] = "success"
        if tools.check_string(session_id):
            if session_valid:
                response["text"] = "Session id {0} is valid".format(session_id)
            else:
                response["text"] = "Session id {0} is invalid".format(session_id)
        else:
            response["type"] = "error"
            response["text"] = "Invalid input"
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find session_id in request data"
        response["data"].update({"valid": False})
    return tools.return_json(response)

@api.route('/respond', methods=["GET", "POST"])
def command_response():
    """
    Api path for responding to a command question
    :param session_id:
    :param command_id:
    :return:
    """
    log.info(":API:/api/respond")
    response = {"type": None, "text": None, "data": {}}
    if request.is_json:
        request_data = request.get_json()
        try:
            log.debug(request_data.keys())
            command_id = request_data["command_id"]
            session_id = request_data["session_id"]
            response_value = request_data["value"]
            #Validate the JSON response object
            if tools.check_string([command_id, session_id]):
                if session_id in core.sessions.keys():
                    session_data = core.sessions[session_id]
                    session_commands = session_data["commands"]
                    response_command = None
                    for command_obj in session_commands:
                        if command_obj["id"] == command_id:
                            response_command = command_obj
                    if response_command:
                        if "function" in command_obj.keys() and "event" in command_obj.keys():
                            response_function = command_obj["function"]
                            log.info(":{0}: Executing response function {1} with response {2}".format(
                                command_id, response_function, response_value
                            ))
                            #Execute the response
                            try:
                                response_result = response_function(response_value, command_obj)
                                log.info(":{0}:Successfully executed response, returning {1}".format(
                                    session_id, tools.fold(response_result)
                                ))
                                response = response_result
                            except Exception:
                                exc_type, exc_value, exc_traceback = sys.exc_info()
                                error_string = repr(traceback.format_exception(exc_type, exc_value,
                                                  exc_traceback))
                                log.error(error_string)
                                username = session_data["username"]
                                user_table = tools.find_one(username=username)
                                if user_table:
                                    response["type"] = "error"
                                    if user_table["admin"]:
                                        response["text"] = error_string
                                    else:
                                        response["text"] = "An error has occurred while trying to fetch a response." \
                                                           "Please contact will@willbeddow.com to report the error and " \
                                                           "get more information"

                                else:
                                    log.error("USER {0} NOT FOUND IN DATABASE. WARNING.".format(username))
                                    response["type"] = "error"
                                    response["text"] = "A database error has occurred. Please contact will@willbeddow.com" \
                                                       "to report the error, along with the circumstances under which it" \
                                                       "occurred."
                        else:
                            response["type"] = "error"
                            response["text"] = "Command {0} didn't register for a response or didn't" \
                                               " register the required data for a response.".format(command_id)
                    else:
                        response["type"] = "error"
                        response["text"] = "Couldn't find a command object in session {0} with command id {1}".format(
                            session_id, command_id
                        )
                else:
                    response["type"] = "error"
                    response["text"] = "Invalid session id {0}".format(session_id)
            else:
                response["type"] = "error"
                response["text"] = "Submitted response data {0} failed string validation. Valid characters are {0}".format(
                    tools.valid_chars
                )
        except KeyError:
            response["type"] = "error"
            response["text"] = "command_id, session_id, and JSON response object required"
    else:
        response["type"] = "error"
        response["text"] = "/api/respond requires a JSON request"
    return tools.return_json(response)

@api.route('/command', methods=["GET", "POST"])
def process_command():
    """
    Api path for processing a command
    :param command:
    :param session_id:
    :return response object:
    """
    log.info(":API:/api/command")
    response = {"type": None, "data": {}, "text": None}
    if request.is_json:
        request_data = request.get_json()
    else:
        request_data = request.form
    try:
        command = request_data["command"]
        session_id = request_data["session_id"]
        log.debug(":{1}:Processing command {0}".format(command, session_id))
        if session_id in core.sessions.keys():
            # Add the command to the core.sessions command queue
            session_data = core.sessions[session_id]
            log.info(":{1}:Adding command {0} to the command queue".format(command, session_id))
            command_data = tools.create_command_obj(session_id, command)
            command_response = core.sessions_monitor.command(
                command_data, core.sessions[session_id], db, add_to_updates_queue=False
            )
            if session_id in core.commands.keys():
                core.commands[session_id].append(command_data)
            else:
                core.commands.update({session_id: [command_data]})
            session_data["commands"].append(command_data)
            core.commands.update(command_data)
            log.info(":{0}:Returning command response {1}".format(session_id, tools.fold(str(command_response))))
            response = command_response
        else:
            log.info(":{0}:Couldn't find session id in sessions".format(session_id))
            response["type"] = "error"
            response["text"] = "Invalid session id"
    except KeyError:
        log.debug("Couldn't find session id and command in request data")
        response["type"] = "error"
        response["text"] = "Couldn't find session id and command in request data"
    return tools.return_json(response)