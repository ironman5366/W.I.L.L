# -*- coding: utf-8 -*-
import core
from flask import Blueprint, render_template, redirect, request, session, make_response, Response, stream_with_context
import bcrypt
import logging
import threading
import time
import tools
import requests

log = logging.getLogger()

db = None
start_time = None
configuration_data = None
socketio = None

web = Blueprint('web', __name__, template_folder='templates')

@web.route("/signup")
def signup():
    """
    Render signup template
    :return:
    """
    log.info(":WEB:/signup")
    return render_template("signup.html")


def update_loop(session_id, sid):
    """
    :param session_id: W.I.L.L session id
    :param sid: Flask session id
    Update thread that will emit socket.io updates to the user while they're connected

    :return:
    """
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


def disconnect_session():
    """
    :param session_id:
    End the webapp session and the update thread on the users disconnect from the page
    :return:
    """
    log.info(":SOCKET:disconnect")
    session_id = session["session_id"]
    if session_id in core.sessions.keys():
        log.info(":{0}:Session disconnected".format(session_id))
        #del core.sessions[session_id]
    else:
        log.debug(":{0}:Session id wasn't found in core.sessions".format(session_id))

@web.route("/settings", methods=["GET"])
def settings_page():
    """
    Render the settings template
    :return:
    """
    log.info(":WEB:/settings")
    if "username" in session.keys():
        if "logged-in" in session.keys():
            if session["logged-in"]:
                session["user"] = db["users"].find_one(username=session["username"])
                if session["user"]:
                    return render_template("settings.html")
    return redirect("/")

def get_updates(data):
    """
    :param data: socket.io data about the update thread:
    Authenticate and start the update thread
    :return:
    """
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

@web.route("/login", methods=["POST"])
def login():
    """
    :param username:
    :param password:
    :return Login data:
    """
    response = {"type": None, "text": None, "data": {}}
    try:
        username = str(request.form["username"])
        password = request.form["password"]
        if all(tools.check_string(x) for x in [username, password]):
            user_table = db["users"].find_one(username=username)
            db_hash = user_table["password"]
            if bcrypt.checkpw(password.encode('utf8'), db_hash.encode('utf8')):
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
        else:
            response["type"] = "error"
            response["text"] = "Invalid input, allowed characters are {0}".format(tools.valid_chars)
    except KeyError:
        response["type"] = "error"
        response["text"] = "Couldn't find username and password in request data"
    resp = make_response(redirect("/"))
    if response["type"] == "success":
        log.info(":{0}:Setting cookies for username and user token".format(username))
        session["username"] = username
        session["user_token"] = response["data"]["user_token"]
    return resp

@web.route("/", methods=["GET", "POST"])
def main():
    """
    Render the webapp index.html template
    :return index template:
    """
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
    if configuration_data["debug"]:
        session["debug_http"] = True
    session["first-command"] = True
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
                if "session_id" in session.keys() and session["session_id"] in core.sessions.keys():
                    session_id = session["session_id"]
                    if session_id in core.commands.keys():
                        session_commands = core.commands[session_id]
                        log.debug(":{1}:Session already logged in, setting session_commands to {0}".format(
                            session_commands, session_id
                        ))
                        session["commands"] = session_commands
                else:
                    session["first-command"] = True
                    session_id = tools.gen_session(username, "WEB", db)
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

@web.route('/admin/<path>', methods=["GET"])
def report(path):
    """
    Render template for admin-only reporting page or bounce a non admin user back to /
    :param session:
    :return report template:
    """
    log.info(":WEB:/admin/{0}".format(path))
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
                if path == "report":
                    return render_template('report.html')
                elif path == "logging":
                    if "log_proxy" in configuration_data.keys():
                        req = requests.get(configuration_data["log_proxy"], stream=True)
                        return Response(stream_with_context(req.iter_content()), content_type=req.headers['content-type'])
                    else:
                        return redirect("/")
                elif path == "db":
                    if "db_proxy" in configuration_data.keys():
                        req = requests.get(configuration_data["db_proxy"], stream=True)
                        return Response(stream_with_context(req.iter_content()),
                                        content_type=req.headers['content-type'])
                else:
                    return redirect("/")
    return redirect("/")