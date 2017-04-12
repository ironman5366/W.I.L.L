#Buildin imports
import logging

#External imports
from itsdangerous import BadSignature
import falcon
import bcrypt

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
    client_user_auth(req, resp, resource, params)
    # Check the client scope. We don't have to validate the client and user, client_user_auth does that for us
    session = graph.session()
    doc = req.context["doc"]
    username = doc["username"]
    client_id = doc["client_id"]
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
            resp.status_code = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "SCOPE_INSUFFICIENT",
                        "type": "error",
                        "text": "Your clients scope {0} does not meet the required scope admin for this method".format(
                            scope
                        ),
                        "status": resp.status_code
                    }]
            }
            raise falcon.HTTPError(resp.status_code, "Insufficient")
    else:
        log.error("Invalid scope in database! Unrecognized scope {0} appeared in database between user {1} and client "
                  "{2}".format(scope, username, client_id))
        # Throw an error because there's invalid data
        resp.status_code = falcon.HTTP_INTERNAL_SERVER_ERROR
        req.context["result"] = {
            "errors":
                [{
                    "type": "error",
                    "id": "SCOPE_INTERNAL_ERROR",
                    "status": resp.status_code,
                    "text": "The database provided an invalid scope. Please contact will@willbeddow.com to submit a "
                            "bug report."
                }]
        }
        raise falcon.HTTPError(resp.status_code, title="Internal scope error")

def client_is_official(req, resp, resource, params):
    """
    Checks that a client is official

    """
    client_auth(req, resp, resource, params)
    doc = req.context["doc"]
    client_id = doc["client_id"]
    session = graph.session()
    clients = session.run("MATCH (c:Client {client_id: {client_id}}) return (c)",
                {"client_id": client_id})
    session.close()
    client = clients[0]
    # Check if the client is an official client provided by myself
    if client["official"]:
        log.debug("Client {0} is an official client".format(client_id))
    else:
        resp.status_code = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "CLIENT_UNOFFICIAL",
                    "type": "error",
                    "status": resp.status_code,
                    "text": "Client {0} is not official".format(client_id)
                }]
        }
        raise falcon.HTTPError(resp.status_code, "Client unofficial")




def user_is_admin(req, resp, resource, params):
    """
    Simple scope hook for admin prviliges
    
    """
    # If there's a scope problem with the client this will raise an error. It also runs the client and user auth checks
    _scope_check(req, resp, resource, params, "admin")
    doc = req.context["doc"]
    username = doc["username"]
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
        resp.status_code = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "USER_NOT_ADMIN",
                    "type": "error",
                    "status": resp.status_code,
                    "text": "User {0} is not an administrator".format(username)
                }]
        }
        raise falcon.HTTPError(resp.status_code, "Administrator privileges")

def client_user_auth(req, resp, resource, params):
    """
    Check a client that has a permanent access token for a user.
    
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 

    """
    # First check that the client has proper authentication
    client_auth(req, resp, resource, params)
    # If the client has proper authentication, check their access token
    doc = req.context["doc"]
    if "access_token" in doc.keys():
        access_token = doc["access_token"]
        # Check that the username is in the database
        if "username" in doc.keys():
            username = doc["username"]
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
                                         "client_id": doc["client_id"]})
                    # If the relationship exists
                    if rels:
                        rel = rels[0]
                        encrypted_access_token = rel["access_token"]
                        if bcrypt.checkpw(unsigned_access_token, encrypted_access_token):
                            log.debug("Successful authentication from client {0} on behalf of user {1}".format(
                                doc["client_id"], username
                            ))
                        else:
                            resp.status_code=falcon.HTTP_UNAUTHORIZED
                            req.context["result"] = {
                                "errors":
                                    [{
                                        "id": "ACCESS_TOKEN_INVALID",
                                        "type": "error",
                                        "text": "Submitted access token is invalid",
                                        "status": resp.status_code
                                    }]
                            }
                            raise falcon.HTTPError(resp.status_code)
                    else:
                        resp.status_code = falcon.HTTP_UNAUTHORIZED
                        req.context["result"] = {
                            "error":
                                [{
                                    "type": "error",
                                    "id": "USER_NOT_AUTHENTICATED",
                                    "status": resp.status_code,
                                    "text": "User {0} has not authenticated with client {1}".format(
                                        username, doc["client_id"]
                                    )
                                }]
                        }
                        raise falcon.HTTPError(resp.status_code, "User not authenticated")
                except BadSignature:
                    resp.status_code = falcon.HTTP_UNAUTHORIZED
                    req.context["result"] = {
                        "errors":
                            [{
                                "id": "ACCESS_TOKEN_INVALID",
                                "type": "error",
                                "status": resp.status_code,
                                "text": "Provided access token had a bad or corrupt signature"
                            }]
                    }
                    raise falcon.HTTPError(resp.status_code, "Invalid access token")
                finally:
                    # No matter what close the session
                    session.close()
            else:
                resp.status_code = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "USERNAME_INVALID",
                            "type": "error",
                            "status": resp.status_code,
                            "text": "User {0} not found".format(username)
                        }]
                }
                raise falcon.HTTPError(resp.status_code, title="User not found")
        else:
            resp.status_code = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "USERNAME_NOT_FOUND",
                        "type": "error",
                        "status": resp.status_code,
                        "text": "Username not provided"
                    }]
            }
            raise falcon.HTTPError(resp.status_code, "Username not found")
    else:
        resp.status_code = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "ACCESS_TOKEN_NOT_FOUND",
                    "type": "error",
                    "text": "Access token not provided",
                    "status": resp.status_code
                }]
        }
        raise falcon.HTTPError(resp.status_code, "Accesss token required")

