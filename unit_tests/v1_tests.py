# Builtin imports
from unittest.mock import *
import unittest
import uuid

# External imports
import falcon
import bcrypt
from itsdangerous import TimestampSigner, Signer

# Internal imports
from will.API import v1, hooks
from will.userspace import sessions

timestamp_signer = None
signer = None

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


def mock_session(return_value=None, side_effect=None, hook_return_value=None, hook_side_effect=None):
    """
    Reach into the v1 and the hook file and change it's `graph.session` class to a mock method that returns what the tests
    need it to return
    :param return_value: 

    """
    hooks.graph = MagicMock()
    hooks.graph.session = Mock
    if hook_side_effect:
        assert not hook_return_value
        hooks.graph.session.run = MagicMock(side_effect=hook_side_effect)
    elif hook_return_value:
        hooks.graph.session.run = MagicMock(return_value=hook_return_value)
    v1.db = MagicMock()
    v1.db.session = MagicMock
    if side_effect:
        # Give an option to return it with a side effect instead of a return value
        assert not return_value
        v1.db.session.run = MagicMock(side_effect=side_effect)
    elif return_value:
        v1.db.session.run = MagicMock(return_value=return_value)


class StepConnector:
    step = 1

    def mock(self, *args):
        print(args)
        if self.check:
            self.check(args)
        if self.step in self.step_mappings.keys():
            step_callable = self.step_mappings[self.step]
            self.step += 1
            return step_callable(args)
        else:
            raise NotImplementedError("No mapping found for step {}".format(self.step))

    def __init__(self, step_mappings, check=None):
        assert(type(step_mappings)==dict)
        self.step_mappings = step_mappings
        self.check = check


def standard_hooks_mock(user_auth=False, client_auth=None, client_user_auth=False, session_auth=None, session_command=None):
    """
    Mock out standard hooks for the scope of the test

    :param user_auth: A bool defining whether to automatically pass the user auth tests
    :param client_auth: A list of dictionaries. Each dictionary should contain the `official` and `origin` keys,
                        defining respectively whether the client should be denoted as official, and whether the client
                        is the origin of the request.
    :param session_auth: A bool defining whether to automatically pass the session based authentication tests
    :return (connector_instance, linked_auth):
            Connector instance is an instance of the StepConnector class defining the appropriate session mocks for the
            hooks. Linked auth is the authentication data that needs to be appended to the fake request
    """
    if client_auth:
        assert type(client_auth) == list
        for client_mock_data in client_auth:
            assert type(client_mock_data) == dict
            client_auth_keys = client_mock_data.keys()
            check_keys = {
                "official": bool,
                "origin": bool,
                "client_id": str
            }
            for k,v in check_keys.items():
                assert k in client_auth_keys
                assert type(client_mock_data[k]) == v
    else:
        client_auth = []
    # The mocking steps for the StepConnector instance
    hook_steps = {}
    linked_auth = {}
    new_key = lambda: max(hook_steps.keys())+1 if hook_steps else 1
    # Mock out hooks.user_auth
    if client_auth:
        for client in client_auth:
            if client["origin"]:
                client_id_field = "origin_client_id"
                client_secret_field = "origin_client_secret"
            else:
                client_id_field = "client_id"
                client_secret_field = "client_secret"
            client_secret = "client-secret".encode('utf-8')
            signed_client_secret = signer.sign(client_secret).decode('utf-8')
            # Generate a hash of the client secret
            client_secret_hash = bcrypt.hashpw(client_secret, bcrypt.gensalt()).decode('utf-8')
            linked_auth.update({
                client_id_field: client["client_id"],
                client_secret_field: signed_client_secret
            })
            raw_client_attrs = {
                "official": client["official"],
                "client_secret": client_secret_hash,
                "client_id": client["client_id"]
            }
            for k,v in client.items():
                if k not in raw_client_attrs.keys():
                    raw_client_attrs.update({k:v})
            def client_attrs(x): return [raw_client_attrs]
            # If the client is official, optionally add it twice, so the official hook will also pass
            hook_steps.update({new_key(): client_attrs})
            if client["official"]:
                if client["mock_official"]:
                    hook_steps.update({new_key(): client_attrs})
    if user_auth:
        # Password is hash of 'tachi'
        def user_exists(x): return [{"username": "holden",
                                "password": "$2b$12$ICD1Tzv2oFBWXLphBEhIO.PKm3VxxJxSPTCkMHMAQUPwei.IOMLJS"}]
        linked_auth.update({
            "username": "holden",
            "password": "tachi"
        })
        hook_steps.update({new_key(): user_exists})
    if client_user_auth:
        # Generate an access token
        # The encrypted value of token
        def access_token_exists(x):
            return [{"access_token": "$2b$12$g59RaPDZRoIMV/cpnaElOOqi37vPCeeyxe5GQX7gDpLPhRZZ3vsYG"}]
        signed_token = signer.sign("token".encode('utf-8'))
        linked_auth.update({"access_token": signed_token})
        hook_steps.update({new_key(): access_token_exists})

    if session_auth:
        # Generate a random session id for this mock, so I don't have to worry about removing mocks from
        # the sessions.sessions dict after the scope of the test is finished
        session_id = str(uuid.uuid4())
        # Sign the session id
        signed_session_id = signer.sign(session_id.encode('utf-8'))
        linked_auth.update({"session_id": signed_session_id})
        # Create a mock session instance that provides the same keys as it
        session_instance_mock = MagicMock()
        session_instance_mock.username = "holden"
        session_instance_mock.client = "rocinate"
        if not callable(session_command):
            s = session_command

            def session_command(x):
                return s
        session_instance_mock.command = MagicMock(side_effect=session_command)
        # Check whether the client and user also need to be explicitly mocked in the auth
        if not client_auth:
            linked_auth.update({"client_id": "rocinate"})
        if not user_auth:
            linked_auth.update({"username": "holden"})
        # Insert the session into the sessions.sessions dict
        sessions.sessions.update({session_id: session_instance_mock})
    connector_instance = StepConnector(hook_steps)
    return (connector_instance, linked_auth)




