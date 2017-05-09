#Builtin imports
import logging

#External imports
from itsdangerous import BadSignature
import falcon
import bcrypt

#Internal imports
from will.userspace import sessions

graph = None
signer = None

log = logging.getLogger()

scopes = {
    "admin": 0,
    "official": 1,
    "settings_change": 2,
    "settings_read": 3,
    "command": 4,
    "basic": 5
}

def user_auth(req, resp, resource, params):
    """
    Basic auth with a username and password
    
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 
    :return: 
    """
    auth = req.context["auth"]
    auth_keys = auth.keys()
    if "username" in auth_keys and "password" in auth_keys:
        username = auth["username"]
        password = auth["password"]
        # Connect to the db
        session = graph.session()
        # Search for the user in the database
        user_search = session.run("MATCH (u:User {username: {username}})"
                                  "return (u)",
                                  {"username": username})
        session.close()
        # If the user exists
        if user_search:
            user_node = user_search[0]
            # Check the pw against the hash
            auth = bcrypt.checkpw(password.encode('utf-8'), user_node["password"].encode('utf-8'))
            # If the password is incorrect, through an unauthorized error
            if not auth:
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "type": "error",
                            "text": "Password incorrect",
                            "id": "PASSWORD_INVALID",
                            "status": resp.status
                        }]
                }
                raise falcon.HTTPError(resp.status, "Incorrect password")
        else:
            resp.status = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "USER_INVALID",
                        "text": "User {} doesn't exist".format(username),
                        "status": resp.status
                    }]
            }
            raise falcon.HTTPError(resp.status, "Username invalid")

    else:
        resp.status = falcon.HTTP_BAD_REQUEST
        req.context["result"] = {
            "errors":
                [{
                    "type": "error",
                    "id": "USERNAME_PASSWORD_NOT_FOUND",
                    "text": "A request to this method must include a username and password",
                    "status": resp.status
                }]
        }
        raise falcon.HTTPError(resp.status, "Username/password not found")

def assert_param(req, resp, resource, params):
    """
    Make sure that a parameter has been passed to the method, through a bad request error if one hasn't been
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 
    """
    if not params.values():
        resp.status = falcon.HTTP_BAD_REQUEST
        req.context["result"] = {
            "errors":
                [{
                    "type": "error",
                    "id": "PARAM_NOT_FOUND",
                    "text": "This method requires url parameters that were not found",
                    "status": resp.status
                }]
        }
        raise falcon.HTTPError(resp.status, "Paramater required")

def session_auth(req, resp, resource, params):
    """
    Checks an active session id
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 
    
    """
    # Check if the session id is present
    auth = req.context["auth"]
    signed_session_id = None
    if "session_id" in auth.keys():
        signed_session_id = auth["session_id"]
    if signed_session_id:
        # Unsign the session id
        try:
            session_id = signer.unsign(signed_session_id)
            req.context["unsigned_session_id"] = session_id
            # Go through the sessions
            if session_id in sessions.sessions.keys():
                session = sessions.sessions[session_id]
                if "client_id" in auth.keys():
                    client_id = auth["client_id"]
                    # The session is correct, add data to req.context
                    if session.client == client_id:
                        req.context["session"] = session
                    else:
                        resp.status = falcon.HTTP_UNAUTHORIZED
                        req.context["result"] = {
                            "errors":
                                [{
                                    "type": "error",
                                    "id": "SESSION_ID_CLIENT_MISMATCHED",
                                    "text": "Session with session id {0} did not have client {1}".format(
                                        signed_session_id, client_id
                                    ),
                                    "status": resp.status
                                }]
                        }
                        raise falcon.HTTPError(resp.status, "Session client mismatch")
            else:
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "type": "error",
                            "id": "SESSION_ID_INVALID",
                            "text": "Session id {} is invalid".format(signed_session_id),
                            "status": resp.status
                        }]
                }
                raise falcon.HTTPError(resp.status, "Invalid session id")
        # The session id had an invalid signature
        except BadSignature:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "text": "Signature of passed session id was invalid",
                        "id": "SESSION_ID_BAD_SIGNATURE",
                        "status": resp.status
                    }]
            }
            raise falcon.HTTPError(resp.status, "Invalid signature")
    else:
        resp.status = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "type": "error",
                    "id": "SESSION_ID_NOT_FOUND",
                    "text": "This request must be authenticated with a session id",
                    "status": resp.status
                }]
        }
        raise falcon.HTTPError(resp.status, "Session id not found")

def calculate_scope(scope_submitted, scope_required):
    """
    Determine whether a submitted scope is high level enough to meet the permissions of the required scope
    
    :param scope_submitted: The scope that a request submitted, and what it has access to 
    :param scope_required: The scope that would be required for the request to submit successfully 
    :return scope_valid: A bool defining  whether the submitted scope meets the required scope
    """
    if scope_submitted in scopes and scope_required in scopes:
        submitted_level = scopes[scope_submitted]
        required_level = scopes[scope_required]
        return submitted_level <= required_level
    return False

