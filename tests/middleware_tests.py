# Internal imports
from will.API import middleware
from will.userspace import sessions

# Builtin imports
import unittest
from unittest.mock import *
import json

# External imports
import falcon


def mock_request(method="POST", body=None, headers={}, json_decode=False, content_type="application/json"):
    """
    Create a mock request object with an appropriate request context

    :param method: The method of the request
    :param body: The body of the request.
    :param headers: A dict of headers to insert inside the request
    :param json_decode: A bool defining whether to translate the body to json
    :return base_class: The final request object
    """
    if "Content-Type" not in headers:
        headers.update({"Content-Type": content_type})
    base_class = MagicMock()
    base_class.context = {}
    base_class.headers = headers
    base_class.method = method
    if body:
        base_class.content_length = len(body)
    else:
        base_class.content_length = 0

    base_class.client_accepts_json = True
    if json_decode:
        base_class.body = json.dumps(body)
    else:
        base_class.body = body
    base_class.stream.read = lambda: base_class.body
    return base_class


class RequireJSONTests(unittest.TestCase):
    """
    Tests for the method that requires incoming requests that aren't GET to have valid JSON in the body
    """
    instance = middleware.RequireJSON()

    def test_not_accepts_json(self):
        """
        Test that a request that doesn't accept JSON will be rejected
        """
        fake_request = mock_request()
        fake_request.client_accepts_json = False
        try:
            self.instance.process_request(fake_request, MagicMock())
            # Fail if an HttpNotAcceptable error isn't raised
            self.fail("Require JSON middleware failed to raise http not acceptable when the client indicated it "
                      "did not accept JSON responses.")
        except falcon.HTTPNotAcceptable:
            self.assert_(True)

    def test_bad_content_type(self):
        """
        Test a Content-Type other than application/json is submitted in the request it fails with unsupported media
        """
        fake_request = mock_request(content_type="whoops")
        try:
            self.instance.process_request(fake_request, MagicMock())
            # Fail if an HTTPError isn't raised with a status of unsupported media type
            self.fail("Require JSON middleware failed to raise an exception with a status of unsupported media type "
                      "when a request with a content type other than application/json was submitted.")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_UNSUPPORTED_MEDIA_TYPE)


class JSONTranslatorTests(unittest.TestCase):
    instance = middleware.JSONTranslator()

    def test_empty_body(self):
        """
        Test that a request with an empty body raises the correct type of error
        """
        fake_request = mock_request()
        try:
            self.instance.process_request(fake_request, MagicMock())
            # Fail if an HTTPError isn't raised with a status of bad request
            self.fail("JSON translator middleware failed to raise an exception with a status of bad request when "
                      "a request with an empty body was submitted")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_BAD_REQUEST)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "REQUEST_EMPTY")

    def test_malformed_json(self):
        """
        Submit malformed json in the request body and assert that the correct type of HttpError is raised
        """
        invalid_json = "[mal'formed}"
        fake_request = mock_request(body=invalid_json)
        try:
            self.instance.process_request(fake_request, MagicMock())
            # Fail if an HTTPError isn't raised with a status of 500
            self.fail("JSON translator middleware failed to raise a 500 exception when malformed JSON data was "
                      "submitted in the body of a request")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_500)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "JSON_MALFORMED")

    def test_incorrect_json(self):
        """
        Submit json that doesn't include auth or data keys and assert that the correct type of http error is raised
        """
        incorrect_json = {"irrelevant_data": "answer"}
        fake_request = mock_request(body=incorrect_json, json_decode=True)
        try:
            self.instance.process_request(fake_request, MagicMock())
            # Fail if an HTTP_BAD_REQUEST error isn't raised
            self.fail("JSON translator middleware failed to raise an HTTP_BAD_REQUEST exception when JSON was "
                      "submitted that didn't meet the API spec in the body of the request.")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_BAD_REQUEST)
            self.assertEqual(fake_request.context["result"]["errors"][0]["id"], "JSON_INCORRECT")

    def test_empty_response(self):
        """
        Check that a request with no body doesn't fail
        """
        fake_request = MagicMock()
        fake_request.context = {}
        self.instance.process_response(fake_request, MagicMock(), MagicMock())
        self.assert_(True)

    def test_missing_response_data(self):
        """
        Submit a request with an invalid result context, and asset that the correct 
        """
        fake_request = mock_request()
        fake_request.context.update({
            "result": {"irrelevant_data": "irrelevant_key"}
        })
        try:
            self.instance.process_response(fake_request, MagicMock(), MagicMock())
            # The test should fail if a 500 error isn't thrown
            self.fail("JSON translator middleware failed to raise an internal server error when the request context "
                      "did not include the necessary keys")
        except falcon.HTTPError as exception:
            self.assertEqual(exception.status, falcon.HTTP_INTERNAL_SERVER_ERROR)

    def test_proper_response(self):
        """
        Submit a proper response to the middleware and assert that it passes
        """
        fake_request = mock_request()
        fake_response = MagicMock()
        fake_request.context["result"] = {
            "data": {
                "id":
                    "whatever",
                "type": "success",
                "text": "hello"
            }
        }
        self.instance.process_response(fake_request, fake_response, MagicMock())
        fake_request.context["result"] = {
            "errors": [{
                "id":
                    "whatever",
                "type": "error",
                "text": "hello"
            }]
        }
        self.instance.process_response(fake_request, fake_response, MagicMock())
        self.assert_(True)


class AuthTranslatorTests(unittest.TestCase):
    instance = middleware.AuthTranslator()

    def test_invalid_b64_client(self):
        """
        Test an invalid b64 client header
        :return: 
        """
        pass

    def test_invalid_b64_auth(self):
        """
        Test invalid b64 authentication
        :return: 
        """
        pass

    def test_incomplete_auth(self):
        """
        Test an incomplete authentication header
        :return: 
        """
        pass

    def test_missing_client_id(self):
        """
        Test a missing client id
        :return: 
        """

    def test_successful_auth(self):
        """
        Check a request with a successful authentication
        :return: 
        """