class Oauth2StepTests(unittest.TestCase):
    instance = v1.Oauth2Step()

    def setUp(self):
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
            # Mock a client_id and username
            hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                      client_auth=[
                                                                          {
                                                                              "client_id": "rocinate",
                                                                              "official": False,
                                                                              "origin": True
                                                                          },
                                                                          {
                                                                              "client_id": "official",
                                                                              "official": True,
                                                                              "origin": False,
                                                                              "mock_official": True
                                                                          }
                                                                      ])
            # Pretend that the user exists
            fake_request = mock_request(auth=hook_auth)
            # Mock a session to return that the relationship exists
            rel_mock = MagicMock()
            rel_mock.id = "1"

            def check_rel(_, r):
                correct_rel = self.instance._step_id
                if correct_rel == "user_token":
                    self.assertEqual(r["step_rel"], "AUTHORIZED")
                else:
                    self.assertEqual(r["step_rel"], "USES")
                return [rel_mock]
            # The session mock should assert that the correct step relationship was used
            mock_session(
                side_effect=check_rel,
                hook_side_effect=hook_controller_instance.mock)
            self.instance.on_delete(fake_request, MagicMock())
            # Check the result from the request object
            self.assertEqual(fake_request.context["result"]["data"]["type"], "success")
        # If no step id is found, assert that the step id is properly flagged as incorrect
        else:
            auth = {
                "client_id": "nauvoo",
                "username": "johnson",
                "password": "OPA4Lyfe"
            }
            hashed_correct_pw = bcrypt.hashpw(auth ["password"].encode('utf-8'), bcrypt.gensalt()).decode(
                'utf-8')
            # Pretend that the user exists
            mock_session(hook_return_value=[{"username": "holden", "password": hashed_correct_pw}])
            fake_request = mock_request(auth=auth)
            try:
                self.instance.on_delete(fake_request, MagicMock())
            except falcon.HTTPError as exception:
                self.assertEqual(exception.status, falcon.HTTP_NOT_FOUND)
                self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "STEP_ID_NOT_FOUND")

    def test_missing_rel_delete(self):
        """
        Test an otherwise correct delete request where the relationship between the user and client couldn't be
        found, and assert that the correct error is raised
        """
        if self.instance._step_id:
            # Mock the multi step hooks
            # Mock a client_id and username
            hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                      client_auth=[
                                                                          {
                                                                              "client_id": "rocinate",
                                                                              "official": False,
                                                                              "origin": True
                                                                          },
                                                                          {
                                                                              "client_id": "official",
                                                                              "official": True,
                                                                              "origin": False,
                                                                              "mock_official": True
                                                                          }
                                                                      ])
            def rel_not_exist(x): return []
            v1_steps = {
                1: rel_not_exist,
            }
            v1_controller = StepConnector(v1_steps)
            # Pretend that the user exists
            fake_request = mock_request(auth=hook_auth)
            # Mock a session to return that the relationship does not exist
            mock_session(side_effect=v1_controller.mock, hook_side_effect=hook_controller_instance.mock)
            fake_response = MagicMock()
            self.instance.on_delete(fake_request, fake_response)
            # Check the result from the request object
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
        mock_user_token = "aa5cacc7-9d91-471a-a5ac-aebc2c30a9d2"
        # Timestamp sign the user token_
        signed_mock_user_token = timestamp_signer.sign(mock_user_token).decode('utf-8')
        # Password is the hash of 'tachi'
        def rel_exists(x): return [{"user_token": mock_user_token, "scope": "command"}]
        def add_token(x): return []
        # Use the StepConnector class to assign the lambdas to the relevant mocking steps
        v1_steps = {
            1: rel_exists,
            2: add_token,
            3: add_token
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])
        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        # Mock authentication
        auth = {
            "user_token": signed_mock_user_token,
        }
        auth.update(hook_auth)
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_ACCESS_TOKEN")
        self.assert_("token" in fake_request.context["result"]["data"].keys())

    def test_post_mismatched_access_token(self):
        """
        Submit a request with an incorrect access token, and assert that the correct error is thrown
        :return:
        """
        mock_user_token = "aa5cacc7-9d91-471a-a5ac-aebc2c30a9d2"
        # Timestamp sign the user token_
        signed_mock_user_token = timestamp_signer.sign(mock_user_token).decode('utf-8')
        # Password is the hash of 'tachi'
        def rel_exists(x): return [{"user_token": "not-the-user-token", "scope": "command"}]
        def add_token(x): return []
        # Use the StepConrnector class to assign the lambdas to the relevant mocking steps
        v1_steps = {
            1: rel_exists,
            2: add_token,
            3: add_token
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])
        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        # Mock authentication
        auth = {
            "user_token": signed_mock_user_token,
        }
        auth.update(hook_auth)
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        fake_response = MagicMock()
        self.instance.on_post(fake_request, fake_response)
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "AUTH_TOKEN_MISMATCHED")
        self.assertEqual(fake_response.status, falcon.HTTP_FORBIDDEN)

    def test_bad_signature_token(self):
        """
        Submit a request with a token that's not signed and assert that the correct error is raised. The behavior
        should be identical for an expired token
        """
        mock_user_token = "aa5cacc7-9d91-471a-a5ac-aebc2c30a9d2"
        # Password is the hash of 'tachi'

        def rel_exists(x): return [{"user_token": "not-the-user-token", "scope": "command"}]

        def add_token(x): return []
        # Use the StepConnector class to assign the lambdas to the relevant mocking steps
        v1_steps = {
            1: rel_exists,
            2: add_token,
            3: add_token
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])
        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        # Mock authentication without signing the token
        auth = {
            "user_token": mock_user_token,
        }
        auth.update(hook_auth)
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        fake_response = MagicMock()
        self.instance.on_post(fake_request, fake_response)
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "AUTH_TOKEN_INVALID")
        self.assertEqual(fake_response.status, falcon.HTTP_FORBIDDEN)

    def test_no_rel_found(self):
        """
        Submit a seemingly valid request, but don't mock the db returning a valid relationship, and assert that
        the correct error ris raised.
        """
        mock_user_token = "aa5cacc7-9d91-471a-a5ac-aebc2c30a9d2"
        # No point signing the user token when the signature won't be tested in the scope of this request
        # Password is the hash of 'tachi'
        def user_exists(x): return [{"username": "holden",
                                "password": "$2b$12$ICD1Tzv2oFBWXLphBEhIO.PKm3VxxJxSPTCkMHMAQUPwei.IOMLJS"}]
        def rel_not_exists(x): return []
        def add_token(x): return []
        # Use the StepConnector class to assign the lambdas to the relevant mocking steps
        v1_steps = {
            1: rel_not_exists,
            2: add_token,
            3: add_token
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])
        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        # Mock authentication without signing the token
        auth = {
            "user_token": mock_user_token,
        }
        auth.update(hook_auth)
        fake_request = mock_request(auth=auth)
        # Submit a request to the instance, and assert that the correct data is returned
        fake_response = MagicMock()
        self.instance.on_post(fake_request, fake_response)
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USER_NOT_AUTHORIZED")
        self.assertEqual(fake_response.status, falcon.HTTP_UNAUTHORIZED)


