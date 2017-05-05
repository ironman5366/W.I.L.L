# Internal imports
from will.API import hooks
from will.userspace import sessions

# Builtin imports
import unittest
from unittest.mock import *

# External imports
import falcon
import bcrypt
import itsdangerous


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


def mock_session(return_value=None):
    """
    Reach into the hooks file and change it's `graph.session` class to a mock method that returns what the tests
    need it to return
    :param return_value: 
    
    """
    hooks.graph = MagicMock()
    hooks.graph.session = MagicMock
    hooks.graph.session.run = MagicMock(return_value=return_value)


class UserAuthTests(unittest.TestCase):

    def test_successful_login(self):
        """
        Mock the authentication and test a successful authentication flow
        
        """
        correct_auth = {
            "username": "holden",
            "password": "rocinate"
        }
        # Create an encrypted hash of the password to put in the mock database
        hashed_correct_pw = bcrypt.hashpw(correct_auth["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Pretend that the user exists
        mock_session([{"username": "holden", "password":  hashed_correct_pw}])
        fake_request = mock_request(correct_auth)
        # If the hook fails it'll throw a falcon error
        hooks.user_auth(fake_request, MagicMock(), None, None)
        self.assert_(True)

    def test_invalid_password(self):
        """
        Don't submit a password and assert that it raises the correct http error
        """
        incorrect_auth = {
            "username": "holden",
            "password": "tycho"
        }
        fake_request = mock_request(incorrect_auth)
        hashed_correct_pw = bcrypt.hashpw("rocinate".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Pretend that the user exists
        mock_session([{"username": "holden", "password": hashed_correct_pw}])
        with self.assertRaises(falcon.HTTPError) as exception:
            hooks.user_auth(fake_request, MagicMock(), None, None)

    def test_invalid_user(self):
        """
        Submit a username that the mocked database won't find, and assert that it raises the correct http error
        """
        incorrect_auth = {
            "username": "lionelpolanski",
            "password": "OPA4Lyfe"
        }
        fake_request = mock_request(incorrect_auth)
        mock_session([])
        with self.assertRaises(falcon.HTTPError) as exception:
            hooks.user_auth(fake_request, MagicMock(), None, None)

    def test_malformed_auth(self):
        """
        Don't submit username or password in the authentication and assert that it raises the correct http error
        """
        fake_request = mock_request()
        with self.assertRaises(falcon.HTTPError) as exception:
            hooks.user_auth(fake_request, MagicMock(), None, None)
            # Check that the correct status code was submitted
            self.assertEqual(exception.status, falcon.HTTP_BAD_REQUEST)


class AssertParamTests(unittest.TestCase):
    """
    Test hooks.assert_param, the hook that asserts that a request to a deep url (ex: /users/{username}) includes the
    correct parameter and isn't just top level (ex: /users)
    """
    def test_successful_params(self):
        """
        Submit parameters and make sure that the method works as intended
        """
        correct_params = {
            "transponder": "rocinate"
        }
        hooks.assert_param(mock_request(),MagicMock(), None, correct_params)
        self.assert_(True)

    def test_missing_params(self):
        """
        Don't send any params and assert that it throws the right kind of error 
        """
        with self.assertRaises(falcon.HTTPError):
            hooks.assert_param(mock_request(), MagicMock(), None, {})


class SessionAuthTest(unittest.TestCase):
    """
    Check session id based authentication 
    """

    def test_missing_session_id(self):
        """
        Don't submit a session id, and assert that it throws an http error
        """
        with self.assertRaises(falcon.HTTPError):
            hooks.session_auth(mock_request(), MagicMock(), None, None)

    def test_unsigned_session_id(self):
        """
        Submit an unsigned session id, and assert that it throws an http error
        """
        my_session_id = "ubiquitous"
        session_auth = {
            "session_id": my_session_id
        }
        fake_request = mock_request(auth=session_auth)
        # Mock the signer and have it return BadSignature
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(side_effect=itsdangerous.BadSignature("Invalid transponder"))
        resp_mock = MagicMock()
        try:
            hooks.session_auth(fake_request, resp_mock, None, None)
            self.fail("HTTP Error wasn't raised")
        except falcon.HTTPError as exception:
            self.assert_(hooks.signer.unsign.called)
            self.assertEqual(exception.status, falcon.HTTP_BAD_REQUEST)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SESSION_ID_BAD_SIGNATURE")

    def test_invalid_session(self):
        """
        Submit a session id that has a valid signature but doesn't correspond to an existing session
        """
        session_auth = {
            "session_id": "ubiquitous.signature"
        }
        fake_request = mock_request(auth=session_auth)
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value="ubiquitous")
        try:
            hooks.session_auth(fake_request, MagicMock(), None, None)
            self.fail("HTTP Error wasn't raised")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SESSION_ID_INVALID")

    def test_no_client_session(self):
        """
        Submit a request with a signed session id but without a client in the auth dict
        """
        session_auth = {
            "session_id": "ubiquitous.signature",
            "client_id": "rocinate"
        }
        fake_request = mock_request(auth=session_auth)
        # Remove the fake signature
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value="ubiquitous")
        # Mock the important aspects of a session object
        session_mock = MagicMock()
        session_mock.session_id = "ubiquitous"
        session_mock.client = "donnager"
        sessions.sessions.update({session_mock.session_id: session_mock})
        try:
            hooks.session_auth(fake_request, MagicMock(), None, None)
            self.fail("HTTP Error wasn't raised")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SESSION_ID_CLIENT_MISMATCHED")
        # Remove the mock session
        finally:
            del sessions.sessions[session_mock.session_id]

    def test_valid_session(self):
        """
        Submit a valid signed session id, the correct client id, and correctly mock the session object
        """
        session_auth = {
            "session_id": "ubiquitous.signature",
            "client_id": "donnager"
        }
        fake_request = mock_request(auth=session_auth)
        # Remove the fake signature
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value="ubiquitous")
        # Mock the important aspects of a session object
        session_mock = MagicMock()
        session_mock.session_id = "ubiquitous"
        session_mock.client = "donnager"
        sessions.sessions.update({
            session_mock.session_id: session_mock
        })
        try:
            hooks.session_auth(fake_request, MagicMock(), None, None)
            self.assert_(True)
        # Regardless, delete the fake session from sessions
        finally:
            del sessions.sessions[session_mock.session_id]