def _scope_check(req, resp, resource, params, level):
    """
    Check a submitted scope
    
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 
    :param level: the scope
     
    """
    session_auth(req, resp, resource, params)
    # Check the client scope, letting session_auth do validation
    session = graph.session()
    auth = req.context["auth"]
    if "username" in auth.keys():
        username = auth["username"]
        client_id = auth["client_id"]
        # Fetch the user node and the client relation node from the graph, and close the session
        rel_data = session.run("MATCH (u:User {username: {username}})"
                               "MATCH (c:Client {client_id: {client_id}})"
                               "MATCH (u)-[r:USES]->(c)"
                               "return (r)",
                               {"username": username,
                                "client_id": client_id})
        session.close()
        rel = rel_data[0]
        # Check the scope of the relationship
        scope = rel["scope"]
        if scope in scopes.keys():
            # See if the scope meets the required privileges
            scope_met = calculate_scope(scope, level)
            if scope_met:
                log.debug("Client {0} provided a sufficient scope for the request resource {1}".format(
                    client_id, resource
                ))
            else:
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "SCOPE_INSUFFICIENT",
                            "type": "error",
                            "text": "Your clients scope {0} does not meet the required scope admin for this method".format(
                                scope
                            ),
                            "status": resp.status
                        }]
                }
                raise falcon.HTTPError(resp.status, "Insufficient")
        else:
            log.error("Invalid scope in database! Unrecognized scope {0} appeared in database between user {1} and client "
                      "{2}".format(scope, username, client_id))
            # Throw an error because there's invalid data
            resp.status = falcon.HTTP_INTERNAL_SERVER_ERROR
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "SCOPE_INTERNAL_ERROR",
                        "status": resp.status,
                        "text": "The database provided an invalid scope. Please contact will@willbeddow.com to submit a "
                                "bug report."
                    }]
            }
            raise falcon.HTTPError(resp.status, title="Internal scope error")
    else:
        resp.status = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "type": "error",
                    "text": "Username not found in request",
                    "id": "USERNAME_NOT_FOUND",
                    "status": resp.status
                }]
        }
        raise falcon.HTTPError(resp.status, "Username not found")


def client_is_official(req, resp, resource, params):
    """
    Checks that a client is official

    """
    client_auth(req, resp, resource, params)
    auth = req.context["auth"]
    client_id = auth["client_id"]
    session = graph.session()
    clients = session.run("MATCH (c:Client {client_id: {client_id}}) return (c)",
                {"client_id": client_id})
    session.close()
    client = clients[0]
    # Check if the client is an official client provided by myself
    if client["official"]:
        log.debug("Client {0} is an official client".format(client_id))
    else:
        resp.status = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "CLIENT_UNOFFICIAL",
                    "type": "error",
                    "status": resp.status,
                    "text": "Client {0} is not official".format(client_id)
                }]
        }
        raise falcon.HTTPError(resp.status, "Client unofficial")




def user_is_admin(req, resp, resource, params):
    """
    Simple scope hook for admin prviliges
    
    """
    # If there's a scope problem with the client this will raise an error. It also runs the client and user auth checks
    _scope_check(req, resp, resource, params, "admin")
    auth = req.context["auth"]
    username = auth["username"]
    # Run a graph session and check if the user is an admin
    session = graph.session()
    users = session.run("MATCH (u:User {username:{username}}) return(u)",
                            {"username": username})
    session.close()
    user_node = users[0]
    if user_node["admin"]:
        log.debug("User {0} is an administrator and passed all layers of authentication".format(
            username
        ))
    else:
        resp.status = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "USER_NOT_ADMIN",
                    "type": "error",
                    "status": resp.status,
                    "text": "User {0} is not an administrator".format(username)
                }]
        }
        raise falcon.HTTPError(resp.status, "Administrator privileges")


def client_can_read_settings(req, resp, resource, params):
    """
    Simple scope hook for read settings privileges
    """
    _scope_check(req, resp, resource, params, "settings_read")

def client_can_change_settings(req, resp, resource, params):
    _scope_check(req, resp, resource, params, "settings_change")

def client_can_make_commands(req, resp, resource, params):
    _scope_check(req, resp, resource, params, "command")

