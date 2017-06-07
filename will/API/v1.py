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

db = None
timestampsigner = None
signer = None


class Oauth2Step:
    """
    The base class for an Oauth step.
    Inherited by Oauth resource classes, used to house shared code
    The oauth2 resources handle authentication by the oauth2 spec
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
    _step_id = None

    def on_post(self, req, resp):
        raise NotImplementedError

    @falcon.before(hooks.user_auth)
    def on_delete(self, req, resp):
        """
        As an authenticated user, terminate a relationship with a client

        :param req: 
        :param resp: 

        """
        step_rels = {
            "user_token": "AUTHORIZED",
            "access_token": "USES"
        }
        if self._step_id in step_rels.keys():
            step_rel = step_rels[self._step_id]
            auth = req.context["auth"]
            if "client_id" in auth.keys():
                client_id = auth["client_id"]
                session = db.session()
                user_rels = session.run("MATCH (c:Client {client_id: {client_id})"
                                        "MATCH (u:User {username: {username}})"
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
                    resp.status = falcon.HTTP_NOT_FOUND
                    req.context["result"] = {
                        "errors":
                            [{
                                "type": "error",
                                "text": "Couldn't find a relationship between user {0} and client {1}".format(
                                    auth["username"], client_id
                                ),
                                "id": "USER_CLIENT_REL_NOT_FOUND",
                                "status": resp.status
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
                        "id": "STEP_ID_NOT_FOUND",
                        "text": "Step id {0} not recognized".format(self._step_id),
                        "status": resp.status
                    }]
            }


@falcon.before(hooks.client_is_official)
@falcon.before(hooks.origin_client_auth)
class AccessToken(Oauth2Step):
    _step_id = "access_token"

    @falcon.before(hooks.user_auth)
    def on_post(self, req, resp):
        """
        The access token component of the oauth authentication
        :param req: 
        :param resp: 
        :return: 
        """
        auth = req.context["auth"]
        if "user_token" in auth.keys():
            signed_auth_token = auth["user_token"]
            username = auth["username"]
            # Make sure the user exists
            session = db.session()
            # Check if an AUTHORIZED relationship exists between the user and the client
            rels = session.run("MATCH (u:User {username: {username}})"
                               "MATCH (c:Client {client_id: {client_id}})"
                               "MATCH (u)-[r:AUTHORIZED]->(c) return(r)",
                               {"username": username,
                                "client_id": auth["origin_client_id"]})
            if rels:
                # Validation
                rel = rels[0]
                log.debug("Starting client connection process for client {0} and user {1}".format(
                    auth["origin_client_id"], username
                ))
                try:
                    # Check the signature with a 5 minute expiration
                    unsigned_auth_token = timestampsigner.unsign(signed_auth_token, 300).decode('utf-8')
                    log.debug("Token for user {0} provided by client {1} unsigned successfully".format(
                        username, auth["client_id"]
                    ))
                    if unsigned_auth_token == rel["user_token"]:
                        log.debug("Token check successful. Permanently connecting user {0} and client"
                                  " {1}".format(username, auth["client_id"]))
                        # Generate a secure token, sign it, and encrypt it in the database
                        final_token = str(uuid.uuid4())
                        # Sign the unencrypted version for the client
                        signed_final_token = signer.sign(final_token.encode('utf-8')).decode('utf-8')
                        # Encrypt it and put in the database
                        encrypted_final_token = bcrypt.hashpw(
                            signed_final_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        session.run(
                            "MATCH (u:User {username:{username}})"
                            "MATCH (c:Client {client_id:{client_id}})"
                            "CREATE (u)-[:USES {scope: {scope}, {access_token: {access_token}}]->(c)",
                            {
                                "username": username,
                                "client_id": auth["client_id"],
                                "scope": rel["scope"],
                                "access_token": encrypted_final_token
                            }
                        )
                        # Return the signed token to the client
                        req.context["result"] = {
                            "data":
                                {
                                    "id": "CLIENT_ACCESS_TOKEN",
                                    "type": "success",
                                    "token": signed_final_token,
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
                # The timestamp or the signature was invalid
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
                req.context["result"] = {
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
            session.close()
        else:
            resp.status = falcon.HTTP_UNAUTHORIZED
            req.context["result"] = {
                "errors":
                    [{
                        "id": "AUTH_TOKEN_NOT_FOUND",
                        "type": "error",
                        "status": resp.status,
                        "text": "A signed and recent authorization token must be submitted along with this request."
                    }]
            }


@falcon.before(hooks.client_is_official)
@falcon.before(hooks.origin_client_auth)
class UserToken(Oauth2Step):
    """
    User token role for oauth
    """
    _step_id = "user_token"

    @falcon.before(hooks.user_auth)
    def on_post(self, req, resp):
        """
        Send parameters and get a token for a certain id.
        Precondition is that the user is authorized and an OFFICIAL client submitted the request
        
        :param req: The request object
        :param resp: The response object
        
        """
        doc = req.context["doc"]
        auth = req.context["auth"]
        # Generate a user token, put it in the database, and sign it
        # I can be sure that username already exists thanks to the pre request hook
        username = auth["username"]
        client_id = auth["origin_client_id"]
        # Check that there's a scope object in the request and check it against a list of allowed scopes
        if "scope" in doc.keys():
            scope = doc["scope"]
            # Assert that the client and user both exist
            session = db.session()
            clients = session.run("MATCH (c:Client {client_id: {client_id}}) return (c)",
                                  {"client_id": client_id})
            if clients:
                # Get the callback url for the client and make a call to it
                client = clients[0]
                callback_url = client["callback_url"]
                # Use uuid4 for a random id.
                unsigned_id = str(uuid.uuid4())
                # Sign the id with a timestamp. When checking the key we'll check for a max age of 5 minutes
                signed_id = timestampsigner.sign(unsigned_id.encode('utf-8')).decode('utf-8')
                # Put the unsigned id and the scope in the database connected to the user
                # Once the client resubmits the access token, the AUTHORIZED relationship will be destroyed and
                # Replaced with a permanent USED one
                # TODO: do this in a transaction
                session.run("MATCH (u:User {username: {username}})"
                            "MATCH (c:Client {client_id: {client_id}})"
                            "CREATE (u)-[:AUTHORIZED {scope: {scope}, user_token: {auth_token}}]->(c)",
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
                                              "token": signed_id,
                                              "callback_url": callback_url}}
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


class Users:

    @falcon.before(hooks.session_auth)
    @falcon.before(hooks.client_can_change_settings)
    def on_put(self, req, resp):
        """
        Change user settings.
        Clients that have the settings_change hook can change any settings in the noncritical
        settings dictionary within a users profile

        All settings that can be changed with this request are NON-SENSITIVE!

        See the arguments.Setting class for how they are used
        
        :param req: 
        :param resp: 
        :return: 
        """
        doc = req.context["doc"]
        # Pull the session and the username from the request context, inserted by the session_auth hook
        session = req.context["session"]
        username = session.username
        # Assert that the "settings" key is included in the doc
        if "settings" in doc.keys():
            log.debug("Updating settings for user {}".format(username))
            change_settings = doc["settings"]
            # Find the user in the database
            session = db.session()
            users = session.run("MATCH (u:User {username: {username}})"
                                "return (u)",
                               {"username": username})
            user = users[0]
            user_settings = user["settings"]
            updated_settings = user_settings
            changed_settings = 0
            new_settings = 0
            for setting, setting_value in change_settings.items():
                if setting in user_settings.keys():
                    changed_settings += 1
                    log.debug("Updating setting {0} for user {1} from {2} to {3}".format(
                        setting, username, user_settings[setting], setting_value
                    ))
                    updated_settings[setting] = setting_value
                else:
                    new_settings += 1
                    log.debug("Creating setting {0} with value {1} for user {2}".format(
                        setting, setting_value, username
                    ))
                    updated_settings.update({setting: setting_value})
            # Persist the settings into the database
            log.info("Updating settings for user {0}. Changing {1} settings and creating {2} for a total of {3} "
                     "changes".format(username, changed_settings, new_settings, changed_settings+new_settings
            ))
            session.run("MATCH (u:User {username: {username}})"
                        "SET u.settings={settings}",
                        {"username": username,
                         "settings": updated_settings})
            session.close()
        else:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "SETTINGS_KEY_NOT_FOUND",
                        "text": "The settings data key must be included in a request to this method",
                        "status": resp.status
                    }]
            }

    @falcon.before(hooks.client_can_read_settings)
    @falcon.before(hooks.session_auth)
    def on_get(self, req, resp):
        """
        Get information about a user
        
        :param req: 
        :param resp: 
        """
        auth = req.context["auth"]
        username = auth["username"]
        log.debug("Fetching data about user {}".format(username))
        # Start a db session and return nonsensitive user data
        session = db.session()
        matching_users = session.run("MATCH (u:User {username:{username}})"
                                     "return (u)",
                                     {"username": username})
        session.close()
        # We know the user exists because they passed the client user auth hook
        user = matching_users[0]
        user_fields = ["first_name", "last_name", "username", "email", "settings"]
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
        session = db.session()
        # Delete the user in the database
        session.run("MATCH (u:User {username: {username}})"
                    "DETACH DELETE (u)",
                    {"username": username})
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
            session = db.session()
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
                final_token = str(uuid.uuid4())
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

class Commands:
    @falcon.before(hooks.session_auth)
    def on_post(self, req, resp):
        """
        
        :param req: 
        :param resp: 

        """
        auth = req.context["auth"]
        doc = req.context["doc"]
        signed_session_id = auth["session_id"]
        # Try to unsign the session is, throw an error if it's invalid
        try:
            session_id = signer.unsign(signed_session_id)
            # Check to see if the session id is valid
            if session_id in sessions.sessions.keys():
                session = sessions.sessions[session_id]
                if "command" in doc.keys():
                    command = doc["command"]
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
            else:
                resp.status = falcon.HTTP_UNAUTHORIZED
                req.context["result"] = {
                    "errors":
                        [{
                            "type": "error",
                            "text": "Session id {} is invalid. If it was previously valid, "
                                    "it might have expired. Please request a new one.".format(signed_session_id),
                            "id": "SESSION_ID_INVALID",
                            "status": resp.status
                        }]
                }
        except BadSignature:
            resp.status = falcon.HTTP_UNAUTHORIZED
            req.context['result'] = {
                "errors":
                    [{
                        "type": "error",
                        "text": "Session id {} had an invalid signature".format(signed_session_id),
                        "status": resp.status,
                        "id": "SESSION_ID_BAD_SIGNATURE"
                    }]
            }


class Clients:
    @falcon.before(hooks.client_is_official)
    @falcon.before(hooks.origin_client_auth)
    def on_get(self, req, resp):
        """
        On a request from an official client, return data about the client.
        :param req: , 
        :param resp:  
        """
        auth = req.context["auth"]
        origin_client_id = auth["origin_client_id"]
        # Match the client in the database
        session = db.session()
        clients = session.run("MATCH (c:Client {client_id: {client_id}} return (c)", {"client_id": origin_client_id})
        client = clients[0]
        client_callback = client["callback_url"]
        # Get the number of users that use it
        users = session.run("MATCH (c:Client {client_id: {client_id})"
                            "MATCH (u)-[:USES]->(c)"
                            "return (u)",
                            {"client_id": origin_client_id})
        user_num = len(users)
        req.context["result"] = {"data":
                                     {"user_num": user_num,
                                      "id": "CLIENT_DATA_FETCHED",
                                      "text": "Client {0} has a callback url of {1}, and has {2} users.".format(
                                          origin_client_id, client_callback, user_num
                                      )}}
        session.close()

    @falcon.before(hooks.client_is_official)
    @falcon.before(hooks.origin_client_auth)
    def on_delete(self, req, resp):
        """
        Delete a client
        Preconditions: The request is coming from an official client, and the other client has authenticated
        :param req: 
        :param resp: 
        """
        auth = req.context["auth"]
        client_id = auth["origin_client_id"]
        log.debug("Deleting client {}".format(client_id))
        # Start a neo4j session
        session = db.session()
        try:
            session.run("MATCH (c:Client {client_id: {client_id}},"
                        "detach"
                        "delete (c)",
                        {"client_id": client_id})
            req.context["result"] = {
                "data":
                    {"type": "success",
                     "id": "CLIENT_DELETED",
                     "text": "Successfully deleted client {}".format(client_id)}
            }
        # No matter what, close the session
        finally:
            session.close()

    @falcon.before(hooks.client_is_official)
    def on_post(self,req, resp):
        """
        Create a client.
         The hooks before the function makes sure that the client has permission to do this
         Request structure:
         {
            "new_client": 
                {
                    "id": new_client_id,
                    "scope": new_client_scope,
        }
        
        Scope and client id will be validated and if it's successful, the response will include a client secret
        """
        doc = req.context["doc"]
        auth = req.context["auth"]
        if "new_client" in doc.keys():
            data = doc["new_client"]
            # Validate the data inside the request
            required_fields = {
                "id": str,
                "scope": str
            }
            error_cause = None
            try:
                for field in required_fields:
                    error_cause = field
                    assert type(data[field]) == required_fields[field]
            except (KeyError, AssertionError):
                log.debug("{0} caused create client request to fail. Request originated from client {1}".format(
                    error_cause, auth["client_id"]
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
            id = data["id"]
            scope = data["scope"]
            # Check if the submitted id is already in the database
            session = db.session()
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
                        raw_secret_key = str(uuid.uuid4())
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