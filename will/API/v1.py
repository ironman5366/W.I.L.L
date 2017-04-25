# Builtin imports
import logging
import uuid

# Internal imports
from will.API import hooks
from will.userspace import sessions

# External imports
import falcon
from itsdangerous import BadSignature, BadTimeSignature
import bcrypt

log = logging.getLogger()

graph = None
timestampsigner = None
signer = None


# TODO: update ids

class Oauth2:
    @falcon.before(hooks.user_auth)
    def on_post(self, req, resp, step_id):
        """
        Send parameters and get a token for a certain id.
        Precondition is that user and client are authenticated
        
        :param req: The request object
        :param resp: The response object
        :param step_id: The step of the authorization. Should be either ["user_token", or "access_token"]
        
        """
        doc = req.context["doc"]
        if step_id == "user_token":
            # Generate a user token, put it in the database, and sign it
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
                        resp.status = falcon.HTTP_UNAUTHORIZED
                        req.context["result"] = {"errors":
                                                     [{"id": "CLIENT_ID_INVALID",
                                                       "type": "error",
                                                       "status": resp.status,
                                                       "text": "Client id {} is invalid.".format(client_id)}]}
                    # Regardless of the response, close the session
                    session.close()
                else:
                    resp.status = falcon.HTTP_UNAUTHORIZED
                    req.context["result"] = {"errors":
                                                 [{"id": "SCOPE_NOT_FOUND",
                                                   "type": "error",
                                                   "text": "You must provide a scope with this request",
                                                   "status": resp.status}]}
            else:
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {"errors":
                                             [{"id": "CLIENT_ID_NOT_FOUND",
                                               "type": "error",
                                               "status": resp.status,
                                               "text": "You must provide a client id with this request"}]}
            pass
        elif step_id == "access_token":
            if "user_token" in doc.keys():
                signed_auth_token = doc["user_token"]
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
                            log.debug("Starting client connection process for client {0} and user {1}".format(
                                doc["client_id"], username
                            ))
                            try:
                                # Check the signature with a 5 minute expiration
                                unsigned_auth_token = timestampsigner.unsign(signed_auth_token, 300)
                                log.debug("Token for user {0} provided by client {1} unsigned successfully".format(
                                    username, doc["client_id"]
                                ))
                                if unsigned_auth_token == rel["authorization_token"]:
                                    log.debug("Token check successful. Permanently connecting user {0} and client"
                                              " {1}".format(username, doc["client_id"]))
                                    # Generate a secure token, sign it, and encrypt it in the database
                                    final_token = uuid.uuid4()
                                    # Sign the unencrypted version for the client
                                    signed_final_token = signer.sign(final_token)
                                    # Encrypt it and put in the database
                                    encrypted_final_token = bcrypt.hashpw(signed_final_token, bcrypt.gensalt())
                                    session.run({
                                        "MATCH (u:User {username:{username}})"
                                        "MATCH (c:Client {client_id:{client_id}})"
                                        "CREATE (u)-[:USES {scope: {scope}, {access_token: {access_token}}]->(c)",
                                        {
                                            "username": username,
                                            "client_id": doc["client-id"],
                                            "scope": rel["scope"],
                                            "access_token": encrypted_final_token
                                        }
                                    })
                                    # Return the signed token to the client
                                    req.context["result"] = {
                                        "data":
                                            {
                                                "id": "CLIENT_ACCESS_TOKEN",
                                                "type": "success",
                                                "access_token": signed_final_token,
                                                "text": "Generated signed access token"
                                            }
                                    }
                                else:
                                    log.debug("Token provided by client {0} was mismatched with token provided by "
                                              "user {1}".format(doc["client_id"], username))
                                    resp.status = falcon.HTTP_FORBIDDEN
                                    req.context["result"] = {
                                        "errors":
                                            [{
                                                "id": "AUTH_TOKEN_MISMATCHED",
                                                "type": "error",
                                                "text": "Provided token unsigned successfully but did not match with the "
                                                        "token provided by the user."
                                            }]
                                    }
                            # The timestamp or the signature was invalild
                            except (BadSignature, BadTimeSignature):
                                log.debug("Client connection for user {0} and client {1} failed because of a bad or "
                                          "expired signature. Deleting inapplicable relation")
                                resp.status = falcon.HTTP_FORBIDDEN
                                req.context["result"] = {
                                    "errors":
                                        [{
                                            "id": "AUTH_TOKEN_INVALID",
                                            "type": "error",
                                            "text": "Provided authentication token had an invalid or expired signature",
                                            "status": resp.status
                                        }]
                                }
                            # Regardless of whether the token was valid, we want to delete the temporary auth connection
                            finally:
                                session.run("MATCH (u:User {username: {username}})"
                                            "MATCH (c:Client {client_id: {client_id}})"
                                            "MATCH (u)-[r:AUTHORIZED]->(c)"
                                            "DETACH DELETE (r)")

                        else:
                            resp.status = falcon.HTTP_UNAUTHORIZED
                            resp.context["result"] = {
                                "errors":
                                    [{
                                        "id": "USER_NOT_AUTHORIZED",
                                        "type": "error",
                                        "text": "The user {0} has not authorized a connection with client {1}".format(
                                            username, doc["client_id"]
                                        ),
                                        "status": resp.status
                                    }]
                            }
                    else:
                        resp.status = falcon.HTTP_UNAUTHORIZED
                        resp.context["result"] = {
                            "errors":
                                [{
                                    "id": "USERNAME_INVALID",
                                    "type": "error",
                                    "status": resp.status,
                                    "text": "Couldn't find username {0}".format(username)
                                }]
                        }
                    session.close()
                else:
                    resp.status = falcon.HTTP_UNAUTHORIZED
                    resp.context["result"] = {
                        "errors":
                            [{
                                "id": "USERNAME_NOT_FOUND",
                                "type": "error",
                                "status": resp.status,
                                "text": "A valid username must be submitted with this this request"
                            }]
                    }
            else:
                resp.status = falcon.HTTP_UNAUTHORIZED
                resp.context["result"] = {
                    "errors":
                        [{
                            "id": "AUTH_TOKEN_NOT_FOUND",
                            "type": "error",
                            "status": resp.status,
                            "text": "A signed and recent authorization token must be submitted along with this request."
                        }]
                }
        else:
            resp.status = falcon.HTTP_NOT_FOUND
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "STEP_ID_NOT_FOUND",
                        "status": resp.status,
                        "text": "Step id {} not found".format(step_id)
                    }]
            }

    @falcon.before(hooks.user_auth)
    def on_delete(self, req, resp, step_id):
        """
        As an authenticated user, terminate a relationship with a client
        
        :param req: 
        :param resp: 
    
        """
        step_rels = {
            "user_token": "AUTHORIZED",
            "access_token": "USES"
        }
        if step_id in step_rels.keys():
            step_rel = step_rels[step_id]
            doc = req.context["doc"]
            if "client_id" in doc.keys():
                client_id = doc["client_id"]
                session = graph.session()
                user_rels = session.run("MATCH (c:Client {client_id: {client_id})"
                                        "MATCH (u:User {username: {username}"
                                        "MATCH (u)-[r:{step_rel}]->(c)"
                                        "return (r)",
                                        {"client_id": client_id,
                                         "username": doc["username"],
                                         "step_rel": step_rel})
                if user_rels:
                    # Delete the relationship
                    rel = user_rels[0]
                    session.run("MATCH [r:{step_rel}] WHERE ID(r) = {rel_id}"
                                "DETACH DELETE (r)",
                                {
                                    "step_rel": step_rel,
                                    "rel_id": rel.id})
                    req.context["result"] = {
                        "data":
                            {
                                "type": "success",
                                "text": "Deleted relationship between user {0} and client {1}".format(doc["username"],
                                                                                                      client_id)
                            }
                    }
                else:
                    resp.status_code = falcon.HTTP_NOT_FOUND
                    req.context["result"] = {
                        "errors":
                            [{
                                "type": "error",
                                "text": "Couldn't find a relationship between user {0} and client {1}".format(
                                    doc["username"], client_id
                                )
                            }]
                    }
                session.close()
            else:
                resp.status = falcon.HTTP_NOT_FOUND
                req.context["result"] = {
                    "errors":
                    [{
                        "type": "error",
                        "id": "CLIENT_ID_NOT_FOUND",
                        "text": "A DELETE request to this method must include a client id",
                        "status": resp.status
                    }]
                }
        # The passed step id (DELETE /api/v1/oauth2/step_id) was not recognized
        else:
            resp.status = falcon.HTTP_NOT_FOUND
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id":  "STEP_ID_NOT_FOUND",
                        "text": "Step id {0} not recognized".format(step_id),
                        "status": resp.status_code
                    }]
            }


class Users:
    @falcon.before(hooks.client_user_auth)
    def on_put(self, req, resp):
        """
        Update a users settings
        
        :param req: 
        :param resp: 
        :return: 
        """
        pass

    @falcon.before(hooks.client_user_auth)
    def on_get(self, req, resp):
        """
        Get information about a user
        
        :param req: 
        :param resp: 
        :return: 
        """
        pass

    def on_delete(self):
        pass


class Sessions:
    @falcon.before(hooks.client_user_auth)
    def on_get(self, req, resp, session_id):
        """
        Fetch session information
        :param req: 
        :param resp: 
        :param session_id: The session id to fetch
        :return: 
        """
        if session_id in sessions.ended_sessions:
            pass
        else:
            for session in sessions.sessions:
                if session.uid == session_id:
                    pass

    def put(self, req, resp):
        """
        Change an attribute of the session
        :param req: 
        :param resp: 
        :return: 
        """
        doc = req.context["doc"]
