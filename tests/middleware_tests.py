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
    base_class = MagicMock()
    base_class.context = {}
    base_class.headers = headers
    base_class.method = method
    base_class.body = body
    if body:
        base_class.content_length = len(body)
    else:
        base_class.content_length = 0
    base_class.stream.read = lambda: body
    base_class.client_accepts_json = True
    if json_decode:
        base_class.body = json.dumps(base_class.body)
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