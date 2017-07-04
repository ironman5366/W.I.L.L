# Builtin imports
import logging
import uuid
import datetime

# Internal imports
from will.API import hooks
from will.userspace import sessions
from will import tools
from will.schema import *
import will

# External imports
import falcon
from itsdangerous import BadSignature, BadTimeSignature
import bcrypt
import validators

log = logging.getLogger()

db = None
timestampsigner = None
signer = None

# Refreshed by API/__init__.py after routes are processed.
start_time = datetime.datetime.now()

api_version = "1"

# TODO: use the db with transactions!


class APIStatus:
    """
    Output the basic status of the API
    """

    @property
    def report(self):
        """
        Generate an uptime report
        """
        time_run = (datetime.datetime.now()-start_time).total_seconds()
        report_str = "API version {0} running on W.I.L.L version {1}, up for {2} seconds,".format(
            api_version, will.version, time_run)
        report_data = {
            "data":
                {
                    "type": "success",
                    "id": "GENERATED_REPORT",
                    "text": report_str
                }
        }
        return report_data

    def on_get(self, req, resp):
        req.context["result"] = self.report


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

    @falcon.before(hooks.client_is_official)
    @falcon.before(hooks.user_auth)
    def on_delete(self, req, resp):
        """
        As an authenticated user, terminate a relationship with a client, using an official interface
        """
        step_rels = ["user_token", "access_token"]
        if self._step_id in step_rels:
            auth = req.context["auth"]
            auth_keys = auth.keys()
            if "origin_client_id" in auth_keys:
                if "client_id" in auth_keys:
                    client_id = auth["origin_client_id"]
                    session = db()
                    user_rels = session.query(Association).filter_by(username=auth["username"], client_id=client_id).one_or_none()
                    if user_rels:
                        # Delete the relationship
                        session.delete(user_rels)
                        session.commit()
                        req.context["result"] = {
                            "data":
                                {
                                    "type": "success",
                                    "text": "Deleted relationship between user {0} and client {1}".format(
                                        auth["username"],
                                        client_id),
                                    "id": "USER_CLIENT_REL_DELETED"
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
                else:
                    resp.status = falcon.HTTP_BAD_REQUEST
                    req.context["result"] = {
                        "errors":
                            [{
                                "type": "error",
                                "id": "CLIENT_ID_NOT_FOUND",
                                "text": "A DELETE request to this method must include a client id",
                                "status": resp.status
                            }]
                    }
            else:
                resp.status = falcon.HTTP_BAD_REQUEST
                req.context["result"] = {
                    "errors": [{
                        "type": "error",
                        "id": "ORIGIN_CLIENT_ID_NOT_FOUND",
                        "text": "A DELETE method to this request must include a data/origin_client_id key",
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
        """
        auth = req.context["auth"]
        if "user_token" in auth.keys():
            signed_auth_token = auth["user_token"]
            username = auth["username"]
            # Make sure the user exists
            session = db()
            # Check if an AUTHORIZED relationship exists between the user and the client

            user_rels = session.query(Association).filter_by(username=auth["username"],
                                                             client_id=auth["origin_client_id"]).one_or_none()
            if user_rels:
                rel = user_rels.user_token
                # Validation
                log.debug("Starting client connection process for client {0} and user {1}".format(
                    auth["origin_client_id"], username
                ))
                try:
                    # Check the signature with a 5 minute expiration
                    unsigned_auth_token = timestampsigner.unsign(signed_auth_token, 300).decode('utf-8')
                    log.debug("Token for user {0} provided by client {1} unsigned successfully".format(
                        username, auth["client_id"]
                    ))
                    if bcrypt.checkpw(unsigned_auth_token.encode('utf-8'), rel.encode('utf-8')):
                        log.info("Token check successful. Permanently connecting user {0} and client"
                                  " {1}".format(username, auth["client_id"]))
                        # Generate a secure token, sign it, and encrypt it in the database
                        final_token = str(uuid.uuid4())
                        # Sign the unencrypted version for the client
                        signed_final_token = (signer.sign(final_token.encode('utf-8'))).decode('utf-8')
                        # Encrypt it and put in the database
                        encrypted_final_token = bcrypt.hashpw(
                            signed_final_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        user_rels.access_token = encrypted_final_token
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
                    user_rels.user_token = None
                    session.commit()

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
            session = db()
            client = session.query(Client).filter_by(client_id=client_id).one_or_none()
            if client:
                # Use uuid4 for a random id.
                unsigned_id = str(uuid.uuid4())
                # Sign the id with a timestamp. When checking the key we'll check for a max age of 5 minutes
                signed_id = timestampsigner.sign(unsigned_id.encode('utf-8'))
                # Put the unsigned id and the scope in the database connected to the user
                a = Association(user_token=unsigned_id, scope=scope)
                user = session.query(User).filter_by(username=username).one_or_none()
                client = session.query(Client).filter_by(client_id=client_id).one_or_none()
                a.user = user
                a.client = client
                client.users.append(a)
                session.commit()
                req.context["result"] = {"data":
                                             {"id": "USER_AUTHORIZATION_TOKEN",
                                              "type": "success",
                                              "token": signed_id}
                                         }
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
            session = db()
            user = session.query(User).filter_by(username=username).one_or_none()
            user_settings = user.settings
            updated_settings = user_settings
            changed_settings = 0
            new_settings = 0

            def throw_validation_error(s):
                resp.status = falcon.HTTP_BAD_REQUEST
                req.context["result"] = {
                    "errors": [{
                        "type": "error",
                        "id": "SETTING_{}_INVALID".format(s.upper()),
                        "text": "Submitted setting {} failed validation".format(s),
                        "status": resp.status
                    }]
                }

            for setting, setting_value in change_settings.items():
                if setting in user_settings.keys():
                    if setting == "location":
                        if not tools.location_validator(setting_value):
                            # Throw a validation error
                            throw_validation_error(setting)
                            return
                    elif setting == "email":
                        if not validators.url(setting_value):
                            # Throw a validation error
                            throw_validation_error(setting)
                            return
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
                     "changes".format(username, changed_settings, new_settings, changed_settings + new_settings
                                      ))
            user.settings = updated_settings
            session.commit()
            # Rebuild session
            user_session = req.context["session"]
            user_session.reload()
            req.context["result"] = {
                "data":
                    {
                        "id": "SETTINGS_CHANGE_SUCCESSFUL",
                        "type": "success",
                        "text": "Successfully changed settings for user {}".format(username)
                    }
            }
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
            
    @falcon.before(hooks.param_username_decode)
    @falcon.before(hooks.client_can_read_settings)
    def on_get(self, req, resp, username):
        """
        Get information about a user
        
        :param req: 
        :param resp: 
        """
        log.debug("Fetching data about user {}".format(username))
        # Start a db session and return nonsensitive user data
        session = db()
        user = session.query(User).filter_by(username=username).one_or_none()
        # We know the user exists because they passed the client user auth hook
        user_data = {}
        # Put the users data into a dictionary that will be returned in a "data" key
        user_data.update({
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "username":  user.username,
            "settings": user.settings
        })
        req.context["result"] = {
            "data":
                {
                    "type": "success",
                    "id": "USER_DATA_FETCHED",
                    "text": "Fetched user data for user {}".format(username),
                    "user_data": user_data
                }
        }

    @falcon.before(hooks.client_is_official)
    @falcon.before(hooks.user_auth)
    def on_delete(self, req, resp):
        """
        Delete a user
        """
        # Check if the user exists
        session = db()
        auth = req.context["auth"]
        username = auth["username"]
        log.info("Deleting user {}".format(username))
        # End all the users sessions
        for session in sessions.sessions.values():
            if session.username == username:
                session.logout()
        user = session.query(User).filter(username=username).one_or_none()
        # Delete the user in the database
        session.delete(user)
        session.commit()
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
        """
        doc = req.context["doc"]
        data_keys = doc.keys()
        required_fields = {
            "username": str,
            "password": str,
            "first_name": str,
            "last_name": str,
            "settings": dict
        }
        field_errors = []
        # Required settings
        required_settings = {
            "location": tools.location_validator,
            "email": validators.email
        }
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
                # After validating that settings exist in the doc and is a dict, validate that
                # the required settings exist
                elif field == "settings":
                    for setting in required_settings:
                        # If it doesn't exist, create the requisite error, and add it to field_errors
                        if setting not in doc["settings"].keys():
                            field_error = {
                                "type": "error",
                                "id": "REQUIRED_SETTING_{}_NOT_FOUND".format(setting.upper()),
                                "text": "A setting for {} must be provided for user creation".format(setting)
                            }
                            field_errors.append(field_error)
                        elif not required_settings[setting](doc["settings"][setting]):
                            field_error = {
                                "type": "error",
                                "id": "REQUIRED_SETTING_{}_INVALID".format(setting.upper()),
                                "text": "The {} setting failed the validation process".format(setting)
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
            session = db()
            # Check to see if the username already exists

            users_found = session.query(User).filter_by(username=doc["username"]).one_or_none()
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
                hashed_password = bcrypt.hashpw(doc["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                # Use oauth code to generate a access token for the official client.
                # Generate a secure token, sign it, and encrypt it in the database
                final_token = str(uuid.uuid4())
                # Sign the unencrypted version for the client
                signed_final_token = signer.sign(final_token.encode('utf-8')).decode('utf-8')
                # Encrypt it and put in the database
                encrypted_final_token = bcrypt.hashpw(final_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user = User(
                    username=doc["username"],
                    password=hashed_password,
                    first_name=doc["first_name"],
                    last_name=doc["last_name"],
                    settings=doc["settings"],
                    created=datetime.datetime.now(),
                )
                association = Association(access_token=encrypted_final_token, scope="admin")
                official_client = session.query(Client).filter_by(official=True).one()
                association.client = official_client
                user.clients.append(association)
                session.add(user)
                session.commit()
                req.context["result"] = {
                    "data":
                        {
                            "type": "success",
                            "text": "Successfully created user {}".format(doc["username"]),
                            "id": "USER_CREATED",
                            "access_token": signed_final_token
                        }
                }


class Sessions:
    @falcon.before(hooks.client_user_auth)
    def on_post(self, req, resp):
        """
        Create a session
        
        """
        # Doc will be used for dynamic variables
        doc = req.context["doc"]
        auth = req.context["auth"]
        username = auth["username"]
        client = auth["client_id"]
        # Instantiate a session class
        log.debug("Starting session for user {0} on client {1}, with dynamic data {2}"
                  "".format(username, client, doc))
        dynamic_acceptable = {"location": tools.location_validator}
        d_keys = dynamic_acceptable.keys()
        # Dynamic settings are optional
        if doc:
            doc_errors = []
            for k, v in doc.items():
                if k in d_keys:
                    if not dynamic_acceptable[k](v):
                        error = {
                            "type": "error",
                            "id": "DYNAMIC_{}_INVALID".format(k.upper()),
                            "text": "Submitted value for dynamic setting {} failed validation".format(k)
                        }
                        doc_errors.append(error)
            if doc_errors:
                req.context["result"] = {"errors": doc_errors}
                return
        session_class = sessions.Session(username, client, doc)
        # Sign the session id
        unsigned_session_id = session_class.session_id.encode('utf-8')
        session_id = signer.sign(unsigned_session_id).decode('utf-8')
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
        The session auth hook already confirms it exists
        :param req: 
        :param resp: 
        :param session_id:
        """
        # The session auth hook put this into req.context
        session = req.context["session"]
        session.logout()
        req.context["result"] = {
            "data":
                {
                    "type": "success",
                    "id": "SESSION_LOGGED_OUT",
                    "text": "Session {} has been ended".format(session.session_id)
                }
        }


class Commands:
    @falcon.before(hooks.session_auth)
    def on_post(self, req, resp):
        """
        
        :param req: 
        :param resp: 

        """
        doc = req.context["doc"]
        session = req.context["session"]
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


class Clients:
    @falcon.before(hooks.client_is_official)
    @falcon.before(hooks.origin_client_auth)
    def on_get(self, req, resp, origin_client_id):
        """
        On a request from an official client, return data about the client.
        :param req:
        :param resp:
        :param origin_client_id:
        """
        # Match the client in the database
        session = db()
        client = session.query(Client).filter_by(client_id=origin_client_id).one_or_none()
        # Get the number of users that use it
        user_num = len(client.users)
        req.context["result"] = {"data":
                                     {"user_num": user_num,
                                      "id": "CLIENT_DATA_FETCHED",
                                      "text": "Client {0} has {1} users.".format(
                                          origin_client_id, user_num
                                      )}}

    @falcon.before(hooks.client_is_official)
    @falcon.before(hooks.origin_client_auth)
    def on_delete(self, req, resp, *args):
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
            client = session.filter_by(client_id=client_id).one_or_none()
            session.delete(client)
            session.commit()
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
    def on_post(self, req, resp, *args):
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
        }
        
        Scope and client id will be validated and if it's successful, the response will include a client secret
        """
        reserved_client_ids = ["internal"]
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
                            "status": resp.status,
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
            if id not in reserved_client_ids:
                scope = data["scope"]
                # Check if the submitted id is already in the database
                session = db()
                matching_clients = session.query(Client).filter_by(client_id=id).all()
                # If a client with that name already exists:
                if matching_clients:
                    resp.status = falcon.HTTP_CONFLICT
                    req.context["result"] = {
                        "errors":
                            [{
                                "type": "error",
                                "id": "CLIENT_ID_ALREADY_EXISTS",
                                "status": resp.status,
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
                            raw_secret_key = str(uuid.uuid4()).encode('utf-8')
                            # Hash the key. This version will be put in the database
                            hashed_secret_key = bcrypt.hashpw(raw_secret_key, bcrypt.gensalt())
                            # Sign the key. This version will be returned to the user
                            signed_secret_key = signer.sign(raw_secret_key).decode('utf-8')
                            # Put the client in the database
                            new_client = Client(client_id=id, client_secret=hashed_secret_key, official=False)
                            session.add(new_client)
                            session.commit()
                            log.debug("Created client {} in database".format(id))
                            # Return the data to the user
                            req.context["result"] = {
                                "data": {
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
                            "id": "CLIENT_ID_RESERVED",
                            "status": resp.status,
                            "type": "error",
                            "text": "Client id {0} is used in examples or internal functions "
                                    "and cannot be registered".format(id)
                        }]
                }
        else:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "id": "NEW_CLIENT_NOT_FOUND",
                        "status": resp.status,
                        "type": "error",
                        "text": '"new_client" key with client information not found'
                    }]
            }
