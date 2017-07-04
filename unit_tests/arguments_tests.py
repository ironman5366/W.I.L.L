# Builtin imports
from unittest.mock import *
import unittest
import datetime

# External imports
from sqlalchemy.orm import sessionmaker

# Internal imports
from will.core import arguments
from will.schema import *
import create_db

timestamp_signer = None
signer = None
s_key = create_db.db_init(None, None, None, None, "super-secret", "web-official", debug=True)
engine = create_db.engine
db = sessionmaker(bind=engine)

# TODO: make this less of a dumpster fire

class BaseArgumentTests(unittest.TestCase):
    """
    Test the base argument class, and also provide a parent method for other argument tests to inherit from
    """
    base_class = arguments.Argument
    _instance = None
    _session = None
    _user_data = None
    _client = None
    _check_no_errors = True
    _desired_build_status = "successful"

    def load_user_data(self):
        return {"username": "holden", "settings":
                {
                    "location":
                        {
                            "latitude": 44.970468,
                            "longitude": -93.262148
                        },
                    "email": "holden@rocinate.opa",
                    "temp_unit": "C",
                    "timezone": "US/Eastern"
                }}

    def load_graph(self):
        return db

    def load_session(self):
        return MagicMock()

    def load_client(self):
        return "rocinate"

    def setUp(self):
        """
        Build the argument with mocked values
        """
        self.session = db()
        api_keys = self.session.query(APIKey).all()
        print("Found {0} APIKeys".format(len(api_keys)))
        self.session.begin_nested()
        self._session = self.load_session()
        self._user_data = self.load_user_data()
        self._graph = self.load_graph()
        self._client = self.load_client()
        print("Building with desired build status {}".format(self._desired_build_status))
        self._instance = self.base_class(
            self._user_data, self._client, self._session, self._graph)
        # If the class being tested is a parent class, it may not be necessary to have a build pass
        self.assertEqual(self._instance._build_status, self._desired_build_status)
        if self._check_no_errors:
            self.assertEqual(self._instance.errors, [])

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_re_build(self):
        self._instance.build()
        self.assertEqual(self._instance._build_status, self._desired_build_status)
        if self._check_no_errors:
            self.assertEqual(self._instance.errors, [])

    def test_value(self):
        with self.assertRaises(NotImplementedError):
            self._instance.value(MagicMock())


class SessionArgumentTests(BaseArgumentTests):
    base_class = arguments.SessionData

    def test_value(self):
        data = self._instance.value(MagicMock())
        self.assertEqual(data, self._session)


class APIKeyArgumentTests(BaseArgumentTests):
    base_class = arguments.APIKey
    _check_no_errors = False
    key_found = False
    _key_value = "my-key"
    _desired_build_status = None
    key_name = None
    _mocked_keys = ["wolfram", "weather"]

    @classmethod
    def setUpClass(cls):
        print("Setting up class")
        session = db()
        for key_type in cls._mocked_keys:
            key_class = APIKey(key_type=key_type, value="my-key", usages=0, max_usages=9000, refresh=9000,
                               timestamp=datetime.datetime.now())
            session.add(key_class)
        session.commit()

    @classmethod
    def tearDownClass(cls):
        print("Tearing down class")
        session = db()
        api_keys = session.query(APIKey).all()
        [session.delete(a) for a in api_keys]
        session.commit()

    def setUp(self):
        """
        Build the argument with mocked values
        """
        if self.key_found:
            self._key_found = True
            self._desired_build_status = "successful"
            self._check_no_errors = True
        else:
            self._desired_build_status = "No valid API keys found of type {}".format(self.key_name)
            self._key_found = False
            self._check_no_errors = False
        super().setUp()
        print("Building, desired build status is {}".format(self._desired_build_status))
        # If the class being tested is a parent class, it may not be necessary to have a build pass
        self.assertEqual(self._instance._build_status, self._desired_build_status)
        if self._check_no_errors:
            print("Checking that no errors occured")
            self.assertEqual(self._instance.errors, [])

    def load_session(self):
        session_instance = MagicMock
        if self.key_found:
            session_instance.run = MagicMock(return_value=[{"value": self._key_value}])
        else:
            session_instance.run = MagicMock(return_value=[])
        return session_instance

    def test_value(self):
        # Assert that no API key is found for the empty key
        key = self._instance.value(MagicMock())
        if self._key_found:
            self.assertEqual(key, self._key_value)
        else:
            self.assertFalse(key)


