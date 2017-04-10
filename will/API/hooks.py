#Buildin imports
import logging

#External imports
from itsdangerous import BadSignature
import falcon
import bcrypt

graph = None
signer = None

log = logging.getLogger()

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
