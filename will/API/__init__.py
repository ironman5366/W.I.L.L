# Builtin imports
import logging
import datetime
import threading
import uuid

# External imports
import falcon
from wsgiref import simple_server

# Internal imports
from will.exceptions import *
from will.API import sessions, hooks, middleware
from itsdangerous import Signer, TimestampSigner, BadSignature

log = logging.getLogger()

app = None

configuration_data = None
graph = None

temp_tokens = {}

# TODO: !!! HMAC signed user token is stored in relationship with client!
# User rel [:CLIENT {"user_token": unsigned_user_token, "scope": scope]
# Scopes (next level includes last level) ["basic" <- "command", <- "settings_req", <- "settings_change" <- "admin"]


@falcon.before(hooks.client_auth)
class ConnectUser:
    """
    Connect a user to a client using a temporary user token
    """
    def on_post(self, req, resp):
        doc = req.context["doc"]
        if "auth_token" in doc.keys():
            signed_auth_token = doc["auth_token"]
            if "username" in doc.keys():
                username = doc["username"]
                # Make sure the user exists
                session = graph.session()
                users = session.run("MATCH (u:User {username: {username}}) return (u)",
                                    {"username": username})
                # The user exists
                if users:
                    # Check if an AUTHORIZED relationship exists between the user and the client
                    rels = session.run("MATCH (u:User {username: {username}})"
                                       "MATCH (c:Client {client_id: {client_id}})"
                                       "MATCH (u)-[r:AUTHORIZED]->(c) return(r)",
                                       {"username": username,
                                        "client_id": doc["client_id"]})
                    if rels:
                        # Validation
                        rel = rels[0]
                        #TODO: unsign the id with 300 seconds


                    else:
                        resp.status_code = falcon.HTTP_UNAUTHORIZED
                        resp.context["result"]
                else:
                    resp.status_code = falcon.HTTP_UNAUTHORIZED
                    resp.context["result"] = {
                        "errors":
                            [{
                                "id": "USERNAME_INVALID",
                                "type": "error",
                                "status": resp.status_code,
                                "text": "Couldn't find username {0}".format(username)
                            }]
                    }
                session.close()
            else:
                resp.status_code = falcon.HTTP_UNAUTHORIZED
                resp.context["result"] = {
                    "errors":
                        [{
                            "id": "USERNAME_NOT_FOUND",
                            "type": "error",
                            "status": resp.status_code,
                            "text": "A valid username must be submitted with this this request"
                        }]
                }
        else:
            resp.status_code = falcon.HTTP_UNAUTHORIZED
            resp.context["result"] = {
                "errors":
                    [{
                        "id": "AUTH_TOKEN_NOT_FOUND",
                        "type": "error",
                        "status": resp.status_code,
                        "text": "A signed and recent authorization token must be submitted along with this request."
                    }]
            }

