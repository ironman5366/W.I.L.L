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


def mock_session(return_value=None, side_effect=None):
    """
    Reach into the hooks file and change it's `graph.session` class to a mock method that returns what the tests
    need it to return
    :param return_value: 
    
    """
    hooks.graph = MagicMock()
    hooks.graph.session = MagicMock
    if side_effect:
        # Give an option to return it with a side ffect instead of a return value
        assert not return_value
        hooks.graph.session.run = MagicMock(side_effect=side_effect)
    else:
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


class CalculateScopeTests(unittest.TestCase):
    """
    Basic tests for the utility method that checks submitted and required scopes based on hooks.scopes
    """

    def test_invalid_scope(self):
        """
        Submit a scope that's under the level of the required scope, and assert that the returned value is False
        """
        required_scope = "admin"
        submitted_scope = "command"
        scope_resp = hooks.calculate_scope(submitted_scope, required_scope)
        self.assertFalse(scope_resp)

    def test_wrong_submitted_scope(self):
        """
        Submit a submitted scope that doesn't exist
        """
        required_scope = "admin"
        submitted_scope = "nope"
        scope_resp = hooks.calculate_scope(submitted_scope, required_scope)
        self.assertFalse(scope_resp)

    def test_wrong_required_scope(self):
        """
        Submit a required scope that doesn't exist
        """
        required_scope = "nope"
        submitted_scope = "command"
        scope_resp = hooks.calculate_scope(submitted_scope, required_scope)
        self.assertFalse(scope_resp)

    def test_correct_scope(self):
        """
        Submit a correct required and submitted scope, with the submitted scope within the correct range
        """
        required_scope = "command"
        submitted_scope = "settings_change"
        scope_resp = hooks.calculate_scope(submitted_scope, required_scope)
        self.assertTrue(scope_resp)


class CheckScopeTests(unittest.TestCase):
    """
    Tests for the internal method hooks._scope_check that determines whether scope data submitted in a valid 
    authenticated requests matches the corresponding scope permissions in the database
    """
    session_auth_copy = None

    def setUp(self):
        """
        Mock out hooks.session_auth so that it doesn't interfere with the testing
        """
        self.session_auth_copy = hooks.session_auth
        hooks.session_auth = MagicMock()

    def tearDown(self):
        """
        Restore hooks.session_auth
        """
        hooks.session_auth = self.session_auth_copy

    def test_valid_scope(self):
        """
        Mock a request that has a valid scope for the request it's accessing
        """
        method_required_scope = "command"
        # Mock the database query to return the scope we want it to
        mock_session([{"scope": "command"}])
        hooks._scope_check(
            mock_request(auth={"username": "holden", "client_id": "rocinate"}),
            MagicMock(),
            None,
            None,
            method_required_scope)
        self.assert_(True)

    def test_invalid_scope(self):
        """
        Mock a request that doesn't have a sufficient scope for the request it's trying to access
        """
        method_required_scope = "settings_change"
        # Mock the database query to return a lower scope
        mock_session([{"scope": "settings_read"}])
        fake_request = mock_request(auth={"username": "holden", "client_id": "rocinate"})
        try:
            hooks._scope_check(fake_request, MagicMock(), None, None, method_required_scope)
            # If it doesn't throw the required error, the test should fail
            self.fail("The scope check method didn't reject an invalid scope")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_INSUFFICIENT")

    def test_bad_database_scope(self):
        """
        Test the function behavior when the database returns an invalid scope 
        """
        method_required_scope = "settings_change"
        # Mock the database query to return a scope that doens't exist
        mock_session([{"scope": "nonexistent_scope"}])
        fake_request = mock_request(auth={"username": "holden", "client_id": "rocinate"})
        try:
            hooks._scope_check(fake_request, MagicMock(), None, None, method_required_scope)
            # If it doesn't throw the required error, the test should fail
            self.fail("The scope check method didn't raise an error when the database returned a bad scope")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_INTERNAL_SERVER_ERROR)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "SCOPE_INTERNAL_ERROR")

    def test_no_username_submitted(self):
        """
        Mock a request to the method that doesn't include a username and assert that it throws the correct type of error
        """
        # Submit a valid scope, although it doesn't matter, since the method will check for the username before it
        # checks the scope
        method_required_scope = "settings_change"
        # Don't include anything in the auth section of the request
        invalid_request = mock_request()
        try:
            hooks._scope_check(invalid_request, MagicMock(), None, None, method_required_scope)
            # If it doesn't throw the required error, the test should fail
            self.fail("The scope check method didn't raise an error when no username was submitted" )
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(invalid_request.context["result"]["errors"][0]["id"], "USERNAME_NOT_FOUND")


