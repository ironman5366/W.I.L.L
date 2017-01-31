# External imports
from flask import Flask, session, send_from_directory
from flask import request
from flask import render_template
from flask_socketio import SocketIO
from flask_socketio import join_room, leave_room
from flask import redirect
from flask import make_response
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
import time
import threading
import time
import datetime
import atexit
import signal

now = datetime.datetime.now()

app = Flask(__name__)

# Load the will.conf file
if os.path.isfile("will.conf"):
    data_string = open("will.conf").read()
    json_data = json.loads(data_string)
    configuration_data = json_data
else:
    print ("Couldn't find will.conf file, exiting")
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
app.secret_key = configuration_data["secret_key"]
log = app.logger
db_url = configuration_data["db_url"]
db = dataset.connect(db_url)
core.db = db

socketio = SocketIO(app)

gmtime = time.gmtime()

start_time = "{0}:{1} UTC {2}".format(gmtime.tm_hour, gmtime.tm_min, now.strftime("%m/%d/%Y"))

@atexit.register
def dump_events(*args):
    log.info(":SYS:Dumping events")
    for event in core.events:
        if event["type"] != "function":
            log.debug(":SYS:Dumping event {0}".format(event))
            db["events"].upsert(event, ['uid'])

signal.signal(signal.SIGTERM, dump_events)


