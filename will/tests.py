import logging
import unittest
import will
import json
import requests

logging.basicConfig(filename="unittests.log", level=logging.DEBUG)

log = logging.getLogger()

json_header = "application/vnd.api+json"

def api_request(method, request_data, header, encode_json=True):
    if encode_json:
        request_data = json.dumps(request_data)
    log.info("{0} -> {1} ({2})".format(method, request_data, header))
    response = requests.post("http://localhost/api/v1/{}".format(method), data=request_data, header=header)
    log.debug(response.text)
    return response.text

class APITests(unittest.TestCase):
    def setUp(self):
        self.will = will.will()
    def tearDown(self):
        self.will.kill()
    def testRunning(self):
        assert self.will.running
if __name__ == '__main__':
    unittest.main()