class ClientIsOfficialTests(unittest.TestCase):

    """
    Test that the hook which checks whether the client is noted as official works properly
    """
    client_auth_copy = None

    def setUp(self):
        """
        Mock out hooks.client_auth while this test is running
        """
        self.client_auth_copy = hooks.client_auth
        hooks.client_auth = MagicMock()

    def tearDown(self):
        """
        Restore hooks.client_auth from the copy
        """
        hooks.client_auth = self.client_auth_copy

    def test_official_client(self):
        """
        Test a valid official client
        """
        # Mock the session so that it will return that the client is official
        mock_session([{"official": True}])
        correct_client_id = "rocinate"
        fake_request = mock_request(auth={"client_id": correct_client_id})
        hooks.client_is_official(fake_request, MagicMock(), None, None)
        self.assert_(True)

    def test_unofficial_client(self):
        """
        Test a client that's not noted as official, and assert that it throws the correct error
        """
        bad_client_id = "anubis"
        fake_request = mock_request(auth={"client_id": bad_client_id})
        mock_session([{"official": False}])
        try:
            hooks.client_is_official(fake_request, MagicMock(), None, None)
            # The test should fail if the required error isn't thrown
            self.fail("Client is official tests didn't raise an error when an unofficial client was submitted")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_UNOFFICIAL")


class UserIsAdminTests(unittest.TestCase):
    _scope_check_copy = None

    def setUp(self):
        """
        Mock hooks._scope_check for just this function
        """
        self._scope_check_copy = hooks._scope_check
        hooks._scope_check = MagicMock()

    def tearDown(self):
        """
        Restore hooks._scope_check from the copy
        """
        hooks._scope_check = self._scope_check_copy

    def test_valid_user(self):
        """
        Mock a request where the user is an administrator
        """
        admin_user = {"username": "holden"}
        fake_request = mock_request(auth=admin_user)
        # Mock the database query to say that the user is an admin
        mock_session([{"admin": True}])
        hooks.user_is_admin(fake_request, MagicMock(), None, None)
        self.assert_(True)

    def test_invalid_user(self):
        """
        Mock a request where the user is not an administrator, and assert that it throws the correct http error
        """
        invalid_user = {"username": "amos"}
        fake_request = mock_request(auth=invalid_user)
        # Mock the database sssion to say that the user isn't dn admin
        mock_session([{"admin": False}])
        try:
            hooks.user_is_admin(fake_request, MagicMock(), None, None)
            self.fail("User is admin hook did not reject a non administrator user")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USER_NOT_ADMIN")


class ScopeHookTests(unittest.TestCase):
    """
    Test all of the basic scope hooks within one method
    """
    _scope_check_copy = None
    _scope_check_mock = MagicMock()

    def setUp(self):
        """
        Mock hooks._scope_check for just this function
        """
        self._scope_check_copy = hooks._scope_check
        hooks._scope_check = self._scope_check_mock

    def tearDown(self):
        """
        Restore hooks._scope_check from the copy
        """
        hooks._scope_check = self._scope_check_copy

    def test_client_read_settings(self):
        hooks.client_can_read_settings(None, None, None, None)
        self._scope_check_mock.assert_called_with(None,  None, None, None, "settings_read")

    def test_client_can_change_settings(self):
        hooks.client_can_change_settings(None, None, None, None)
        self._scope_check_mock.assert_called_with(None, None, None, None, "settings_change")

    def test_client_can_make_commands(self):
        hooks.client_can_make_commands(None, None, None, None)
        self._scope_check_mock.assert_called_with(None, None, None, None, "command")