@falcon.before(hooks.user_auth)
class GiveUserToken:
    """
    Grant a temporary access token to take back to a client
    """
    def on_post(self, req, resp):
        """
        Generate a user token of sufficient randomness using uuid, sign it, and return it
        
        """
        doc = req.context["doc"]
        # I can be sure that username already exists thanks to the pre request hook
        username = doc["username"]
        if "client_id" in doc.keys():
            client_id = doc["client_id"]
            # Check that there's a scope object in the request and check it against a list of allowed scopes
            if "scope" in doc.keys():
                scope = doc["scope"]
                # Assert that the client and user both exist
                session = graph.session()
                clients = session.run("MATCH (c:Client {client_id: {client_id}}) return (c)")
                if clients:
                    # Use uuid4 for a random id.
                    unsigned_id = uuid.uuid4()
                    # Sign the id with a timestamp. When checking the key we'll check for a max age of 5 minutes
                    signed_id = timestampsigner.sign(unsigned_id)
                    # Put the unsigned id and the scope in the database connected to the user
                    # Once the client resubmits the access token, the AUTHORIZED relationship will be destroyed and
                    # Replaced with a permanent USED one
                    # TODO: do this in a transaction
                    session.run("MATCH (u:User {username: {username}})"
                                "MATCH (c:Client {client_id: {client_id}})"
                                "CREATE (u)-[:AUTHORIZED {scope: {scope}, authorization_token: {auth_token}}]->(c)",
                                {
                                    "username": username,
                                    "client_id": client_id,
                                    "scope": scope,
                                    "auth_token": unsigned_id
                                }
                            )
                    req.context["result"] = {"data":
                                                 {"id": "USER_AUTHORIZATION_TOKEN",
                                                  "type": "success",
                                                  "token": signed_id}}
                else:
                    resp.status_code = falcon.HTTP_UNAUTHORIZED
                    req.context["reuslt"] = {"errors":
                                                 [{"id":  "CLIENT_ID_INVALID",
                                                  "type":  "error",
                                                  "status": resp.status_code,
                                                  "text": "Client id {} is invalid.".format(client_id)}]}
                # Regardless of the response, close the session
                session.close()
            else:
                resp.status_code = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {"errors":
                                             [{"id": "SCOPE_NOT_FOUND",
                                              "text": "You must provide a scope with this request",
                                              "status": resp.status_code}]}
        else:
            resp.status_code = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {"errors":
                                        [{"id": "CLIENT_ID_NOT_FOUND",
                                          "status": resp.status_code,
                                          "text": "You must provide a client id with this request"}]}

class StatusCheck:
    def on_get(self, req, resp):
        pass

class GetToken:
    def on_get(self):
        pass
    def on_post(self):
        pass


# Clients have bcrypt protected client secret, unprotected client public, and signed user_key
# After a session is started, all that needs to be passed is a timestamp user token, linked to the authentication
@falcon.before(hooks.client_auth)
class StartSession:
    pass

    def _match_clients(self):
        session = graph.session()
        clients = session.run("MATCH (c:Client) return (c)")
        session.close()
        self._clients = clients
        self._clients_cached = datetime.datetime.now()
        return clients

    def _client_is_valid(self, client_id):
        try:
            unsigned_client_id = signer.unsign(client_id)
            # Search for the client in the database
            # Refresh cached clients list every 5 minutes
            current_time = datetime.datetime.now()
            time_filter = ((current_time - self._clients_cached).total_seconds() >= 600)
            if self._clients and time_filter:
                clients = self._clients
            else:
                clients = self._match_clients()
            return any(unsigned_client_id == client["client_id"] for client in clients)
        except BadSignature:
            return False

    def _token_is_valid(self, client_id, token):
        try:
            # Unsign a token and check if it matches the client_id
            unsigned_client_id = signer.unsign(client_id)
            unsigned_token = signer.unsign(token)
            if unsigned_token in temp_tokens.keys():
                return temp_tokens[token] == unsigned_client_id
            return False
        except BadSignature:
            return False

def api_thread():
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()

def start():
    global app
    global session_monitor
    global signer
    global timestampsigner
    try:
        error_cause = "secret_key"
        secret_key = configuration_data["secret-key"]
        assert type(secret_key) == str
        signer = Signer(secret_key)
        timestampsigner = TimeoutError(secret_key)
        hooks.signer = signer
        error_cause = "banned-ips"
        assert type(configuration_data["banned-ips"]) in (list, set)
    except (KeyError, AssertionError):
        error_string = "Please ensure that {0} is properly defined in your configuration_file.".format(error_cause)
        log.error(error_string)
        raise ConfigurationError(error_string)
    sessions.graph = graph
    hooks.graph = graph
    # Start the session monitor
    session_monitor = sessions.Monitor()
    app = falcon.API(
        middleware=[
            middleware.MonitoringMiddleware(banned_ips=configuration_data["banned-ips"]),
            middleware.RequireJSON(),
            middleware.JSONTranslator()
        ]
    )
    # Start the debug server if applicable
    if configuration_data["debug"]:
        log.debug("Starting the debug server")
        t = threading.Thread(target=api_thread)
        t.start()


# TODO: write content for the API and add /api/v1 mapping
# TODO: add an error handler for HTTP Unauthorized

def kill():
    """
    Kill the API and all sessions
    
    """
    # Kill the session monitor
    session_monitor.running = False