class Oauth2UserTokenTests(Oauth2StepTests):
    instance = v1.UserToken()

    def test_post(self):
        def client_exists(x): return [{"client_id": "rocinate", "callback_url": "http://random_url"}]
        def token_data(x): return []
        v1_steps = {
            1: client_exists,
            2: token_data
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True,
                                                                          "callback_url": "http://random_url"
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])

        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc={"scope": "command"})
        # Submit a request to the instance, and assert that the correct data is returned
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "USER_AUTHORIZATION_TOKEN")
        self.assert_("token" in fake_request.context["result"]["data"].keys())

    def test_origin_client_not_found(self):
        """
        Submit a request where the method can't find the origin client in the database, and assert that the correct
        error is raised
        """
        def client_exists(x): return []
        def token_data(x): return []
        v1_steps = {
            1: client_exists,
            2: token_data
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True,
                                                                          "callback_url": "http://random_url"
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])

        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc={"scope": "command"})
        # Submit a request to the instance, and assert that the correct data is returned
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_ID_INVALID")

    def test_missing_scope(self):
        """
        Submit a request without a scope attached, and assert that the correct error is raised
        :return:
        """
        def client_exists(x): return [{"client_id": "rocinate", "callback_url": "http://random_url"}]
        def token_data(x): return []
        v1_steps = {
            1: client_exists,
            2: token_data
        }
        hook_controller_instance, hook_auth = standard_hooks_mock(user_auth=True,
                                                                  client_auth=[
                                                                      {
                                                                          "client_id": "rocinate",
                                                                          "official": False,
                                                                          "origin": True,
                                                                          "callback_url": "http://random_url"
                                                                      },
                                                                      {
                                                                          "client_id": "official",
                                                                          "official": True,
                                                                          "origin": False,
                                                                          "mock_official": True
                                                                      }
                                                                  ])

        v1_controller_instance = StepConnector(v1_steps)
        # Set a session mock, with the controller instances as the side effects
        mock_session(side_effect=v1_controller_instance.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth)
        # Submit a request to the instance, and assert that the correct data is returned
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_NOT_FOUND")


