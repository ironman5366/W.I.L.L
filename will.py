# External imports
from flask import Flask
from flask import request
import flask
import dataset
import bcrypt

# Internal imports
import tools
import core

# Builtin imports
import logging
import sys
import datetime
import Queue
import os
import json
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Load the will.conf file
if os.path.isfile("will.conf"):
    data_string = open("will.conf").read()
    json_data = json.loads(data_string)
    configuration_data = json_data
else:
    print "Couldn't find will.conf file, exiting"
    os._exit(1)
logfile = configuration_data["logfile"]
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filemode='w', filename=logfile)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
#log = logging.getLogger()
handler = RotatingFileHandler(logfile, maxBytes=10000000, backupCount=5)
handler.setLevel(logging.DEBUG)
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.addHandler(handler)

app.logger.setLevel(logging.DEBUG)
log = app.logger
db_url = configuration_data["db_url"]
db = dataset.connect(db_url)

@app.route('/api/new_user', methods=["GET","POST"])
def new_user():
    '''Put a new user in the database'''
    response = {"type": None, "data": {}, "text": None}
    try:
        username = request.form["username"]
        log.debug("Username is {0}".format(username))
        password = request.form["password"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        default_plugin = request.form["default_plugin"]
        wolfram_key = request.form["wolfram_key"]
        log.info("Attempting to create new user with username {0} and email {1}".format(username, password))
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
            log.info("Adding a new user {0} to the database".format(username))
            db.begin()
            # Hash the password
            log.info("Hashing password")
            hashed = bcrypt.hashpw(str(password), bcrypt.gensalt())
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
                    "default_plugin": default_plugin,
                    "wolfram_key": wolfram_key
                })
                db.commit()
                response["type"] = "success"
                response["text"]  = "Thank you {0}, you are now registered for W.I.L.L".format(first_name)
            except:
                db.rollback()

    except KeyError:
        log.error("Needed data not found in new user request")
        response["type"] = "error"
        response["text"] = "Couldn't find required data in request. " \
                           "To create a new user, a username, password, first name, last name, default plugin," \
                           "wolframalpha key, and email is required"
    return tools.return_json(response)


@app.route('/api/start_session', methods=["GET","POST"])
def start_session():
    '''Generate a session id and start a new session'''
    # Check the information that the user has submitted
    response = {"type": None, "data": {}, "text": None}
    try:
        username = request.form["username"]
        password = request.form["password"]
        log.info("Checking password for username {0}".format(username))
        users = db["users"]
        user_data = users.find_one(username=username)
        if user_data:
            # Check the password
            db_hash = user_data["password"]
            log.info("Db hash is {0}".format(db_hash))
            user_auth = bcrypt.checkpw(str(password), db_hash)
            if user_auth:
                # Authentication was successful, give the user a session id
                log.info("Authentication successful for user {0}".format(username))
                session_id = tools.get_session_id(db)
                # Register a session id

                core.sessions.update({
                    session_id: {
                        "username": username,
                        "commands": Queue.Queue(),
                        "created": datetime.datetime.now(),
                        "updates": Queue.Queue(),
                        "id": session_id
                    }
                })
                # Return the session id to the user
                response["type"] = "success"
                response["text"] = "Authentication successful"
                response["data"].update({"session_id": session_id})
        else:
            response["type"] = "error"
            response["text"] = "Couldn't find user with username {0}".format(username)
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find username and password in request data"
    # Render the response as json
    return tools.return_json(response)


@app.route('/api/end_session', methods=["GET", "POST"])
def end_session():
    '''End the users session'''
    response = {"type": None, "data": {}, "text": None}
    try:
        session_id = request.form["session_id"]
        # Check for the session id in the core.sessions dictionary
        if session_id in core.sessions.keys():
            log.info("Ending session {0}".format(session_id))
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


@app.route("/api/get_updates", methods=["GET", "POST"])
def get_updates():
    '''Get the updates for the user'''
    response = {"type": None, "data": {}, "text": None}
    try:
        session_id = request.form["session_id"]
        if session_id in core.sessions.keys():
            session_data = core.sessions[session_id]
            # Get data from the updates queue and put it into the response
            while not session_data["updates"].empty():
                update = session_data["updates"].get()
                log.debug("Found update object {0}".format(update))
                update_id = update["id"]
                response["data"].update({
                    update_id: update
                })
            response["type"] = "success"
            response["text"] = "Fetched updates"
        else:
            response["type"] = "error"
            response["text"] = "Session id {0} wasn't found in core.sessions".format(session_id)
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find session id in request data"
    return tools.return_json(response)


@app.route('/api/command', methods=["GET", "POST"])
def command():
    '''Take command and add it to the processing queue'''
    response = {"type": None, "data": {}, "text": None}
    try:
        command = request.form["command"]
        session_id = request.form["session_id"]
        log.debug("Processing command {0} and session id {1}".format(command, session_id))
        if session_id in core.sessions.keys():
            # Add the command to the core.sessions command queue
            session_data = core.sessions[session_id]
            log.info("Adding command {0} to the command queue for session {1}".format(command, session_id))
            command_id = tools.get_command_id(session_id)
            command_data = {
                "id": command_id,
                "command": command
            }
            session_data["commands"].put(command_data)
            response["type"] = "success"
            response["text"] = "Command submitted"
            response["data"].update(dict(command_id=command_id))
        else:
            response["type"] = "error"
            response["text"] = "Invalid session id"
    except KeyError:
        log.info("Couldn't find session id and command in request data")
        response["type"] = "error"
        response["text"] = "Couldn't find session id and command in request data"
    return tools.return_json(response)

def start():
    log.info("Starting W.I.L.L")
    log.info("Loaded configuration file and started logging")
    log.info("Connecting to database")
    log.info("Starting W.I.L.L core")
    core.initialize(db)
    log.info("Starting sessions parsing thread")
    core.sessions_monitor(db)
    log.info("Connected to database, running server")
    #app.run(debug=configuration_data["debug"])
    #host="0.0.0.0", port=80,

if __name__ == "__main__":
    start()
    app.run()