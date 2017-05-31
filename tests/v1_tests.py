# Builtin imports
from unittest.mock import *
import unittest

# External imports
import falcon
import bcrypt
from itsdangerous import TimestampSigner, Signer

# Internal imports
from will.API import v1, hooks

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
        print (args)
        if self.check:
            self.check(args)
        if self.step in self.step_mappings.keys():
            step_callable = self.step_mappings[self.step]
            self.step += 1
            return step_callable()
        else:
            raise NotImplementedError("No mapping found for step {}".format(self.step))

    def __init__(self, step_mappings, check=None):
        assert(type(step_mappings)==dict)
        self.step_mappings = step_mappings
        self.check = check


def standard_hooks_mock(user_auth=False, client_auth=None):
    """
    Mock out standard hooks for the scope of the test

    :param user_auth: A bool defining whether to automatically pass the user auth tests
    :param client_auth: A list of dictionaries. Each dictionary should contain the `official` and `origin` keys,
                        defining respectively whether the client should be denoted as official, and whether the client
                        is the origin of the request.
    :return (connector_instance, linked_auth):
            Connector instance is an instance of the StepConnector class defining the appropriate session mocks for the
            hooks. Linked auth is the authentication data that nees to be appended to the fake request
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
            client_attrs = lambda: [raw_client_attrs]
            # If the client is official, optionally add it twice, so the official hook will also pass
            hook_steps.update({new_key(): client_attrs})
            if client["official"]:
                if client["mock_official"]:
                    hook_steps.update({new_key(): client_attrs})
    if user_auth:
        # Password is hash of 'tachi'
        user_exists = lambda: [{"username": "holden",
                                "password": "$2b$12$ICD1Tzv2oFBWXLphBEhIO.PKm3VxxJxSPTCkMHMAQUPwei.IOMLJS"}]
        linked_auth.update({
            "username": "holden",
            "password": "tachi"
        })
        hook_steps.update({new_key(): user_exists})
    print ("Creating step connector with hook steps {}".format(hook_steps))
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
        Test a sucessful delete call to remove authentication between a user and client
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
        user_exists = lambda: [{"username": "holden",
                                "password": "$2b$12$ICD1Tzv2oFBWXLphBEhIO.PKm3VxxJxSPTCkMHMAQUPwei.IOMLJS"}]
        rel_exists = lambda: [{"user_token": mock_user_token, "scope": "command"}]
        add_token = lambda: []
        # Use the StepConnector class to assign the lambdas to the relevant mocking steps
        v1_steps = {
            1: user_exists,
            2: rel_exists,
            3: add_token,
            4: add_token
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



class Oauth2UserTokenTests(Oauth2StepTests):
    instance = v1.UserToken()

    def test_post(self):
        client_exists = lambda: [{"client_id": "rocinate", "callback_url": "http://random_url"}]
        token_data = lambda: []
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
        print (fake_request.context["result"])
        self.assertEqual(fake_request.context["result"]["data"]["id"], "USER_AUTHORIZATION_TOKEN")
        self.assert_("token" in fake_request.context["result"]["data"].keys())