class UsersTests(unittest.TestCase):
    instance = v1.Users()

    def setUp(self):
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
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": False,
                "scope": "settings_change"
            }
        ], session_auth=True)
        mock_session(hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc={})
        fake_response = MagicMock()
        # Assert that the correct error is thrown for the doc not including a settings key
        self.instance.on_put(fake_request, fake_response)
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SETTINGS_KEY_NOT_FOUND")

    def test_on_put_success(self):
        """
        Submit a successful mocked request to change the settings, and assert that it passes
        """
        # Mock out session auth and and client that can change settings
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": False,
                "scope": "settings_change"
            }
        ], session_auth=True)
        def user_exists(x):return [{"username": "holden", "settings": {"thing1": "value1"}}]
        def settings_change_confirmation(x): return []
        # Mock that the user exists in a v1 session
        v1_steps = {
            1: user_exists,
            2: settings_change_confirmation
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc={"settings":
                                                             {"thing1": "newvalueforthing1",
                                                              "new_setting": "newsettinvalue"}})
        fake_response = MagicMock()
        self.instance.on_put(fake_request, fake_response)
        self.assert_(True)

    def test_on_get_success(self):
        """
        Test a successful request to read a users settings.
        Note: This method does not require any other tests, because all mitigating conditions and factors are removed
        by the hooks and middleware before it
        """
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": False,
                "scope": "settings_read"
            }
        ], session_auth=True)
        def user_exists(x): return [
            {
                "first_name": "james",
                "last_name": "holden",
                "email": "holden@rocinate.opa",
                "username": "holden",
                "settings": {"thing1": "value1"}}]
        def settings_change_confirmation(x): return []
        # Mock that the user exists in a v1 session
        v1_steps = {
            1: user_exists,
            2: settings_change_confirmation
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth)
        fake_response = MagicMock()
        self.instance.on_get(fake_request, fake_response)
        self.assert_(True)

    def test_on_delete_success(self):
        """
        Test a successful request to delete a user from the database.
        Note: This method does nto require any other tests, because all mitigating conditions and factors are removed
        by the hooks and middleware before it
        """
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": True,
                "origin": False,
                "scope": "official",
                "mock_official": True
            }
        ], session_auth=True)
        # Create a mock session with the username and assert that it's logout method is called
        session_instance_mock = MagicMock()
        session_instance_mock.username = "holden"
        session_instance_mock.logout = MagicMock()
        session_id = str(uuid.uuid4())
        sessions.sessions.update({session_id: session_instance_mock})
        # A blank array that will be returned when the user delete is called
        def user_delete_confirmation(x): return []
        v1_steps = {
            1: user_delete_confirmation
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth)
        # Call the method
        self.instance.on_delete(fake_request, MagicMock())
        # Assert that the logout() method was called of the fake session
        session_instance_mock.logout.assert_any_call()

    def test_on_post_success(self):
        """
        Test a successful request to create a user
        """
        # Mock an official client
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": True,
                "origin": False,
                "scope": "official",
                "mock_official": True
            }
        ])
        # The required information to create a user
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings":
                {
                    "location": "Minnesota, Earth",
                    "email": "holden@rocinate.opa"
                }
        }
        # Mock no users with that username already found

        def no_users_found(x): return []

        def validate_user_info(a):
            """
            Validate the received data about the user

            :param a: The arguments, in an arr
            :return []: A blank array indicating that the request was processed
            """
            q, u = a
            # Go through all the values in doc and make sure they're the same
            for k,v in doc.items():
                # The password will be hashed. Everything else should be validated
                if k != "password":
                    print("Validating {}".format(k))
                    self.assertEqual(v, u[k])
            self.assertEqual(u["client_id"], "rocinate")
            return []

        v1_steps = {
            1: no_users_found,
            2: validate_user_info
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc=doc)
        # Call the method
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "USER_CREATED")

    def test_on_post_required_setting_not_found(self):
        """
        Submit an otherwise correct request to create a new user that does not include one of the required settings
        defined in the method (e.g. location or email). Assert that the proper error is part of the field errors
        raised
        """
        # Mock an official client
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": True,
                "origin": False,
                "scope": "official",
                "mock_official": True
            }
        ])
        # The required information to create a user, minus the "email" key in settings
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings":
                {
                    "location": "Minnesota, Earth"
                }
        }

        mock_session(hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc=doc)
        # Call the method
        self.instance.on_post(fake_request, MagicMock())
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
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": True,
                "origin": False,
                "scope": "official",
                "mock_official": True
            }
        ])
        # The required information to create a user, but with an invalid settings key
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings": "settings_str"
        }

        mock_session(hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc=doc)
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
        # Mock an official client
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": True,
                "origin": False,
                "scope": "official",
                "mock_official": True
            }
        ])
        # The required information to create a user, minus the settings key
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden"
        }

        mock_session(hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc=doc)
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
        """
                Test a successful request to create a user
                """
        # Mock an official client
        hook_controller_instance, hook_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": True,
                "origin": False,
                "scope": "official",
                "mock_official": True
            }
        ])
        # The required information to create a user
        doc = {
            "username": "holden",
            "password": "nagata",
            "first_name": "James",
            "last_name": "holden",
            "settings":
                {
                    "location": "Minnesota, Earth",
                    "email": "holden@rocinate.opa"
                }
        }

        # Mock no users with that username already found

        def user_found(x):
            return [{
                "username": "holden",
                "first_name": "Clarissa",
                "last_name": "Mao"
            }]


        v1_steps = {
            1: user_found
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hook_controller_instance.mock)
        fake_request = mock_request(auth=hook_auth, doc=doc)
        # Call the method
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USERNAME_ALREADY_EXISTS")


