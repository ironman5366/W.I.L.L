# Builtin imports
import logging
import uuid
import time

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

class Oauth2:
    """
    Handles all oauth2 authentication.
    At the route /api/v1/oauth2/step_id where step_id is one of `user_token` or `access_token`
    Post:
        user_token
            As an authenticated user (username+pw authentication from hooks.user_auth), request a signed access token
            That will be given to a client. The token is valid for 5 minutes and only valid with the client_id
            specified in the request, and with the scope specified in the request.
        access_token
            Post a user token to create a permanent relationship between a client and a user. Delete the previous
            user_token and return the access token. The access token will only be valid for the correct scope.
    Delete:
        access_token
            Delete the relationship between a user and a client
    """
    @falcon.before(hooks.client_auth)
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
        auth = req.context["auth"]
        if step_id == "user_token":
            # Generate a user token, put it in the database, and sign it
            # I can be sure that username already exists thanks to the pre request hook
            username = auth["username"]
            if "client_id" in auth.keys():
                client_id = auth["client_id"]
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
            if "user_token" in auth.keys():
                signed_auth_token = auth["user_token"]
                if "username" in auth.keys():
                    username = auth["username"]
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
                                auth["client_id"], username
                            ))
                            try:
                                # Check the signature with a 5 minute expiration
                                unsigned_auth_token = timestampsigner.unsign(signed_auth_token, 300)
                                log.debug("Token for user {0} provided by client {1} unsigned successfully".format(
                                    username, auth["client_id"]
                                ))
                                if unsigned_auth_token == rel["authorization_token"]:
                                    log.debug("Token check successful. Permanently connecting user {0} and client"
                                              " {1}".format(username, auth["client_id"]))
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
                                            "client_id": auth["client_id"],
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
                                              "user {1}".format(auth["client_id"], username))
                                    resp.status = falcon.HTTP_FORBIDDEN
                                    req.context["result"] = {
                                        "errors":
                                            [{
                                                "id": "AUTH_TOKEN_MISMATCHED",
                                                "type": "error",
                                                "text": "Provided token unsigned successfully but did not match with "
                                                        "the token provided by the user."
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
                                            username, auth["client_id"]
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
            auth = req.context["auth"]
            if "client_id" in auth.keys():
                client_id = auth["client_id"]
                session = graph.session()
                user_rels = session.run("MATCH (c:Client {client_id: {client_id})"
                                        "MATCH (u:User {username: {username}"
                                        "MATCH (u)-[r:{step_rel}]->(c)"
                                        "return (r)",
                                        {"client_id": client_id,
                                         "username": auth["username"],
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
                                "text": "Deleted relationship between user {0} and client {1}".format(auth["username"],
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
                                    auth["username"], client_id
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
    @falcon.before(hooks.session_auth)
    @falcon.before(hooks.client_can_change_settings)
    def on_put(self, req, resp):
        """
        Change user settings
        
        :param req: 
        :param resp: 
        :return: 
        """
        pass

    @falcon.before(hooks.session_auth)
    @falcon.before(hooks.client_can_read_settings)
    def on_get(self, req, resp):
        """
        Get information about a user
        
        :param req: 
        :param resp: 
        """
        auth = req.context["auth"]
        username = auth["username"]
        log.debug("Fetching data about user {}".format(username))
        # Start a graph session and return nonsensitive user data
        session = graph.session()
        matching_users = session.run("MATCH (u:User {username:{username}})"
                                     "return (u)",
                                     {"username": username})
        session.close()
        # We know the user exists because they passed the client user auth hook
        user = matching_users[0]
        user_fields = ["first_name", "last_name", "username", "settings"]
        user_data = {}
        # Put the users data into a dictionary that will be returned in a "data" key
        for d in user_fields:
            user_data.update({d: user[d]})
        req.context["result"] = {
            "data":
                {
                    "type": "success",
                    "text": "Fetched user data for user {}".format(username),
                    "user_data": user_data
                }
        }


    @falcon.before(hooks.session_auth)
    @falcon.before(hooks.client_is_official)
    def on_delete(self, req, resp):
        """
        Delete a user
        :return: 
        """
        auth = req.context["auth"]
        username = auth["username"]
        log.info("Deleting user {}".format(username))
        # End all the users sessions
        for session in sessions.sessions.values():
            if session.username == username:
                session.logout()
        session = graph.session()
        # Delete the user in the database
        session.run("MATCH (u:User {username: {username}})"
                    "DETACH DELETE (u)")
        session.close()
        req.context["result"] = {
            "data":
                {
                    "type": "success",
                    "text": "Deleted user {}".format(username),
                    "id": "USER_DELETED"
                }
        }

    @falcon.before(hooks.client_is_official)
    def on_post(self, req, resp):
        """
        Create a new user
        
        :param req: 
        :param resp: 
        :return: 
        """
        doc = req.context["data"]
        data_keys = doc.keys()
        required_fields = {
            "username": str,
            "password": str,
            "first_name": str,
            "last_name": str,
            "settings": dict
        }
        field_errors = []
        # TODO: validate settings
        for field, field_type in required_fields.items():
            if field in data_keys:
                if type(doc[field]) != field_type:
                    field_error = {
                        "type": 'error',
                        "id": "FIELD_{}_INVALID_TYPE".format(field.upper()),
                        "text": "Field {0} must be of type {1}".format(field, type(field_type).__name__),
                        "status": falcon.HTTP_BAD_REQUEST
                    }
                    field_errors.append(field_error)
            else:
                field_error = {
                    "type": "error",
                    "id": "FIELD_{}_NOT_FOUND".format(field.upper()),
                    "text": "Field {} required to create a user".format(field),
                    "status": falcon.HTTP_BAD_REQUEST
                }
                field_errors.append(field_error)
        # Check if there were errors during validation
        if field_errors:
            resp.status_code = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors": field_errors
            }
        # If the data was validated successfully, create the user in the database
        # At the same time create an authorization token for the official client
        else:
            session = graph.session()
            # Check to see if the username already exists
            users_found = session.run("MATCH (u:User {username: {username})",
                                      {"username": doc["username"]})
            if users_found:
                resp.status = falcon.HTTP_CONFLICT
                req.context["result"] = {
                    "errors":
                        [{
                            "type": "error",
                            "id": "USERNAME_ALREADY_EXISTS",
                            "text": "Username {} is already taken".format(doc["username"]),
                            "status": resp.status
                        }]
                }
            # The user doesn't already exist
            else:
                log.info("Creating user {}".format(doc["username"]))
                # Hash the users password
                hashed_password = bcrypt.hashpw(doc["password"], bcrypt.gensalt())
                auth = req.context["auth"]
                client_id = auth["client_id"]
                # Use oauth code to generate a access token for the official client.
                # Generate a secure token, sign it, and encrypt it in the database
                final_token = uuid.uuid4()
                # Sign the unencrypted version for the client
                signed_final_token = signer.sign(final_token)
                # Encrypt it and put in the database
                encrypted_final_token = bcrypt.hashpw(signed_final_token, bcrypt.gensalt())
                session.run(
                    "MATCH (c:Client {client_id: {client_id})"
                    "CREATE (u:User {"
                    "admin: false, "
                    "username: {username}, "
                    "password: {password}, "
                    "first_name: {first_name}, "
                    "last_name: {last_name},"
                    "settings:  {settings}"
                    "created: {created}})-[:USES {scope: 'official', access_token: {access_token}})->(c)",
                    {
                        "client_id": client_id,
                        "username": doc["username"],
                        "password": hashed_password,
                        "first_name": doc["first_name"],
                        "last_name": doc["last_name"],
                        "settings": doc["settings"],
                        "created": time.time(),
                        "access_token": encrypted_final_token
                    }
                )
                req.context["result"] = {
                    "data":
                        {
                            "type": "success",
                            "text": "Successfully created user {}".format(doc["username"]),
                            "id": "USER_CREATED",
                            "access_token": signed_final_token
                        }
                }
            session.close()



class Sessions:
    @falcon.before(hooks.client_user_auth)
    def on_post(self, req, resp, null_session_id):
        """
        Create a session
        
        """
        if null_session_id:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "NO_SESSION_ID_ON_CREATE",
                        "text": "POST requests to this method cannot include session id paths",
                        "status": resp.status
                    }]
            }
        else:
            auth = req.context["auth"]
            username = auth["username"]
            client = auth["client_id"]
            # Instantiate a session class
            log.debug("Starting session for user {0} on client {1}".format(username, client))
            session_class = sessions.Session(username, client)
            # Sign the session id
            unsigned_session_id = session_class.session_id
            session_id = signer.sign(unsigned_session_id)
            req.context["result"] = {
                "data":
                    {
                        "type": "success",
                        "id": "SESSION_CREATED",
                        "session_id": session_id,
                        "text": "Successfully created a session for user {0} on client {1}".format(username, client)
                    }
            }

    @falcon.before(hooks.session_auth)
    def on_delete(self, req, resp, session_id):
        """
        Logout a session
        The session auth hook already confirms it exists, and the assert param hook 
        :param req: 
        :param resp: 
        :param session_id:
        :return: 
        """
        # The session auth hook put this into req.context
        session = req.context["session"]
        session.logout()
