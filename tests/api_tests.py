from will import API
import unittest
import falcon
from unittest.mock import *


class InstanceTest(unittest.TestCase):
    def test_load(self):
        print("Testing API load")
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
class RoutingTest(unittest.TestCase):
    def test_routing(self):
        app = Mock()
        app.add_route = MagicMock()
        API.router.process_routes(app)
        self.assertTrue(app.add_route.called)

if __name__ == '__main__':
    unittest.main(exit=True)