def user_auth(req, resp, resource, params):
    """
    A hook to authenticate a request with a username and password in it
    
    :param req: 
    :param resp: 
    :param resource: 
    :param params: 
    """
    doc = req.context["doc"]
    if "username" in doc.keys() and "password" in doc.keys():
        username = doc["username"]
        password = doc["password"]
        session = graph.session()
        user_nodes = session.run("MATCH (u:User {username: {username}}) return (u)",
                                 {"username": username})
        session.close()
        # Check if the user exists
        if user_nodes:
            user = user_nodes[0]
            pw_hash = user["password"]
            # Check if the password is valid
            if bcrypt.checkpw(password, pw_hash):
                log.debug("Successfully authenticated user {0} with username and password".format(username))
            else:
                log.debug("Authentication failed for user {0}".format(username))
                resp.status_code = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "PASSWORD_INVALID",
                            "status": resp.status_code,
                            "type": "error",
                            "text": "Invalid password for user {0}".format(username)
                        }]
                }
                raise falcon.HTTPError(resp.status_code, title="Invalid password")
        else:
            error_message = "Couldn't find user {0}".format(username)
            log.debug(error_message)
            resp.status_code = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "USER_INVALID",
                        "status": resp.status_code,
                        "text": "User {0} could not be found".format(username)
                    }]
            }
            raise falcon.HTTPError(resp.status_code, "User not found")
    else:
        resp.status_code = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "type": "error",
                    "id": "USERNAME_PASSWORD_NOT_FOUND",
                    "status":  resp.status_code,
                    "text": "To access this API method you must provide a username and password"
                }]
        }
        raise falcon.HTTPError(resp.status_code, "Username/password not found")

def client_auth(req, resp, resource, params):
    """
    Runs authentication for a client id and a client secret

    :param req: Request object
    :param resp: Response object
    :param resource: The resource that will be activated
    :param params: Additional parameters
    """
    doc = req.context["doc"]
    if "client_id" in doc.keys() and "client_secret" in doc.keys():
        session = graph.session()
        client_id = doc["client_id"]
        secret_key = doc["client_secret"]
        clients = session.run("MATCH (c:Client {name: {client_id}}) return (c)",
                              {"client_id": client_id})
        if clients:
            client = clients[0]
            secret_key_hash = client["secret_key"]
            if bcrypt.checkpw(secret_key, secret_key_hash):
                log.debug("Successful authentication for client {0}".format(client_id))
            else:
                log.debug("Failed authentication for client {0}".format(client_id))
                resp.status_code = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "CLIENT_SECRET_INVALID",
                            "type": "error",
                            "text": "Provided clients secret key is invalid",
                            "status": resp.status_code
                        }]
                }
                raise falcon.HTTPError(resp.status_code, title="Invalid client secret")
        else:
            resp.status_code = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "CLIENT_ID_INVALID",
                        "type": "error",
                        "text": "Couldn't find client {0}".format(client_id),
                        "status": resp.status_code
                    }]
            }
            raise falcon.HTTPError(resp.status_code, title="Client not foun ")
    else:
        resp.status_code = falcon.HTTP_UNAUTHORIZED
        req.context["result"] = {
            "errors":
                [{
                    "id": "CLIENT_ID_NOT_FOUND",
                    "status": resp.status_code,
                    "type": "error",
                    "text": "You must pass a client id and client secret with every request"
                }]
        }
        raise falcon.HTTPError(resp.status_code, title="Client info not found")
