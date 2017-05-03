from will import API
import unittest
import falcon
from unittest.mock import *
from will.exceptions import ConfigurationError


class RouterTests(unittest.TestCase):

    def test_routes(self):
        app = Mock()
        app.add_route = MagicMock()
        API.router.process_routes(app)
        self.assertTrue(app.add_route.called)


class InstanceTests(unittest.TestCase):
    def test_load(self):
        API.configuration_data = {
            "debug": True,
            "banned-ips": [],
            "secret-key": "so-secret"
        }
        app_instance = API.start(MagicMock())
        print("Got mock instance from API")
        self.assertIsInstance(app_instance, falcon.API)

if __name__ == '__main__':
    unittest.main()
