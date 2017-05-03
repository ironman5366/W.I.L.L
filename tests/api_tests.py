from will import API
import unittest
import falcon
from unittest.mock import *
import sys


class InstanceTests(unittest.TestCase):
    def test_load(self):
        API.configuration_data = {
            "debug": True,
            "banned-ips": [],
            "secret-key": "so-secret"
        }
        app_instance = API.start(MagicMock())
        self.assertIsInstance(app_instance, falcon.API)


class RouterTest(unittest.TestCase):
    def test_routing(self):
        app = Mock()
        app.add_route = MagicMock()
        API.router.process_routes(app)
        self.assertTrue(app.add_route.called)

if __name__ == '__main__':
    unittest.main(exit=True)
