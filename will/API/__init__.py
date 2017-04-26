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

# Store errors so that an admin can retrieve the data
errors = {}

@falcon.before(hooks.user_is_admin)
class StatusCheck:
    def on_post(self, req, resp):
        """
        Collect data from all the running functions, and return reports
        
        :param req: 
        :param resp: 
        """
        return session_manager.report


@falcon.before(hooks.session_auth)
class Command:
    def on_post(self, req, resp):
        """
        Call a command with the session that was found
        
        :param req: 
        :param resp: 
        
        """
        # The session_auth hook automatically put the instantiated session class in the request context
        session = req.context["session"]
        # Check to make sure that "command" is in the request body
        doc = req.context["doc"]
        if "command" in doc.keys():
            command = doc["command"]
            # Run the command in the sessions command instance
            try:
                # Let the command return the direct result dictionary
                result = session.command(command)
                log.debug("Got result {0} from command {1}".format(
                    result, command
                ))
                req.context["result"] = result
            except Exception as ex:
                exception_type, exception_args = (type(ex).__name__, ex.args)
                command_error_string = "Error of type {error_type} with arguments {error_args} occurred while " \
                                       "running command {command} in session {session_id} owned by user " \
                                       "{username}".format(
                                        error_type=exception_type,
                                        error_args=exception_args,
                                        command=command,
                                        session_id=session.session_id,
                                        username=session.username)
                log.warning(command_error_string)
                resp.status = falcon.HTTP_INTERNAL_SERVER_ERROR
                req.context["result"] = {
                    "errors":
                        [{
                            "type": "error",
                            "id": "COMMAND_ERROR",
                            "status": resp.status,
                            "text": "An internal error occurred while parsing command {0}".format(
                                command
                            )
                        }]
                }
        else:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "status": resp.status,
                        "text": "To use this method you must submit a command parameter in the request",
                        "id": "COMMAND_NOT_FOUND"
                    }]
            }