class ClientUserAuthTests(unittest.TestCase):
    """
    Tests for the method hooks.client_user_auth that authenticates both the client and the user
    """
    client_auth_copy = None

    def setUp(self):
        """
        Mock hooks.client_auth for the scope of the method
        """
        self.client_auth_copy = hooks.client_auth
        hooks.client_auth = MagicMock()

    def tearDown(self):
        hooks.client_auth = self.client_auth_copy

    def test_access_token_missing(self):
        """
        Submit a request that doesn't include an access token in the auth section of the request and assert that the
        correct http error is raised
        """
        fake_request = mock_request()
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an HTTPError isn't thrown
            self.fail("The client user auth method failed to raise an error when it was called without an access token")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "ACCESS_TOKEN_NOT_FOUND")

    def test_username_missing(self):
        """
        Submit a request that includes an access token but not a username and assert that the correct http error
        is raised
        """
        fake_request = mock_request(auth={"access_token": "token"})
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an HTTPError isn't thrown
            self.fail("The client user auth method failed to raise an error when it was called without a username")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USERNAME_NOT_FOUND")

    def test_invalid_username(self):
        """
        Submit a request that includes an invalid username
        """
        fake_request = mock_request(auth={"access_token": "token", "username": "lionelpolanski"})
        # Mock the session to return no users
        mock_session([])
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            # If an HTTPError isn't raised the test should fail
            self.fail("The client user auth method failed to raise an error when it was called with a nonexistent "
                      "username")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USERNAME_INVALID")

    def test_bad_signature_access_token(self):
        """
        Submit a request that includes a valid username, but an access token with a bad signature. Assert that the 
        method raises the correct http error
        """
        fake_request = mock_request(auth={"access_token": "token", "username": "holden"})
        # Mock the session to return the user
        mock_session([{"username": "holden"}])
        # Mock itsdangerous to raise a bad signature error
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(side_effect=itsdangerous.BadSignature("Oops"))
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an HTTPError isn't raised
            self.fail("The client user auth method failed to raise an error when an access token with a bad signature"
                      "was submitted")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "ACCESS_TOKEN_INVALID")
        # Unmock itdangerous
        finally:
            hooks.signer = itsdangerous_signer_copy

    def test_no_rel_found(self):
        """
        Assert that the method throws the correct error when it receives a request from a user that's not properly
        linked with the client
        """
        # A hacky way to have different values for different mocked db queries inside the method
        def session_side_effect(param, _):
            # If it's the first one, return that the user exists
            if param.endswith("return (u)"):
                return ([{"username": "holden"}])
            # If it's the other query, return that there's no rel
            else:
                return ([])
        mock_session(side_effect=session_side_effect)
        fake_request = mock_request(auth={"access_token": "token", "username": "holden", "client_id": "rocinate"})
        # Mock itsdangerous to return what we want it do
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value=True)
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an HTTPError isn't raised
            self.fail("The client user auth method failed to raise an error when the client and user were not "
                      "authenticated together.")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "USER_NOT_AUTHENTICATED")
        # Unmock itsdangerous
        finally:
            hooks.signer = itsdangerous_signer_copy

    def test_invalid_access_token(self):
        """
        Test an invalid access token
        """

        # A hacky way to have different values for different mocked db queries inside the method
        def session_side_effect(param, _):
            # If it's the first one, return that the user exists
            if param.endswith("return (u)"):
                return ([{"username": "holden"}])
            # If it's the other query, return that there's no rel
            else:
                # The hashed value of "not_token"
                return ([{"access_token": "$2b$12$oFr1SU2H5PKM7Der91GnAOVX4zxv6bDokeLF7zUFhHPJoScXi11la"}])
        mock_session(side_effect=session_side_effect)
        fake_request = mock_request(auth={"access_token": "token", "username": "holden", "client_id": "rocinate"})
        # Mock itsdangerous to return what we want it do
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value="token")
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an HTTPError isn't raised
            self.fail("The client user auth method failed to raise an error when the client and user were not "
                      "authenticated together.")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "ACCESS_TOKEN_INVALID")
        # Unmock itsdangerous
        finally:
            hooks.signer = itsdangerous_signer_copy

    def test_valid_auth(self):
        """
        Submit a valid username, and a valid rel
        """

        # A hacky way to have different values for different mocked db queries inside the method
        def session_side_effect(param, _):
            # If it's the first one, return that the user exists
            if param.endswith("return (u)"):
                return ([{"username": "holden"}])
            # If it's the other query, return that there's no rel
            else:
                # The encyrpted value of "token"
                return ([{"access_token": "$2b$12$g59RaPDZRoIMV/cpnaElOOqi37vPCeeyxe5GQX7gDpLPhRZZ3vsYG"}])

        mock_session(side_effect=session_side_effect)
        fake_request = mock_request(auth={"access_token": "token", "username": "holden",  "client_id": "rocinate"})
        # Mock itsdangerous to return what we want it do
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value="token")
        try:
            hooks.client_user_auth(fake_request, MagicMock(), None, None)
            self.assert_(True)
        # Unmock itsdangerous regardless of if the test fails
        finally:
            hooks.signer = itsdangerous_signer_copy


