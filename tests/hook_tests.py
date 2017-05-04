# Internal imports
from will.API import hooks

# Builtin imports
import unittest
from unittest.mock import *

# External imports
import falcon
import bcrypt


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


class UserAuth(unittest.TestCase):

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
        mock_session([{"username": "johnson", "password": hashed_correct_pw}])
        with self.assertRaises(falcon.HTTPError) as exception:
            hooks.user_auth(fake_request, MagicMock(), None, None)
            # Check that the correct status code was submitted
            self.assertEquals(exception.status, falcon.HTTP_UNAUTHORIZED)

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
            # Check that the correct status code was submitted
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)

    def test_malformed_auth(self):
        """
        Don't submit username or password in the authentication and assert that it raises the correct http error
        """
        fake_request = mock_request()
        with self.assertRaises(falcon.HTTPError) as exception:
            hooks.user_auth(fake_request, MagicMock(), None, None)
            # Check that the correct status code was submitted
            self.assertequal(exception.status, falcon.HTTP_BAD_REQUEST)