def client_user_auth(req, resp, resource, params):
    """
    Check a client exists and has a permanent access token for a user.
    
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 

    """
    # First check that the client has proper authentication
    client_auth(req, resp, resource, params)
    # If the client has proper authentication, check their access token
    auth = req.context["auth"]
    if "access_token" in auth.keys():
        access_token = auth["access_token"]
        # Check that the username is in the database
        if "username" in auth.keys():
            username = auth["username"]
            # Check that the username exists
            session = graph.session()
            users = session.run("MATCH (u:User {username: {username}}) return (u)",
                                {"username": username})
            session.close()
            if users:
                # Unsign the access token
                session = graph.session()
                try:
                    unsigned_access_token = signer.unsign(access_token)
                    # Check the access token against the database using bcrypt
                    session = graph.session()
                    rels = session.run(
                                        "MATCH (u:User {username:{username}})"
                                        "MATCH (c:Client {client_id: {client_id}})"
                                        "MATCH (u)-[r:USES]->(c)"
                                        "return (r)",
                                        {"username": username,
                                         "client_id": auth["client_id"]})
                    # If the relationship exists
                    if rels:
                        rel = rels[0]
                        encrypted_access_token = rel["access_token"]
                        if bcrypt.checkpw(unsigned_access_token.encode('utf-8'),
                                          encrypted_access_token.encode('utf-8')):
                            log.debug("Successful authentication from client {0} on behalf of user {1}".format(
                                auth["client_id"], username
                            ))
                        else:
                            resp.status=falcon.HTTP_UNAUTHORIZED
                            req.context["result"] = {
                                "errors":
                                    [{
                                        "id": "ACCESS_TOKEN_INVALID",
                                        "type": "error",
                                        "text": "Submitted access token is invalid",
                                        "status": resp.status
                                    }]
                            }
                            raise falcon.HTTPError(resp.status)
                    else:
                        resp.status = falcon.HTTP_UNAUTHORIZED
                        req.context["result"] = {
                            "errors":
                                [{
                                    "type": "error",
                                    "id": "USER_NOT_AUTHENTICATED",
                                    "status": resp.status,
                                    "text": "User {0} has not authenticated with client {1}".format(
                                        username, auth["client_id"]
                                    )
                                }]
                        }
                        raise falcon.HTTPError(resp.status, "User not authenticated")
                except BadSignature:
                    resp.status = falcon.HTTP_UNAUTHORIZED
                    req.context["result"] = {
                        "errors":
                            [{
                                "id": "ACCESS_TOKEN_INVALID",
                                "type": "error",
                                "status": resp.status,
                                "text": "Provided access token had a bad or corrupt signature"
                            }]
                    }
                    raise falcon.HTTPError(resp.status, "Invalid access token")
                finally:
                    # No matter what close the session
                    session.close()
            else:
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "USERNAME_INVALID",
                            "type": "error",
                            "status": resp.status,
                            "text": "User {0} not found".format(username)
                        }]
                }
                raise falcon.HTTPError(resp.status, title="User not found")
        else:
            resp.status = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "USERNAME_NOT_FOUND",
                        "type": "error",
                        "status": resp.status,
                        "text": "Username not provided"
                    }]
            }
            raise falcon.HTTPError(resp.status, "Username not found")
    else:
        resp.status = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "ACCESS_TOKEN_NOT_FOUND",
                    "type": "error",
                    "text": "Access token not provided",
                    "status": resp.status
                }]
        }
        raise falcon.HTTPError(resp.status, "Access token required")

def client_auth(req, resp, resource, params):
    """
    Runs authentication for a client id and a client secret

    :param req: Request object
    :param resp: Response object
    :param resource: The resource that will be activated
    :param params: Additional parameters
    """
    auth = req.context["auth"]
    if "client_id" in auth.keys() and "client_secret" in auth.keys():
        client_id = auth["client_id"]
        signed_secret_key = auth["client_secret"]
        # Try to usnign the secret key before opening a databsae connection
        try:
            secret_key = signer.unsign(signed_secret_key)
        except BadSignature:
            # The signature was invalid
            resp.status = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "CLIENT_SECRET_BAD_SIGNATURE",
                        "type":  "error",
                        "status": resp.status,
                        "text": "The submitted client secret key was unsigned or had a bad signature"
                    }]
            }
            raise falcon.HTTPError(resp.status, "Bad signature")
        session = graph.session()
        clients = session.run("MATCH (c:Client {name: {client_id}}) return (c)",
                              {"client_id": client_id})
        session.close()
        if clients:
            client = clients[0]
            secret_key_hash = client["client_secret"]
            if bcrypt.checkpw(secret_key.encode('utf-8'), secret_key_hash.encode('utf-8')):
                log.debug("Successful authentication for client {0}".format(client_id))
            else:
                log.debug("Failed authentication for client {0}".format(client_id))
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "CLIENT_SECRET_INVALID",
                            "type": "error",
                            "text": "Provided clients secret key is invalid",
                            "status": resp.status
                        }]
                }
                raise falcon.HTTPError(resp.status, title="Invalid client secret")
        else:
            resp.status = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "CLIENT_ID_INVALID",
                        "type": "error",
                        "text": "Couldn't find client {0}".format(client_id),
                        "status": resp.status
                    }]
            }
            raise falcon.HTTPError(resp.status, title="Client not found")
    else:
        resp.status = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "CLIENT_ID_NOT_FOUND",
                    "status": resp.status,
                    "type": "error",
                    "text": "You must pass a client id and client secret with every request"
                }]
        }
        raise falcon.HTTPError(resp.status, title="Client info not found")
