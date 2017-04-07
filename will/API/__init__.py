# Builtin imports
import json
import logging
import datetime

# External  imports
import falcon

# Internal imports
from will.exceptions import *
from will.API import sessions
from itsdangerous import Signer, BadSignature

log = logging.getLogger()

app = falcon.API()

configuration_data = None
graph = None

temp_tokens = {}


def user_is_admin(req, resp, resource, params):
    # TODO
    return True


@falcon.before(user_is_admin)
class StatusCheck:
    def on_get(self, req, resp):
        pass

class GetToken:
    pass

class AuthMiddleware:
    _clients = None
    _clients_cached = datetime.datetime.now()

    def process_request(self, req, resp, resource):
        token = req.get_header('Token')
        client_id = req.get_header("Client-Id")

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
            unsigned_client_id = signer.unsign(client_id)
            unsigned_token = signer.unsign(token)
            if unsigned_token in temp_tokens.keys():
                return temp_tokens[token] == unsigned_client_id
            return False
        except BadSignature:
            return False


class SessionMiddleWare:
    def process_request(self, req, resp):
        pass


class RequireJSON(object):
    def process_request(self, req, resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                'This API only supports responses encoded as JSON.',
                href='http://docs.examples.com/api/json')

        if req.method in ('POST', 'PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType(
                    'This API only supports requests encoded as JSON.',
                    href='http://docs.examples.com/api/json')


class JSONTranslator(object):
    def process_request(self, req, resp):
        # req.stream corresponds to the WSGI wsgi.input environ variable,
        # and allows you to read bytes from the request body.
        #
        # See also: PEP 3333
        if req.content_length in (None, 0):
            # Nothing to do
            return

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        try:
            req.context['doc'] = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')

    def process_response(self, req, resp, resource):
        if 'result' not in req.context:
            return

        resp.body = json.dumps(req.context['result'])


def start():
    global session_monitor
    global signer
    try:
        secret_key = configuration_data["secret-key"]
        assert type(secret_key) == str
        signer = Signer(secret_key)
    except (KeyError, AssertionError):
        error_string = "Please ensure that the secret_key is defined as a str in your configuration file."
        log.error(error_string)
        raise ConfigurationError(error_string)
    sessions.graph = graph
    # Start the session monitor
    session_monitor = sessions.Monitor()

# TODO: write content for the API and add /api/v1 mapping

def kill():
    """
    Kill the API and all sessions
    
    """
    # Kill the session monitor
    session_monitor.running = False
