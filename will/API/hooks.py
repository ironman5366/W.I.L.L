#Buildin imports
import logging

#External imports
from itsdangerous import BadSignature
import falcon
import bcrypt

graph = None
signer = None

log = logging.getLogger()

#TODO: add scope hooks

def user_session(req, resp, resource, params):
    pass

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
                                 {"username": doc["username"]})
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
                raise falcon.HTTP_UNAUTHORIZED("Invalid password", "Invalid password for user {0}".format(username))
        else:
            error_message = "Couldn't find user {0}".format(username)
            log.debug(error_message)
            raise falcon.HTTP_UNAUTHORIZED("User not found", error_message)
    else:
        raise falcon.HTTP_UNAUTHORIZED("Username and password not found",
                                       "To access this API method you must provide a username and password")

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
                raise falcon.HTTP_UNAUTHORIZED(
                    "Invalid client_secret",
                    "Secret key is invalid"
                )
        else:
            raise falcon.HTTP_UNAUTHORIZD(
                "Client not found",
                "Couldn't find client with client id {0}".format(client_id)
            )
    else:
        raise falcon.HTTP_UNAUTHORIZED(
            "Client info not found",
            "You must pass a client id and client secret with every request"
        )
