# Builtin imports
import logging
import datetime

# External imports
import falcon

# Internal imports
from will.exceptions import *
from will.API import sessions, hooks, middleware
from itsdangerous import Signer, BadSignature

log = logging.getLogger()

app = None

configuration_data = None
graph = None

temp_tokens = {}

class StartSession:
    @falcon.before(client_auth)
    def on_post(self, req, resp):
        # Decoded JSON data
        doc = req.context["doc"]


@falcon.before(user_is_admin)
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

class AuthMiddleware:
    _clients = None
    _clients_cached = datetime.datetime.now()

    def process_request(self, req, resp, resource):
        token = req.get_header('Token')
        client_id = req.get_header("Client-Id")
        client_secret = req.get_header("Client-Secret")
        challenges = ['Token type="Fernet"']

        # If they provided a temporary token
        if token:
            if not self._token_is_valid(client_id, token):
                description = "Provided token is invalid or the token or the client id signature did not match"
                raise falcon.HTTP_UNAUTHORIZED("Token invalid",
                                              description,
                                              challenges,
                                              href="http://will.readthedocs.io/auth")
        elif client_id:
            if client_secret:
                pass
                if not self._client_is_valid(client_id):
                    description = "Client id {0} either was not found in the database or had an invalid signature".format(
                        client_id
                    )
                    raise falcon.HTTP_UNAUTHORIZED("Invalid client id",
                                                   description,
                                                   challenges,
                                                   href="http://will.readthedocs.io/auth")
                else:
                    # If they weren't already headed to GetToken, that's where they're headed now.
                    raise falcon.HTTPSeeOther("/api/v1/get_token")
            else:
                return False
        else:
            description = 'Please provide a signed client id as part of the request'
            raise falcon.HTTP_UNAUTHORIZED('Client id required',
                                          description,
                                          challenges,
                                          href='http://will.readthedocs.io/auth')

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





def start():
    global app
    global session_monitor
    global signer
    try:
        error_cause = "secret_key"
        secret_key = configuration_data["secret-key"]
        assert type(secret_key) == str
        signer = Signer(secret_key)
        hooks.signer = signer
        error_cause = "banned_ips"
        assert type(configuration_data["banned_ips"]) in (list, set)
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
            middleware.MonitoringMiddleware(banned_ips=configuration_data["banned_ips"]),
            middleware.RequireJSON(),
            middleware.JSONTranslator()
        ]
    )


# TODO: write content for the API and add /api/v1 mapping
# TODO: add an error handler for HTTP Unauthorized

def kill():
    """
    Kill the API and all sessions
    
    """
    # Kill the session monitor
    session_monitor.running = False