@falcon.before(hooks.client_is_official)
class CreateClient:
    def on_post(self, req, resp):
        """
        Create a client.
         The hooks before the function makes sure that the client has permission to do this
         Request structure:
         {
            "client_id": "id_of_submitter",
            "client_secret": "signed_relevant_secret_key",
            "data": 
                {  
                    "id": "id of new client",
                    "scope": "scope of new_client"
                }
        }
            
        """
        doc = req.context["doc"]
        # Check for all the required components for creating a new client
        if "data" in doc.keys():
            data = doc["data"]
            # Validate the data inside the request
            required_fields = {
                "id": str,
                "scope": str,
                "webhook": str,
                "provides": list
            }
            error_cause = None
            try:
                for field in required_fields:
                    error_cause = field
                    assert type(data[field]) == required_fields[field]
            except (KeyError, AssertionError):
                log.debug("{0} caused create client request to fail. Request originated from client {1}".format(
                    error_cause, doc["client_id"]
                ))
                resp.status = falcon.HTTP_BAD_REQUEST
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "{0}_INVALID".format(error_cause.upper()),
                            "status":  resp.status,
                            "text": "Please check the {0} field and resubmit. {0} was either missing, or wasn't of "
                                    "required type {1}".format(
                                error_cause, required_fields[error_cause]
                            ),
                            "type": "error"
                        }]
                }
                return
            # Data was validated successfully, fetch it from the document
            id = required_fields["id"]
            scope = required_fields["scope"]
            # Check if the submitted id is already in the database
            session = graph.session()
            matching_clients = session.run("MATCH (c:Client {client_id:{id}})",
                                           {"id": id})
            # If a client with that name already exists:
            if matching_clients:
                resp.status = falcon.HTTP_CONFLICT
                req.context["result"] = {
                    "errors":
                        [{
                            "type": "error",
                            "id": "CLIENT_ID_ALREADY_EXISTS",
                            "status":  resp.status,
                            "text": "A client with client id {0} already exists".format(
                                id
                            )
                        }]
                }
            else:
                # The id is unused
                # Check to see if the scope is valid
                if scope in hooks.scopes.keys():
                    # The highest level that can be automatically created is a level of 2, settings_change
                    scope_level = hooks.scopes[scope]
                    # The client requested a valid scope that they're authorized to use
                    # A scope of level 2 is settings_change which is the highest scope that non official
                    # Clients are allowed to use
                    if scope_level >= 2:
                        log.debug("Adding client {0} with scope {1} to database, and generating secret key".format(
                            id, scope
                        ))
                        # Generate the key. Nobody will see the unsigned unhashed version
                        raw_secret_key = uuid.uuid4()
                        # Hash the key. This version will be put in the database
                        hashed_secret_key = bcrypt.hashpw(raw_secret_key, bcrypt.gensalt())
                        # Sign the key. This version will be returned to the user
                        signed_secret_key = signer.sign(raw_secret_key)
                        # Put the client in the database
                        session.run("CREATE (c:Client "
                                    "{client_id: {client_id}, "
                                    "official: false, "
                                    "secret_key: {hashed_secret}, "
                                    "scope: {scope}",
                                    {
                                        "client_id": id,
                                        "hashed_secret": hashed_secret_key,
                                        "scope": scope
                                    })
                        log.debug("Created client {} in database".format(id))
                        # Return the data to the user
                        req.context["result"] = {
                            "data":{
                                "id": "CLIENT_CREATED",
                                "status": resp.status,
                                "type": "success",
                                "secret_key": signed_secret_key,
                                "client_id": id,
                                "scope": scope
                            }
                        }

                    else:
                        resp.status = falcon.HTTP_UNAUTHORIZED
                        req.context["result"] = {
                            "errors":
                                [{
                                    "id": "SCOPE_NOT_AUTHORIZED",
                                    "status": resp.status,
                                    "type": "error",
                                    "text": "The client does not have authorization to create a new client with a "
                                            "scope of {0}".format(scope)
                                }]
                        }
                else:
                    resp.status = falcon.HTTP_BAD_REQUEST
                    req.context["result"] = {
                        "errors":
                            [{
                                "id": "SCOPE_INVALID",
                                "status": resp.status,
                                "type": "error",
                                "text": "Unrecognized scope {0}".format(scope)
                            }]
                    }
            # No matter what, close the session
            session.close()
        else:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "id": "DATA_NOT_FOUND",
                        "status": resp.status,
                        "type": "error",
                        "text": '"data" key with client information not found'
                    }]
            }

@falcon.before(hooks.client_user_auth)
class StartSession:
    def on_post(self, req, resp):
        doc = req.context["doc"]
        username = doc["username"]
        client_id = doc["client_id"]
        user_session = sessions.Session(username, client_id)
        # Sign the session id from the instantiated class
        session_id = user_session.session_id
        signed_session_id = signer.sign(session_id)
        success_string = "Successfully started session for user {0}".format(
            username
        )
        log.debug(success_string)
        req.context["result"] = {
            "data":
                {
                    "type": "success",
                    "id": "SESSION_ID",
                    "session_id": signed_session_id,
                    "text": success_string
                }
        }


def api_thread():
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
    # Pass the graph object to functions that need it
    sessions.graph = graph
    hooks.graph = graph
    v1.graph = graph
    # Pass the debug bool to middleware
    middleware.debug = configuration_data["debug"]
    v1.session_manager = manager_thread
    # Check the relevant configuration data for the API
    try:
        error_cause = "secret_key"
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
    # Start the debug server if applicable
    if configuration_data["debug"]:
        log.debug("Starting the debug server")
        t = threading.Thread(target=api_thread)
        t.start()

def kill():
    """
    Kill the API and all sessions
    
    """
    # Kill the session monitor
    session_monitor.running = False
