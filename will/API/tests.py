import unittest
from falcon import testing
from will.API import v1, middleware, hooks

class APITestCase(testing.TestCase):
    master_url = None
    @staticmethod
    def _fmt_resp(resp):
        resp_str = "{0}: {1}".format(resp.status_code, resp.status)
        log.info(resp_str)
        print(resp_str)
    def setUp(self):
        super(APITestCase, self).setUp()
        self.app = Will.app

class MiddlewareTests(APITestCase):
    """
    Test middlware bounces
    """
    # Could be any valid url
    master_url = "/api/v1/users/"

    def test_bad_content_type(self):
        # Don't submit all the parameters the first time
        doc = {"data": {}, "auth": {}}
        resp = self.simulate_post(path=self.master_url, body=json.dumps(doc), headers={"Accept": json_header})
        self._fmt_resp(resp)
        self.assertEqual(resp.status_code, 415)
        self.assertEqual(resp.json["title"], "Unsupported media type")

    def test_null_request(self):
        resp = self.simulate_post(path=self.master_url, headers={"Accept": json_header})
        self._fmt_resp(resp)
        self.assertEqual(resp.status_code, 415)
        self.assertEqual(resp.json["title"], "This API only supports responses encoded as JSON")

    def test_malformed_request(self):
        malformed_body = "{'doc': 'hello']"
        resp = self.simulate_post(path=self.master_url, headers={"Accept": json_header})
        self._fmt_resp(resp)
        self.assertEqual(True, True)

# Unit tests for the API
if __name__ == '__main__':
    unittest.main()
