# Builtin imports
import logging
import datetime
import threading
import uuid

# External imports
import falcon
from wsgiref import simple_server
import bcrypt

# Internal imports
from will.exceptions import *
from will.API import hooks, middleware,v1,router
from will.userspace import sessions
from itsdangerous import Signer, TimestampSigner, BadSignature

log = logging.getLogger()
app = None

configuration_data = None

session_manager = None
graph = None

temp_tokens = {}

# User temporary rel [:AUTHORIZED{"user_token": unsigned_user_token, "scope": scope]
# Scopes (next level includes last level) ["basic" <- "command", <- "settings_read", <- "settings_change"]
# Locked scopes are ["admin"] - for verified W.I.L.L clients that can manage clients and utilize admin features on admin
# Accounts

def api_thread():
    """
    Run this simple debug server if debug is set to true in the configuration data
    
    """
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()

def start(manager_thread):
    """
    Start the api and call the router
    :param manager_thread: 
    :return: 
    """
    global app
    global signer
    global timestampsigner
    global session_mangaer
    global graph
    # Pass the graph object to functions that need it
    sessions.graph = graph
    hooks.graph = graph
    v1.graph = graph
    # Pass the debug bool to middleware
    middleware.debug = configuration_data["debug"]
    v1.session_manager = manager_thread
    session_mangaer = manager_thread
    # Check the relevant configuration data for the API
    try:
        error_cause = "secret-key"
        secret_key = configuration_data["secret-key"]
        assert type(secret_key) == str
        signer = Signer(secret_key)
        timestampsigner = TimestampSigner(secret_key)
        hooks.signer = signer
        v1.signer = signer
        v1.timestampsigner = timestampsigner
        error_cause = "banned-ips"
        assert type(configuration_data["banned-ips"]) in (list, set)
    except (KeyError, AssertionError):
        error_string = "Please ensure that {0} is properly defined in your configuration_file.".format(error_cause)
        log.error(error_string)
        raise ConfigurationError(error_string)
    # Create an app instance and give it instances of the middleware
    app = falcon.API(
        middleware=[
            middleware.MonitoringMiddleware(banned_ips=configuration_data["banned-ips"]),
            middleware.RequireJSON(),
            middleware.JSONTranslator(),
            middleware.AuthTranslator()
        ]
    )
    # Add the routes for each version to the API
    router.process_routes(app)
    return app

def kill():
    """
    Kill the API and all sessions
    
    """
    # Kill the session monitor
    session_manager.running = False