@app.route('/api/new_user', methods=["GET","POST"])
def new_user():
    '''Put a new user in the database'''
    log.info(":API:/api/new_user")
    response = {"type": None, "data": {}, "text": None}
    try:
        username = request.form["username"]
        log.debug("Username is {0}".format(username))
        password = request.form["password"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        city = request.form["city"]
        country = request.form["country"]
        state = request.form["state"]
        log.debug("Attempting to create new user with username {0} and email {1}".format(username, password))
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

    except KeyError:
        log.error("Needed data not found in new user request")
        response["type"] = "error"
        response["text"] = "Couldn't find required data in request. " \
                           "To create a new user, a username, password, first name, last name," \
                           "and email is required"
    return tools.return_json(response)

@app.route("/signup")
def signup():
    log.info(":API:/api/signup")
    return render_template("signup.html")

def gen_session(username):
    session_id = tools.get_session_id(db)
    # Start monitoring notifications
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
    return session_id

@app.route('/api/start_session', methods=["GET","POST"])
def start_session():
    '''Generate a session id and start a new session'''
    log.info(":API:/api/start_session")
    # Check the information that the user has submitted
    response = {"type": None, "data": {}, "text": None}
    try:
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
        elif request.method == "GET":
            username = request.args.get("username", "")
            password = request.args.get("password", "")
            if not (username and password):
                raise KeyError()
        log.info(":{0}:Checking password".format(username))
        users = db["users"]
        user_data = users.find_one(username=username)
        if user_data:
            user_data = db["users"].find_one(username=username)
            # Check the password
            db_hash = user_data["password"]
            user_auth = bcrypt.checkpw(str(password), db_hash)
            if user_auth:
                log.info(":{0}:Authentication successful".format(username))
                # Return the session id to the user
                session_id = gen_session(username)
                if session_id:
                    response["type"] = "success"
                    response["text"] = "Authentication successful"
                    response["data"].update({"session_id": session_id})
                else:
                    response["type"] = "error"
                    response["text"] = "Invalud username/password"
        else:
            response["type"] = "error"
            response["text"] = "Couldn't find user with username {0}".format(username)
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

@app.route('/api/check_session', methods=["GET", "POST"])
def check_session():
    log.info(":API:/api/check_session")
    response = {"type": None, "text": None, "data": {}}
    try:
        session_id = request.form["session_id"]
        session_valid = (session_id in core.sessions.keys())
        response["data"].update({"valid": session_valid})
        response["type"] = "success"
        if session_valid:
            response["text"] = "Session id {0} is valid".format(session_id)
        else:
            response["text"] = "Session id {0} is invalid".format(session_id)
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find session_id in request data"
        response["data"].update({"valid": False})
    return tools.return_json(response)

@app.route('/api/end_session', methods=["GET", "POST"])
def end_session():
    '''End the users session'''
    log.info(":API:/api/end_session")
    response = {"type": None, "data": {}, "text": None}
    try:
        session_id = request.form["session_id"]
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

def update_loop(session_id, sid):
    while session_id in core.sessions.keys():
        try:
            session_data = core.sessions[session_id]
        except KeyError:
            #Session ended while loop was sleeping
            break
        session_updates = session_data["updates"]
        while not session_updates.empty():
            update = session_updates.get()
            log.debug("Pushing update {0}".format(update))
            socketio.emit('update', update, room=sid)
        time.sleep(1)
    log.info(":{0}:Ending updates for finished session".format(session_id))

@socketio.on('disconnect')
def disconnect_session():
    '''End the webapp session and the update thread on disconnect'''
    log.info(":SOCKET:disconnect")
    session_id = session["session_id"]
    if session_id in core.sessions.keys():
        log.info(":{0}:Ending session".format(session_id))
        del core.sessions[session_id]
    else:
        log.debug(":{0}:Session id wasn't found in core.sessions".format(session_id))

@app.route("/api/settings", methods=["POST"])
def settings():
    log.info(":API:/api/settings")
    response = {"type": None, "text": None, "data": {}}
    if "username" in request.form.keys() and "password" in request.form.keys():
        username = request.form["username"]
        password = request.form["password"]
        user_table = db["users"].find_one(username=username)
        if user_table:
            db_hash = user_table["password"]
            if bcrypt.checkpw(str(password), db_hash):
                #TODO: write a framework that allowc ahgning of notifications
                immutable_settings = ["username", "admin", "id", "user_token", "notifications", "password"]
                db.begin()
                log.info(":{0}:Changing settings for user".format(username))
                try:
                    for setting in request.form.keys():
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
        response["text"] = "Couldn't find username or password in request data"
    return tools.return_json(response)

@app.route("/settings", methods=["GET"])
def settings_page():
    log.info(":WEB:/settings")
    if "username" in session.keys():
        if "logged-in" in session.keys():
            if session["logged-in"]:
                session["user"] = db["users"].find_one(username=session["username"])
                if session["user"]:
                    return render_template("settings.html")
    return redirect("/")

@socketio.on("get_updates")
def get_updates(data):
    '''Websocket thread for getting updates'''
    log.info(":SOCKET:get_updates")
    session_id = data["session_id"]
    if session_id:
        if session_id in core.sessions.keys():
            #If the session id is valid
            log.debug("{1}:Subscribing client {0} to updates for session_id".format(
                request.environ["REMOTE_ADDR"], session_id
            ))
            #Keep running this loop while the session is active
            log.info(":{0}:Starting update loop".format(session_id))
            update_thread = threading.Thread(target=update_loop, args=(session_id, request.sid))
            update_thread.start()
        else:
            log.debug("Session id {0} is invalid".format(session_id))
            socketio.emit("update", {"value": "Error, invalid session id"})
    else:
        socketio.emit("update", {"value": "Error, couldn't find session id in update request"})

@app.route("/login", methods=["POST"])
def login():
    response = {"type": None, "text": None, "data": {}}
    try:
        username = str(request.form["username"])
        password = request.form["password"]
        user_table = db["users"].find_one(username=username)
        db_hash = user_table["password"]
        if bcrypt.checkpw(str(password), db_hash):
            log.info(":{0}:Logged in user".format(username))
            #Generate user token
            session["logged-in"] = True
            session["username"] = username
            user_token = tools.get_user_token(username)
            db['users'].upsert({"username":username, "user_token":user_token}, ['username'])
            response["type"] = "success"
            response["text"] = "Authentication successful"
            response["data"].update({"user_token":user_token})
        else:
            response["type"] = "error"
            response["text"] = "Invalid username/password"
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find username and password in request data"
    resp = make_response(redirect("/"))
    if response["type"] == "success":
        log.info(":{0}:Setting cookies for username and user token".format(username))
        session["username"] = username
        session["user_token"] = response["data"]["user_token"]
    return resp

@app.route("/", methods=["GET", "POST"])
def main():
    log.info(":WEB:/")
    if "username" in session.keys():
        username = session["username"]
    else:
        username = None
    if username:
        log.info(":{0}:Found username cookies".format(username))
    log.debug("Setting session data")
    if "logged-in" not in session.keys():
        session["logged-in"] = False
    session["welcome-message"] = "Welcome to W.I.L.L"
    if username:
        user_table = db["users"].find_one(username=username)
        if "user_token" in user_table.keys() and "user_token" in session.keys():
            user_token = session["user_token"]
            if user_table["user_token"] == user_token:
                log.info(":{0}:User authenticated via user_token in cookies".format(username))
                new_token = tools.get_user_token(username)
                db["users"].upsert({"username":username, "user_token": new_token}, ['username'])
                session["logged-in"] = True
                user_first_name = user_table["first_name"]
                session["welcome-message"] = "Welcome back {0}".format(user_first_name)
                session_id = gen_session(username)
                session["session_id"] = session_id
                session["user_token"] = new_token
                log.info(":{0}:Generated session id for user {1}".format(
                    session_id, username
                ))
                resp = make_response(render_template('index.html'))
                return resp
            else:
                log.debug("User tokens don't match.\n{0}\n{1}".format(request.cookies.get("user_token"),
                                                                     db["users"].find_one(username=username)["user_token"]))
                session["logged-in"] = False
        else:
            log.debug("Couldn't find user token in cookies")
            session["logged-in"] = False
    else:
        log.debug("Couldn't find username in cookies")
        session["logged-in"] = False
    #If the cookies aren't found
    return render_template('index.html')

@app.route('/report', methods=["GET"])
def report():
    log.info(":WEB:/report")
    if "username" in session.keys() and "logged-in" in session.keys() and session["logged-in"]:
        user_table = db["users"].find_one(username=session["username"])
        if user_table:
            if user_table["admin"]:
                #Get the session_data
                session["commands-processed"] = core.processed_commands
                time_str = start_time
                session["start-time"] = start_time
                users_online = 0
                users_processed = []
                for session_id in core.sessions:
                    session_data = core.sessions[session_id]
                    session_user = session_data["username"]
                    if session_user not in users_processed:
                        users_processed.append(str(session_user))
                        users_online+=1
                session["users-online"] = users_online
                session["active-sessions"] = len(core.sessions)
                session["errors"] = core.error_num
                session["success"] = core.success_num
                session["users-list"] = users_processed
                return render_template('report.html')
    return redirect("/")

@app.route('/command', methods=["GET", "POST"])
def command():
    log.info(":WEB:command")
    username = request.form["username"]
    password = request.form["password"]
    user_table = db["users"].find_one(username=username)
    db_hash = user_table["password"]
    if bcrypt.checkpw(str(password), db_hash):
        log.info(":{0}:Starting session for user".format(username))
        session_data = json.loads(start_session())
        session_id = session_data["data"]["session_id"]
        session.update({"session_id":session_id})
        return render_template("command.html")
    else:
        return "Invalid password"
@app.route('/api/command', methods=["GET", "POST"])
def process_command():
    '''Take command and add it to the processing queue'''
    log.info(":API:/api/command")
    response = {"type": None, "data": {}, "text": None}
    try:
        command = request.form["command"]
        session_id = request.form["session_id"]
        log.debug(":{1}:Processing command {0}".format(command, session_id))
        if session_id in core.sessions.keys():
            # Add the command to the core.sessions command queue
            session_data = core.sessions[session_id]
            log.info(":{1}:Adding command {0} to the command queue".format(command, session_id))
            command_id = tools.get_command_id(session_id)
            command_data = {
                "id": command_id,
                "command": command
            }
            command_response = core.sessions_monitor.command(
                command_data, core.sessions[session_id], db, add_to_updates_queue=False
            )
            session_data["commands"].put(command_data)
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

@app.route('/api/get_sessions', methods=["GET", "POST"])
def get_sessions():
    '''Return a list of open sessions for the user'''
    log.info(":API:/api/get_sessions")
    response = {"type": None, "data": {}, "text": None}
    sessions = core.sessions
    try:
        username = request.form["username"]
        password = request.form["password"]
        db_hash = db['users'].find_one(username=username)["password"]
        user_auth = bcrypt.checkpw(str(password), db_hash)
        if user_auth:
            response["data"].update({"sessions":[]})
            for session in sessions:
                if sessions[session]["username"] == username:
                    response["data"]["sessions"].append(session)
            response["type"] = "success"
            response["text"] = "Fetched active sessions"
        else:
            response["type"] = "error"
            response["text"] = "Invalid username/password combination"
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find username and password in request"
    return tools.return_json(response)

def start():
    log.info(":SYS:Starting W.I.L.L")
    log.info(":SYS:Loaded configuration file and started logging")
    log.info(":SYS:Connecting to database")
    log.info(":SYS:Starting W.I.L.L core")
    core.initialize(db)
    log.info(":SYS:Starting sessions parsing thread")
    core.sessions_monitor(db)
    log.info(":SYS:Connected to database, running server")

if __name__ == "__main__":
    start()
    log.info(":SYS:Running app")
    socketio.run(
        app, host=configuration_data["host"], port=configuration_data["port"], debug=configuration_data["debug"])