class WeatherAPIKeyTest(APIKeyArgumentTests):
    base_class = arguments.WeatherAPI
    key_found = True
    key_name = "weather"


class WolframAPIKeyTest(APIKeyArgumentTests):
    base_class = arguments.WolframAPI
    key_found = True
    key_name = "wolfram"


class CommandObjectTests(BaseArgumentTests):
    base_class = arguments.CommandObject

    def test_value(self):
        command_mock = MagicMock()
        obj = self._instance.value(command_mock)
        self.assertEqual(obj, command_mock)


class CommandTextTests(BaseArgumentTests):
    base_class = arguments.CommandText

    def test_value(self):
        command_mock = MagicMock()
        command_mock.text = "hello"
        obj = self._instance.value(command_mock)
        self.assertEqual(obj, "hello")


class CommandParsedTests(BaseArgumentTests):
    base_class = arguments.CommandParsed

    def test_value(self):
        command_mock = MagicMock()
        parsed_mock = MagicMock()
        command_mock.parsed = parsed_mock
        obj = self._instance.value(command_mock)
        self.assertEqual(obj, parsed_mock)


class CommandCreatedTests(BaseArgumentTests):
    base_class = arguments.CommandCreated

    def test_value(self):
        command_mock = MagicMock()
        command_mock.created = datetime.datetime.now()
        obj = self._instance.value(command_mock)
        self.assertEqual(obj, command_mock.created)


class CommandUIDTests(BaseArgumentTests):
    base_class = arguments.CommandUID

    def test_value(self):
        command_mock = MagicMock()
        command_mock.uid = "command-uid"
        obj = self._instance.value(command_mock)
        self.assertEqual(obj, "command-uid")


class UserDataTests(BaseArgumentTests):
    base_class = arguments.UserData

    def test_value(self):
        user_data = self.load_user_data()
        u = self._instance.value(MagicMock())
        self.assertEqual(user_data, u)


class ClientIdTests(BaseArgumentTests):
    base_class = arguments.ClientID

    def test_value(self):
        client_id = self.load_client()
        c = self._instance.value(MagicMock())
        self.assertEqual(client_id, c)


class SettingTests(BaseArgumentTests):
    _check_no_errors = False
    base_class = arguments.Setting
    _desired_build_status = "Couldn't find setting None for user"

    def test_value(self):
        v = self._instance.value(MagicMock())
        self.assertIsNone(v)


class TempUnitTests(SettingTests):
    base_class = arguments.TempUnit
    _check_no_errors = True
    _desired_build_status = "successful"

    def test_value(self):
        v = self._instance.value(MagicMock())
        self.assertEqual(v, "C")


class LocationTests(SettingTests):
    base_class = arguments.Location
    _desired_build_status = "successful"
    _check_no_errors = True

    def test_value(self):
        v = self._instance.value(MagicMock())
        print(v)
        # Check the latitude and longitude of the returned geopy object
        user_data = self.load_user_data()
        latitude = user_data["settings"]["location"]["latitude"]
        longitude = user_data["settings"]["location"]["longitude"]
        self.assertEqual(round(v.latitude, 2), round(latitude, 2))
        self.assertEqual(round(v.longitude, 2), round(longitude, 2))


class TimeZoneTests(SettingTests):
    base_class = arguments.TimeZone
    _desired_build_status = "successful"
    _check_no_errors = True

    def test_value(self):
        v = self._instance.value(MagicMock())
        self.assertEqual(v.tzinfo._tzname, "EDT")
