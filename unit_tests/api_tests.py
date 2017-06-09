# Internal imports
from will import API
from will import exceptions

# Builtin imports
import unittest
from unittest.mock import *


class InstanceTest(unittest.TestCase):
    def test_load(self):
        """
        Test load an instance of the API, asserting that the App class instantiates the middleware and calls the 
        app_callable parameter with it
        """
        configuration_data = {
            "debug": True,
            "banned-ips": [],
            "secret-key": "so-secret"
        }
        # Mock the API object instead of creating a real one because a real one creates a blocking thread
        API_mock = MagicMock()
        API_instance = API.App(configuration_data, MagicMock(), MagicMock(), app_callable=API_mock)
        self.assertTrue(API_mock.called)
        API_mock.assert_called_with(middleware=API_instance.middleware)
        API_instance.kill()

    def test_malformed_conf(self):
        """
        Pass the API a malformed configuration object and assert that it raises an instance of 
        `exceptions.ConfigurationError`
        """
        malformed_conf_data = {
            "nope": 1.23
        }
        with self.assertRaises(exceptions.ConfigurationError):
            API.App(malformed_conf_data, MagicMock(), MagicMock())


class RoutingTest(unittest.TestCase):
    def test_routing(self):
        app = Mock()
        app.add_route = MagicMock()
        API.router.process_routes(app)
        self.assertTrue(app.add_route.called)

if __name__ == '__main__':
    unittest.main()