class SessionTests(unittest.TestCase):
    """
    Tests for the v1/sessions method
    """
    instance = v1.Sessions()
    _session_instance_copy = None


    # Mock out the session class for the course of this
    def setUp(self):
        self._session_instance_copy = sessions.Session

    def tearDown(self):
        sessions.Session = self._session_instance_copy

    def test_on_post_success(self):
        """
        Test a successful request to create a session, and assert that it passes
        """
        hooks_controller_instance, hook_auth = standard_hooks_mock(user_auth=True, client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": False
            }
        ], client_user_auth=True)
        # Mock sessions.Session

        def session_test(username, client_id):
            # Check the username and client_id and create a MagicMock
            self.assertEqual(username, "holden")
            self.assertEqual(client_id, "rocinate")
            session_instance = MagicMock()
            session_instance.username = username
            session_instance.client_id = client_id
            session_instance.session_id = "my-session-id"
            return session_instance
        sessions.Session = MagicMock(side_effect=session_test)
        fake_request = mock_request(auth=hook_auth)
        mock_session(hook_side_effect=hooks_controller_instance.mock)
        # Send the request
        self.instance.on_post(fake_request, MagicMock(), null_session_id=None)
        self.assertIn("my-session-id", fake_request.context["result"]["data"]["session_id"])

    def test_session_id_on_post(self):
        """
        Test a post request that incorrectly submitted a session id, and assert that the correct erro is raised
        """
        hooks_controller_instance, hook_auth = standard_hooks_mock(user_auth=True, client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": False
            }
        ], client_user_auth=True)

        # Mock sessions.Session

        def session_test(username, client_id):
            # Check the username and client_id and create a MagicMock
            self.assertEqual(username, "holden")
            self.assertEqual(client_id, "rocinate")
            session_instance = MagicMock()
            session_instance.username = username
            session_instance.client_id = client_id
            session_instance.session_id = "my-session-id"
            return session_instance

        sessions.Session = MagicMock(side_effect=session_test)
        fake_request = mock_request(auth=hook_auth)
        mock_session(hook_side_effect=hooks_controller_instance.mock)
        # Send the request, incorrectly including a sesion id
        self.instance.on_post(fake_request, MagicMock(), null_session_id="my-session-id")
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "NO_SESSION_ID_ON_CREATE")

    def test_session_id_on_delete(self):
        """
        Test the basic session delete method
        """
        hooks_controller_instance, hook_auth = standard_hooks_mock(session_auth=True)
        fake_request = mock_request(auth=hook_auth)
        mock_session(hook_side_effect=hooks_controller_instance.mock)
        self.instance.on_delete(fake_request, MagicMock(), session_id=hook_auth["session_id"])
        self.assertEqual(fake_request.context["result"]["data"]["id"], "SESSION_LOGGED_OUT")


