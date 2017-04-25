import logging
import unittest
import will
import json
import requests

logging.basicConfig(filename="unittests.log", level=logging.DEBUG)

log = logging.getLogger()

json_header = "application/vnd.api+json"
api_path = "http://127.0.0.1:5000/api/v{version_num}/{api_route}"
api_version = "1"

def api_request(route, request_data, header=json_header, encode_json=True):
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
    def testStatusCheck(self):
        response = api_request("status_check",  {}, json_header)
        log.info(response)
if __name__ == '__main__':
    unittest.main()