class ClientAuthTests(unittest.TestCase):
    """
    Tests for the method hooks.client_auth, which authenticates just a client
    """

    def test_client_id_missing(self):
        """
        Mock a request with the client_id parameter missing. Note: this will be the same as if client_auth is missing
        """
        fake_request = mock_request()
        try:
            hooks.client_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an HTTPError isn't raised
            self.fail("The client auth hook failed to raise an error when a request was submitted without the client "
                      "id parameter")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_ID_NOT_FOUND")

    def test_client_not_exist(self):
        """
        Submit a client id that the mocked database won't find
        """
        fake_request = mock_request(auth={"client_id": "anubis", "client_secret": "super-secret"})
        # Mock the session to not find the client
        mock_session([])
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value=True)
        try:
            hooks.client_auth(fake_request, MagicMock(), None, None)
            # The test should fail if it an HTTPError isn't raised
            self.fail("The client auth hook failed to raise an error when a nonexistent client id was submitted")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_ID_INVALID")
        # Unmock itsdangerous regardless of if the test fails
        finally:
            hooks.signer = itsdangerous_signer_copy

    def test_client_secret_bad_signature(self):
        """
        Submit a client_secret parameter that's unsigned, an assert that it raises the correct http error
        """
        fake_request = mock_request(auth={"client_id": "anubis", "client_secret": "super-secret"})
        # Mock the database to find the client
        mock_session([{"client_id": "anubis"}])
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(side_effect=itsdangerous.BadSignature("oops"))
        try:
            hooks.client_auth(fake_request, MagicMock(), None, None)
            # The test should fail if an http error isn't raised
            self.fail("The client auth method failed to raise an error when a client secret without a signature was "
                      "submitted")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_SECRET_BAD_SIGNATURE")
        # Unmock itsdangerous regardless of if the test fails
        finally:
            hooks.signer = itsdangerous_signer_copy

    def test_client_secret_invalid(self):
        """
        Submit a client secret key that has a valid signature, but is invalid
        """
        fake_request = mock_request(auth={"client_"
                                          "id": "anubis", "client_secret": "super-secret"})
        # Mock the session to not find the client
        # The hash of "secret"
        mock_session([{
            "client_secret": "$2b$12$WNFp8f2wqiCEZ/x8SKUGp.H4cOq09OAk.kZh7kxaywN65wpgruxiC"
        }])
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value="super-secret")
        try:
            hooks.client_auth(fake_request, MagicMock(), None, None)
            # The test should fail if it an HTTPError isn't raised
            self.fail("The client auth hook failed to raise an invalid client secret was submitted")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNAUTHORIZED)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "CLIENT_SECRET_INVALID")
        # Unmock itsdangerous regardless of if the test fails
        finally:
            hooks.signer = itsdangerous_signer_copy

    def test_valid_client_auth(self):
        """
        Submit valid mocked credentials, and assert that no errors are raised
        """
        fake_request = mock_request(auth={"client_"
                                          "id": "anubis", "client_secret": "secret"})
        # Mock the session to not find the client
        # The hash of "secret"
        mock_session([{
            "client_secret": "$2b$12$WNFp8f2wqiCEZ/x8SKUGp.H4cOq09OAk.kZh7kxaywN65wpgruxiC"
        }])
        itsdangerous_signer_copy = hooks.signer
        hooks.signer = MagicMock()
        hooks.signer.unsign = MagicMock(return_value='secret')
        try:
            hooks.client_auth(fake_request, MagicMock(), None, None)
            # The test should fail if it an HTTPError isn't raised
            self.assert_(True)
        # Unmock itsdangerous regardless of if the test fails
        finally:
            hooks.signer = itsdangerous_signer_copy