class CommandTests(unittest.TestCase):
    """
    Test the /v1/commands methods
    """
    instance = v1.Commands()

    def setUp(self):
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
        hooks_controller_instance, hook_auth = standard_hooks_mock(session_auth=True, session_command={
            "data":
                {
                    "type":  "success",
                    "id": "GENERIC_COMMAND_SUCCESSFUL",
                    "text": "command result!"
                }
        })
        doc = {
            "command": "my_command"
        }
        fake_request = mock_request(auth=hook_auth, doc=doc)
        mock_session(hook_side_effect=hooks_controller_instance.mock)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "GENERIC_COMMAND_SUCCESSFUL")

    def test_post_no_command(self):
        """
        Submit a request without a command in the doc, and assert that the correct error is raised
        """
        hooks_controller_instance, hook_auth = standard_hooks_mock(session_auth=True, session_command={
            "data":
                {
                    "type": "success",
                    "id": "GENERIC_COMMAND_SUCCESSFUL",
                    "text": "command result!"
                }
        })
        fake_request = mock_request(auth=hook_auth)
        mock_session(hook_side_effect=hooks_controller_instance.mock)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "COMMAND_NOT_FOUND")


class ClientTests(unittest.TestCase):
    """
    Tests for /v1/clients
    """
    instance = v1.Clients()

    def setUp(self):
        global signer
        global timestamp_signer
        if not signer:
            signer = Signer("super-secret")
            hooks.signer = signer
        if not timestamp_signer:
            timestamp_signer = TimestampSigner("super-secret")
            v1.timestampsigner = timestamp_signer

    def test_on_get_success(self):
        """
        Test a successful request to the on_get method
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": True
            },
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])

        def client_data(x):
            return [{"client_id": "rocinate", "callback_url": "http://random_url"}]

        def client_users(x):
            return [{"username": "user1"}, {"username": "user2"}]

        v1_steps = {
            1: client_data,
            2: client_users
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth)
        self.instance.on_get(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["user_num"], 2)
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_DATA_FETCHED")

    def test_on_delete_success(self):
        """
        Test a successful request t the on_delete method
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "rocinate",
                "official": False,
                "origin": True
            },
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])

        def delete_client_confirmation(x):
            return []
        v1_steps = {
            1: delete_client_confirmation
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth)
        self.instance.on_delete(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_DELETED")

    def test_on_post_success(self):
        """
        Test the successful creation of a client
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "command"
            }
        }
        def client_not_already_exists(x):
            return []
        def client_creation_confirmation(x):
            _, query_data = x
            # Validate the query data
            self.assertEqual(query_data["client_id"], "rocinate")
            self.assertEqual(query_data["scope"], "command")
            return []
        v1_steps = {
            1: client_not_already_exists,
            2: client_creation_confirmation
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["data"]["id"], "CLIENT_CREATED")

    def test_post_unauthorized_scope(self):
        """
        Test an otherwise successful post request that tries to use a scope that it's not authorized too, and assert
        that the correct error is raised
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "admin"
            }
        }

        def client_not_already_exists(x):
            return []

        v1_steps = {
            1: client_not_already_exists
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_NOT_AUTHORIZED")

    def test_post_client_already_exists(self):
        """
        Test an otherwise correct request to the on_post method, but mock that a client with that id already exists
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "command"
            }
        }

        def client_not_already_exists(x):
            return [{"client_id": "rocinate"}]

        v1_steps = {
            1: client_not_already_exists
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_ID_ALREADY_EXISTS")

    def test_post_invalid_data_type(self):
        """
        Submit a post request with an incorrect data type for one of the required keys, and assert that the correct
        error is raised
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])
        doc = {
            "new_client": {
                "id": 1,
                "scope": "command"
            }
        }

        def client_not_already_exists(x):
            return []

        v1_steps = {
            1: client_not_already_exists
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "ID_INVALID")

    def test_post_no_client_information(self):
        """
        Test a request with no client information and assert that the correct error is raised
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])
        mock_session(hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "NEW_CLIENT_NOT_FOUND")

    def test_post_invalid_scope(self):
        """
        Test a request with an invalid scope and assert that the correct error is raised
        """
        hooks_controller_instance, hooks_auth = standard_hooks_mock(client_auth=[
            {
                "client_id": "web-official",
                "official": True,
                "mock_official": True,
                "origin": False
            }
        ])
        doc = {
            "new_client": {
                "id": "rocinate",
                "scope": "definitely_not_vaild"
            }
        }

        def client_not_already_exists(x):
            return []

        v1_steps = {
            1: client_not_already_exists
        }
        v1_step_connector = StepConnector(v1_steps)
        mock_session(side_effect=v1_step_connector.mock, hook_side_effect=hooks_controller_instance.mock)
        fake_request = mock_request(auth=hooks_auth, doc=doc)
        self.instance.on_post(fake_request, MagicMock())
        self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_INVALID")