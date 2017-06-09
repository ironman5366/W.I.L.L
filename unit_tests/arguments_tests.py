# Builtin imports
from unittest.mock import *
import unittest

# Internal imports
from will.core import arguments


class BaseArgumentTests(unittest.TestCase):
    """
    Test the base argument class, and also provide a parent method for other argument tests to inherit from
    """
    base_class = arguments.Argument
    _instance = None
    _session = None
    _user_data = None
    _client = None

    def load_user_data(self):
        return {"username": "holden"}

    def load_graph(self):
        return MagicMock()

    def load_session(self):
        return MagicMock()

    def load_client(self):
        return "rocinate"

    def setUp(self):
        """
        Build the argument with mocked values
        """
        self._session = self.load_session()
        self._user_data = self.load_user_data()
        self._graph = self.load_graph()
        self._client = self.load_client()
        self._instance = self.base_class(
            self._user_data, self._client, self._session, self._graph)
        # Assert that the graph built without errors
        self.assertEqual(self._instance._build_status, "successful")
        self.assertEqual(self._instance.errors, [])

    def test_re_build(self):
        self._instance.build()
        self.assertEqual(self._instance._build_status, "successful")
        self.assertEqual(self._instance.errors, [])

    def test_value(self):
        with self.assertRaises(NotImplementedError):
            self._instance.value(MagicMock())


class SessionArgumentTests(BaseArgumentTests):
    base_class = arguments.SessionData

    def test_value(self):
        data = self._instance.value(MagicMock())
        self.assertEqual(data, self._session)
