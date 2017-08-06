# Builtin imports
from unittest.mock import *
import unittest
import uuid
import datetime

# External imports
import falcon
import bcrypt
from itsdangerous import TimestampSigner, Signer
from sqlalchemy.orm import sessionmaker

# Internal imports
from will.API import v1, hooks
from will.userspace import sessions
from will.schema import *
import create_db

timestamp_signer = None
signer = None
s_key = create_db.db_init(None, None, None, None, "super-secret", "web-official", debug=True)
engine = create_db.engine
db = sessionmaker(bind=engine)

def basic_session(session_id=None,
                  client_id="rocinate",
                  username="holden",
                  session_command=None,
                  created=None,
                  last_reloaded=None):
    """
    Make a MagicMock() object representing a standard session

    :param session_id: The uuid representing the session. Automatically generated if not defined.
    :param client_id: The client that started the session
    :param username: The user that the client is for
    :param session_command: The callable representing the session.command() method. If the passed value is not a
        callable, a function will be created to return that value. If it's not defined, it will be passed as a
        MagicMock returning None
    :param created: The datetime object representing when the session was created. If not specified, generated with
        datetime.datetime.now()
    :param last_reloaded: The datetime object representing when the session was last refreshed. If not specified,
        generated with datetime.datetime.now()
    :return session_mock: A MagicMock() object with all of the relevant attributes
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    if session_command:
        if not callable(session_command):
            s = session_command

            def session_command(_):
                return s
    else:
        session_command = MagicMock(return_value=None)
    if not created:
        created = datetime.datetime.now()
    if not last_reloaded:
        last_reloaded = datetime.datetime.now()

    session_mock = MagicMock()
    session_mock.session_id = session_id
    session_mock.command = session_command
    session_mock.client_id = client_id
    session_mock.username = username
    session_mock.created = created
    session_mock.last_reloaded = last_reloaded

    return session_mock


def basic_user(
        username="holden",
        password="password",
        first_name="James",
        last_name="Holden",
        admin=False,
        settings=None,
        encrypt_pw=True, ):
    """
    A method to create a standard user

    :param username: The username of the user
    :param password: The password of the user
    :param first_name: The first name of the user
    :param last_name: The last name of the user
    :param settings: The users settings
    :param encrypt_pw: A bool defining whether or not to hash the users password with the standard hashing algo
    :return user: An instantiated schema.User class
    """
    if encrypt_pw:
        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if settings is None:
        settings = {
            "email": "will@willbeddow.com",
            "location":
                {
                    "latitude": 44.970468,
                    "longitude": -93.262148
                },
            "temp_unit": "C",
            "timezone": "US/Eastern"
        }
    return User(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        settings=settings,
        admin=admin)


def basic_client(
        client_id="rocinate",
        official=False,
        client_secret=None,
        hash_secret=True,
        scope="command",
        validate_scope=True):
    """
    Generate a client with standard settings

    :param client_id: The clients unique identifier
    :param official: A bool defining whether the client is official
    :param client_secret: The secret key for the client. Will be automatically generated if left as none
    :param hash_secret: A bool defining whether to hash the clients secret key with the standard hashing algo
    :param scope: The scope of the rel
    :param validate_scope: A bool defining whether the scope should be automatically validated
    :return client: An instantiated schema.Client
    """
    if client_secret is None:
        client_secret = 'client-secret-key'
    if hash_secret:
        client_secret = bcrypt.hashpw(client_secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if validate_scope:
        assert scope in hooks.scopes.keys()
    client = Client(client_id=client_id, client_secret=client_secret, scope=scope, official=official)
    return client


def basic_assoc(user=None, client=None, stage="access", token="token", hashtoken=True, scope="command"):
    """
    Create a basic schema.Association object

    :param user: The user of the association. Of type schema.User
    :param client: The client of the association. Of type schema.Client
    :param stage: The stage of the association. Either "access" or "user"
    :param token: The actual token to use.
    :param hashtoken: A bool defining whether to hash the token with bcrypt
    :param scope: The scope of the relationship
    :return assoc: An instantiated Association object
    """
    if not user:
        user = basic_user()
    if not client:
        client = basic_client()
    assert stage in ["access", "user"]
    if hashtoken:
        token = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if stage == "access":
        assoc = Association(access_token=token, scope=scope)
    else:
        assoc = Association(user_token=token, scope=scope)
    assoc.user = user
    client.users.append(assoc)
    return assoc


class DBTest(unittest.TestCase):
    def setUp(self):
        self.session = db()
        self.session.commit()
        self.session.begin_nested()
        hooks.db = MagicMock(return_value=self.session)
        v1.db = MagicMock(return_value=self.session)

    def tearDown(self):
        self.session.rollback()
        self.session.close()


def mock_request(auth={}, doc={}, **kwargs):
    """
    Create a mock request object with an appropriate request context

    :param auth: The optional req.context["auth"] object
    :param doc: The optional req.context["doc"] object
    :param kwargs: Any other args that should be submitted inside the request context
    :return base_class: The final request object
    """
    base_class = MagicMock()
    base_class.context = {}
    base_class.context.update({"auth": auth})
    base_class.context.update({"doc": doc})
    base_class.context.update(kwargs)
    return base_class


class APIStatusTests(unittest.TestCase):
    instance = v1.APIStatus()

    def test_api_status(self):
        resp = MagicMock()
        req = mock_request()
        self.instance.on_get(req, resp)
        self.assertEqual(req.context["result"]["data"]["id"], "GENERATED_REPORT")


class Oauth2StepTests(DBTest):
    instance = v1.Oauth2Step()

    @classmethod
    def setUpClass(cls):
        global signer
        global timestamp_signer
        if not signer:
            signer = Signer("super-secret")
            hooks.signer = signer
        if not timestamp_signer:
            timestamp_signer = TimestampSigner("super-secret")
            v1.timestampsigner = timestamp_signer

    def test_post(self):
        """
        Send a post request to the base post and assert that a not implemented error is raised
        """
        req = mock_request()
        resp = MagicMock()
        with self.assertRaises(NotImplementedError):
            self.instance.on_post(req, resp)

    def test_successful_delete(self):
        """
        Test a successful delete call to remove authentication between a user and client
        """
        # If the Oauth2Step has a step id, assert that it passes correctly.
        if self.instance._step_id:
            # Mock the multi step hooks
            # Create a user and a client, and a fake association
            user = basic_user()
            self.session.add(user)
            client = basic_client()
            raw_token_val = "token"
            hashed_token = bcrypt.hashpw(raw_token_val.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            if self.instance._step_id == "user_token":
                assoc = Association(user_token=hashed_token)
                signed_token = timestamp_signer.sign(raw_token_val.encode('utf-8')).decode('utf-8')
            else:
                assoc = Association(access_token=hashed_token)
                signed_token = signer.sign(raw_token_val.encode('utf-8')).decode('utf-8')
            assoc.client = client
            user.clients.append(assoc)
            auth = {
                self.instance._step_id: signed_token,
                "client_id": "web-official",
                "client_secret": s_key,
                "origin_client_id": "rocinate",
                "origin_client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
                "username": "holden",
                "password": "password"
            }
            # Pretend that the user exists
            fake_request = mock_request(auth=auth)
            # Assert that the rel is gone from the db
            self.session.begin_nested()
            self.instance.on_delete(fake_request, MagicMock())
            assoc_query = self.session.query(Association).filter_by(username="holden", client_id="rocinate").one_or_none()
            self.session.rollback()
            self.assertIsNone(assoc_query)
            # Check the result from the request object
            self.assertEqual(fake_request.context["result"]["data"]["type"], "success")
        # If no step id is found, assert that the step id is properly flagged as incorrect
        else:
            user = basic_user()
            self.session.add(user)
            client = basic_client(client_id="rocinate", client_secret="client-secret-key")
            self.session.add(client)
            auth = {
                "client_id": "web-official",
                "client_secret": s_key,
                "username": "holden",
                "password": "password",
                "origin_client_id": "rocinate",
                "origin_client_secret": "client-secret-key"
            }
            fake_request = mock_request(auth=auth)
            self.instance.on_delete(fake_request, MagicMock())
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "STEP_ID_NOT_FOUND")

    def test_missing_rel_delete(self):
        """
        Test an otherwise correct delete request where the relationship between the user and client couldn't be
        found, and assert that the correct error is raised
        """
        if self.instance._step_id:
            # Mock the multi step hooks
            # Mock a client_id and username
            user = basic_user()
            self.session.add(user)
            client = basic_client()
            self.session.add(client)
            raw_token_val = "client-secret-key"
            signed_token = signer.sign(raw_token_val.encode('utf-8')).decode('utf-8')
            auth = {
                self.instance._step_id: signer.sign(signed_token.encode('utf-8')).decode('utf-8'),
                "client_id": "web-official",
                "client_secret": s_key,
                "origin_client_id": "rocinate",
                "origin_client_secret": signed_token,
                "username": "holden",
                "password": "password"
            }
            # Pretend that the user exists
            fake_request = mock_request(auth=auth)
            # Assert that the rel is gone from the db
            assoc_query = self.session.query(Association).filter_by(username="holden",
                                                                    client_id="rocinate").one_or_none()
            self.assertIsNone(assoc_query)
            fake_response = MagicMock()
            self.instance.on_delete(fake_request, fake_response)
            # Check the result from the request object
            print(fake_request.context["result"])
            self.assertEqual(fake_response.status, falcon.HTTP_NOT_FOUND)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USER_CLIENT_REL_NOT_FOUND")
        else:
            self.assert_(True)


class Oauth2AccessTokenTests(Oauth2StepTests):
    instance = v1.AccessToken()

    def test_post(self):
        """
        Test the creation of a permanent access token, based on a temporary signed user token
        :return:
        """
        user = basic_user()
        self.session.add(user)
        client = basic_client()
        basic_assoc(user=user, client=client, stage="user")
        self.session.add(client)
        mock_user_token = "token".encode('utf-8')
        # Timestamp sign the user token_
        signed_mock_user_token = timestamp_signer.sign(mock_user_token).decode('utf-8')
        # Password is the hash of 'tachi'
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "origin_client_id": "rocinate",
            "origin_client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "user_token": signed_mock_user_token,
            "username": "holden",
            "password": "password"
        }
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        self.session.begin_nested()
        self.instance.on_post(fake_request, MagicMock())
        self.session.rollback()
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_ACCESS_TOKEN")
        self.assert_("token" in fake_request.context["result"]["data"].keys())

    def test_post_mismatched_user_token(self):
        """
        Submit a request with an incorrect user token, and assert that the correct error is thrown
        """
        user = basic_user(password="super-secret-password")
        self.session.add(user)
        client = basic_client(client_secret="super-secret-client")
        raw_token_val = "token"
        hashed_token = bcrypt.hashpw(raw_token_val.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        assoc = Association(user_token=hashed_token)
        # signed_token = timestamp_signer.sign(raw_token_val, 300)
        assoc.client = client
        user.clients.append(assoc)
        mock_user_token = timestamp_signer.sign("aa5cacc7-9d91-471a-a5ac-aebc2c30a9d2").decode('utf-8')
        # Mock authentication without signing the token
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "user_token": mock_user_token,
            "username": user.username,
            "password": "super-secret-password",
            "origin_client_id": client.client_id,
            "origin_client_secret": signer.sign("super-secret-client".encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth)
        # Mock authentication
        # Submit a request to the instance, and assert that the correct data is returned
        fake_response = MagicMock()
        self.session.begin_nested()
        self.instance.on_post(fake_request, fake_response)
        self.session.rollback()
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "AUTH_TOKEN_MISMATCHED")
        self.assertEqual(fake_response.status, falcon.HTTP_FORBIDDEN)

    def test_bad_signature_token(self):
        """
        Submit a request with a token that's not signed and assert that the correct error is raised. The behavior
        should be identical for an expired token
        """
        user = basic_user(password="super-secret-password")
        self.session.add(user)
        client = basic_client(client_secret="super-secret-client")
        raw_token_val = "token"
        hashed_token = bcrypt.hashpw(raw_token_val.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        assoc = Association(user_token=hashed_token)
        # signed_token = timestamp_signer.sign(raw_token_val, 300)
        assoc.client = client
        user.clients.append(assoc)
        mock_user_token = "aa5cacc7-9d91-471a-a5ac-aebc2c30a9d2"
        # Mock authentication without signing the token
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "user_token": mock_user_token,
            "username": user.username,
            "password": "super-secret-password",
            "origin_client_id": client.client_id,
            "origin_client_secret": signer.sign("super-secret-client".encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        fake_response = MagicMock()
        self.session.begin_nested()
        self.instance.on_post(fake_request, fake_response)
        self.session.rollback()
        self.session.commit()
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "AUTH_TOKEN_INVALID")
        self.assertEqual(fake_response.status, falcon.HTTP_FORBIDDEN)


    def test_no_rel_found(self):
        """
        Submit a seemingly valid request, but don't mock the db returning a valid relationship, and assert that
        the correct error ris raised.
        """
        user = basic_user()
        self.session.add(user)
        client = basic_client()
        self.session.add(client)
        raw_token_val = "client-secret-key"
        signed_token = signer.sign(raw_token_val.encode('utf-8')).decode('utf-8')
        auth = {
            "user_token": signed_token,
            "client_id": "web-official",
            "client_secret": s_key,
            "origin_client_id": "rocinate",
            "origin_client_secret": signed_token,
            "username": "holden",
            "password": "password"
        }
        # Pretend that the user exists
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        fake_response = MagicMock()
        self.instance.on_post(fake_request, fake_response)
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USER_NOT_AUTHORIZED")
        self.assertEqual(fake_response.status, falcon.HTTP_UNAUTHORIZED)


class Oauth2UserTokenTests(Oauth2StepTests):
    instance = v1.UserToken()

    def test_post(self):
        client = basic_client()
        self.session.add(client)
        user = basic_user()
        self.session.add(user)
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "origin_client_id": "rocinate",
            "origin_client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "username": "holden",
            "password": "password"
        }
        doc = {
            "scope": "command"
        }
        fake_request = mock_request(auth=auth, doc=doc)
        # Submit a request to the instance, and assert that the correct data is returned
        self.session.begin_nested()
        self.instance.on_post(fake_request, MagicMock())
        self.session.rollback()
        self.assertEqual(fake_request.context["result"]["data"]["id"], "USER_AUTHORIZATION_TOKEN")
        self.assert_("token" in fake_request.context["result"]["data"].keys())


    def test_missing_scope(self):
        """
        Submit a request without a scope attached, and assert that the correct error is raised
        :return:
        """
        user = basic_user()
        self.session.add(user)
        client = basic_client()
        self.session.add(client)
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "origin_client_id": "rocinate",
            "origin_client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "username": "holden",
            "password": "password"
        }
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_NOT_FOUND")


class UsersTests(DBTest):
    instance = v1.Users()

    def setUp(self):
        super().setUp()
        global signer
        global timestamp_signer
        if not signer:
            signer = Signer("super-secret")
            hooks.signer = signer
        if not timestamp_signer:
            timestamp_signer = TimestampSigner("super-secret")
            v1.timestampsigner = timestamp_signer

    def test_on_put_settings_not_found(self):
        """
        Submit a request to change the settings without a settings key in the request data, and assert that the correct
        error is thrown
        """
        # Mock out session auth and and client that can change settings
        s = basic_session()
        sessions.sessions.update({s.session_id: s})
        u = basic_user()
        c = basic_client(scope="settings_change")
        a = basic_assoc(user=u, client=c, scope="settings_change")
        self.session.add(u)
        self.session.add(c)
        auth = {
            "username": "holden",
            "password": "password",
            "client_id": "rocinate",
            "client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "session_id": signer.sign(s.session_id.encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth, doc={})
        fake_response = MagicMock()
        # Assert that the correct error is thrown for the doc not including a settings key
        self.instance.on_put(fake_request, fake_response)
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SETTINGS_KEY_NOT_FOUND")

    def test_on_put_success(self):
        """
        Submit a successful mocked request to change the settings, and assert that it passes
        """
        s = basic_session()
        sessions.sessions.update({s.session_id: s})
        u = basic_user()
        c = basic_client(scope="settings_change")
        a = basic_assoc(user=u, client=c, scope="settings_change")
        self.session.add(u)
        self.session.add(c)
        doc = {
            "settings":
                {
                    "email": "will.beddow@gmail.com",
                    "new_setting": "newsettingvalue"
                }
        }
        auth = {
            "client_id": "rocinate",
            "client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "username": "holden",
            "password": "password",
            "session_id": signer.sign(s.session_id.encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth, doc=doc)
        fake_response = MagicMock()
        self.session.begin_nested()
        self.instance.on_put(fake_request, fake_response)
        self.session.rollback()
        self.assert_(True)

    def test_on_get_success(self):
        """
        Test a successful request to read a users settings.
        Note: This method does not require any other tests, because all mitigating conditions and factors are removed
        by the hooks and middleware before it
        """
        s = basic_session()
        sessions.sessions.update({s.session_id: s})
        u = basic_user()
        c = basic_client(scope="settings_read")
        a = basic_assoc(user=u, client=c, scope="settings_read")
        self.session.add(u)
        self.session.add(c)
        auth = {
            "username": "holden",
            "password": "password",
            "client_id": "rocinate",
            "client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "session_id": signer.sign(s.session_id.encode('utf-8')).decode('utf-8'),
            "access_token": signer.sign("token".encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth)
        fake_response = MagicMock()
        self.instance.on_get(fake_request, fake_response, username="holden")
        self.assert_(True)

    def test_on_delete_success(self):
        """
        Test a successful request to delete a user from the database.
        Note: This method does nto require any other tests, because all mitigating conditions and factors are removed
        by the hooks and middleware before it
        """
        user = basic_user()
        self.session.add(user)
        # Mock a session
        s = basic_session()
        # Put the session into sessions.sessions
        sessions.sessions.update({s.session_id: s})
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "session_id": signer.sign(s.session_id.encode('utf-8')).decode('utf-8'),
            "username": "holden",
            "password": "password"
        }
        fake_request = mock_request(auth=auth)
        # Call the method
        self.session.begin_nested()
        self.instance.on_delete(fake_request, MagicMock())
        self.session.rollback()
        # Assert that the logout() method was called of the fake session
        s.logout.assert_any_call()

    def test_on_post_success(self):
        """
        Test a successful request to create a user
        """
        # The required information to create a user
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings":
                {
                    "location":
                        {
                            "latitude": 44.970468,
                            "longitude": -93.262148
                        },
                    "email": "holden@rocinate.opa"
                }
        }
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        fake_request = mock_request(auth=auth, doc=doc)
        # Call the method
        self.session.begin_nested()
        self.instance.on_post(fake_request, MagicMock())
        self.session.rollback()
        self.assertEqual(fake_request.context["result"]["data"]["id"], "USER_CREATED")

    def test_on_post_required_setting_not_found(self):
        """
        Submit an otherwise correct request to create a new user that does not include one of the required settings
        defined in the method (e.g. location or email). Assert that the proper error is part of the field errors
        raised
        """
        # The required information to create a user, minus the "email" key in settings
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings":
                {
                    "location":
                        {
                            "latitude": 44.970468,
                            "longitude": -93.262148
                        }
                }
        }

        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        fake_request = mock_request(auth=auth, doc=doc)
        # Call the method
        self.session.begin_nested()
        self.instance.on_post(fake_request, MagicMock())
        self.session.rollback()
        # Confirm that an error was raised by the method
        self.assertIn("errors", fake_request.context["result"].keys())
        error_id = "REQUIRED_SETTING_EMAIL_NOT_FOUND"
        # Confirm that one of the errors raised by the method is the one we're looking for
        error_found = any([i["id"] == error_id for i in fake_request.context["result"]["errors"]])
        self.assertTrue(error_found)

    def test_post_invalid_field_type(self):
        """
        Submit an otherwise valid request to the method that has an invalid type for one of the required fields.
        Assert that the correct errors is among the errors raised
        """
        # Mock an official client
        # The required information to create a user, but with an invalid settings key
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings": "settings_str"
        }

        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        fake_request = mock_request(auth=auth, doc=doc)
        # Call the method
        self.instance.on_post(fake_request, MagicMock())
        # Confirm that an error was raised by the method
        self.assertIn("errors", fake_request.context["result"].keys())
        error_id = "FIELD_SETTINGS_INVALID_TYPE"
        # Confirm that one of the errors raised by the method is the one we're looking for
        error_found = any([i["id"] == error_id for i in fake_request.context["result"]["errors"]])
        self.assertTrue(error_found)

    def test_post_field_not_found(self):
        """
        Submit an otherwise valid request to the method, but don't include one of the required fields
        """
        # The required information to create a user, minus the settings key
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden"
        }
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        fake_request = mock_request(auth=auth, doc=doc)
        # Call the method
        self.instance.on_post(fake_request, MagicMock())
        # Confirm that an error was raised by the method
        self.assertIn("errors", fake_request.context["result"].keys())
        error_id = "FIELD_SETTINGS_NOT_FOUND"
        # Confirm that one of the errors raised by the method is the one we're looking for
        error_found = any([i["id"] == error_id for i in fake_request.context["result"]["errors"]])
        self.assertTrue(error_found)

    def test_post_user_already_exists(self):
        """
        Submit a valid post request, but mock that the user already exists, and assert that the correct error is raised
        """
        # The required information to create a user
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings":
                {
                    "location":
                        {
                            "latitude": 44.970468,
                            "longitude": -93.262148
                        },
                    "email": "holden@rocinate.opa"
                }
        }
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        user = basic_user()
        self.session.add(user)
        fake_request = mock_request(auth=auth, doc=doc)
        # Call the method
        self.session.begin_nested()
        self.instance.on_post(fake_request, MagicMock())
        self.session.rollback()
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USERNAME_ALREADY_EXISTS")


class SessionTests(DBTest):
    """
    Tests for the v1/sessions method
    """
    instance = v1.Sessions()
    _session_instance_copy = None

    def setUp(self):
        super().setUp()
        # Mock out the session class for the course of this
        self._session_instance_copy = sessions.Session

    def tearDown(self):
        super().tearDown()
        sessions.Session = self._session_instance_copy

    def test_on_post_success(self):
        """
        Test a successful request to create a session, and assert that it passes
        """
        u = basic_user()
        c = basic_client()
        a = basic_assoc(user=u, client=c)
        self.session.add(u)
        self.session.add(c)

        def session_test(username, client_id, _):
            # Check the username and client_id and create a MagicMock
            self.assertEqual(username, "holden")
            self.assertEqual(client_id, "rocinate")
            session_instance = MagicMock()
            session_instance.username = username
            session_instance.client_id = client_id
            session_instance.session_id = "my-session-id"
            return session_instance

        sessions.Session = MagicMock(side_effect=session_test)
        fake_request = mock_request(auth={
            "username": "holden",
            "password": "password",
            "client_id": "rocinate",
            "client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8'),
            "access_token": signer.sign("token".encode('utf-8')).decode('utf-8')
        })
        # Send the request
        self.instance.on_post(fake_request, MagicMock())
        self.assertIn("my-session-id", fake_request.context["result"]["data"]["session_id"])

    def test_session_id_on_delete(self):
        """
        Test the basic session delete method
        """
        s = basic_session()
        # Put the session id into sessions.sesssions
        sessions.sessions.update({s.session_id: s})
        auth = {
            "session_id": signer.sign(s.session_id.encode('utf-8')).decode('utf-8'),
            "client_id": "rocinate"
        }
        fake_request = mock_request(auth=auth)
        self.instance.on_delete(fake_request, MagicMock(), session_id=auth["session_id"])
        self.assertEqual(fake_request.context["result"]["data"]["id"], "SESSION_LOGGED_OUT")


class CommandTests(DBTest):
    """
    Test the /v1/commands methods
    """
    instance = v1.Commands()

    def setUp(self):
        super().setUp()
        global signer
        global timestamp_signer
        if not signer:
            signer = Signer("super-secret")
            hooks.signer = signer
        if not timestamp_signer:
            timestamp_signer = TimestampSigner("super-secret")
            v1.timestampsigner = timestamp_signer

    def test_post_success(self):
        """
        Test a successful basic command request, mocking out the session command behaivor
        """
        # Mock a session
        session_mock = basic_session(session_command={
            "data":
                {
                    "type": "success",
                    "id": "GENERIC_COMMAND_SUCCESSFUL",
                    "text": "command result!"
                }
        })
        # Put the session into `sessions.sessions`
        session_id = session_mock.session_id
        sessions.sessions.update({session_id: session_mock})
        # Sign the session_id
        signed_session_id = signer.sign(session_id.encode('utf-8')).decode('utf-8')
        auth = {
            "session_id": signed_session_id,
            "client_id": "rocinate"
        }
        doc = {
            "command": "my_command"
        }
        fake_request = mock_request(auth=auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "GENERIC_COMMAND_SUCCESSFUL")

    def test_post_no_command(self):
        """
        Submit a request without a command in the doc, and assert that the correct error is raised
        """
        # Mock a session
        session_mock = basic_session()
        # Put the session into `sessions.sessions`
        session_id = session_mock.session_id
        sessions.sessions.update({session_id: session_mock})
        # Sign the session_id
        signed_session_id = signer.sign(session_id.encode('utf-8')).decode('utf-8')
        auth = {
            "session_id": signed_session_id,
            "client_id": "rocinate"
        }
        # Mock a session
        fake_request = mock_request(auth=auth)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "COMMAND_NOT_FOUND")

class ClientTests(DBTest):
    """
    Tests for /v1/clients
    """
    instance = v1.Clients()

    def setUp(self):
        super().setUp()
        global signer
        global timestamp_signer
        if not signer:
            signer = Signer("super-secret")
            hooks.signer = signer
            v1.signer = signer
        if not timestamp_signer:
            timestamp_signer = TimestampSigner("super-secret")
            v1.timestampsigner = timestamp_signer

    def tearDown(self):
        super().tearDown()

    def test_on_get_success(self):
        """
        Test a successful request to the on_get method
        """
        client = basic_client()
        self.session.add(client)
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "origin_client_id": "rocinate",
            "origin_client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth)
        self.instance.on_get(fake_request, MagicMock(), origin_client_id="rocinate")
        print(fake_request.context["result"])
        self.assertEqual(fake_request.context["result"]["data"]["user_num"], 0)
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_DATA_FETCHED")

    def test_on_delete_success(self):
        """
        Test a successful request t the on_delete method
        """
        client = basic_client()
        self.session.add(client)
        auth = {
            "client_id": "web-official",
            "client_secret": s_key,
            "origin_client_id": "rocinate",
            "origin_client_secret": signer.sign("client-secret-key".encode('utf-8')).decode('utf-8')
        }
        fake_request = mock_request(auth=auth)
        self.instance.on_delete(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_DELETED")

    def test_on_post_success(self):
        """
        Test the successful creation of a client
        """
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "command"
            }
        }
        fake_request = mock_request(auth=auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_CREATED")
        # Assert that the client exists and then remove it from the database
        created_client = self.session.query(Client).filter_by(client_id="rocinate").one_or_none()
        self.assertIsNotNone(created_client)
        self.session.delete(created_client)
        self.session.commit()

    def test_post_unauthorized_scope(self):
        """
        Test an otherwise successful post request that tries to use a scope that it's not authorized too, and assert
        that the correct error is raised
        """
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "admin"
            }
        }
        fake_request = mock_request(auth=auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_NOT_AUTHORIZED")

    def test_post_client_already_exists(self):
        """
        Test an otherwise correct request to the on_post method, but mock that a client with that id already exists
        """
        # Put the client in the database
        client = basic_client()
        self.session.add(client)
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "command"
            }
        }
        fake_request = mock_request(auth=auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_ID_ALREADY_EXISTS")

    def test_post_invalid_data_type(self):
        """
        Submit a post request with an incorrect data type for one of the required keys, and assert that the correct
        error is raised
        """
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        doc = {
            "new_client": {
                "id": 1,
                "scope": "command"
            }
        }
        fake_request = mock_request(auth=auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "ID_INVALID")

    def test_post_no_client_information(self):
        """
        Test a request with no client information and assert that the correct error is raised
        """
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        fake_request = mock_request(auth=auth)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "NEW_CLIENT_NOT_FOUND")

    def test_post_invalid_scope(self):
        """
        Test a request with an invalid scope and assert that the correct error is raised
        """
        auth = {
            "client_id": "web-official",
            "client_secret": s_key
        }
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "definitely_not_valid"
            }
        }
        fake_request = mock_request(auth=auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_INVALID")