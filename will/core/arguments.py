# Builtin imports
import logging
import sys
import inspect
import time
import queue
import datetime

# Internal imports
from will import tools

# External imports
import falcon
import newspaper
from pytz import timezone
from geopy import Nominatim, exc

geocoder = Nominatim()

log = logging.getLogger()

argument_list = []


class Argument:

    _build_status = "successful"
    errors = []

    def build(self):
        """
        Use the class data to determine what the best source of data is, and cache the relevant data when
        possible
         
        """
        return True

    def value(self, command_obj):
        """
        Return the value of the argument
        
        :param command_obj: An instantiated command class
       
        """
        raise NotImplementedError("Argument parent class must not be called directly")

    def __init__(self, user_data, client, session, graph):
        """
        Instantiate an argument and start a build
        
        :param user_data: The users database entry
        :param client: The client that started the session
        :param session: The instantiated session object that the commiserate commands will run through
        """
        self.errors = []
        self._graph = graph
        self._user_data = user_data
        self._client = client
        self._session = session
        self.name = type(self).__name__
        # If _build returns false, there's an error, and the user should be notified
        try:
            build_valid = self.build()
        except Exception as e:
            log.error("Argument {0} raised an unhandled error with args {1}!".format(self, e.args))
            build_valid = False
        if not build_valid:
            # Raise an argument error
            # Inject the error into the session
            self.errors.append(
                {
                    "type": "error",
                    "id": "ARGUMENT_BUILD_FAILED",
                    "text": "The build for argument {0} failed, and the user must address the issue. The build "
                    "provided the following information about the failure: {1}".format(
                        self.name, self._build_status
                    ),
                    "status": falcon.HTTP_CONFLICT
                }
            )


class SessionData(Argument):
    def value(self, command_obj):
        return self._session


class APIKey(Argument):
    """
    Base class that represents an API key argument
    
    """

    key_name = None
    _loaded_keys = queue.Queue(maxsize=1)
    load_url = False
    _url = None

    @property
    def _key(self):
        if self._loaded_keys.empty():
            if not self.build():
                log.error("{0} key fetch failing".format(self.key_name))
                self.errors.append(
                    {
                        "type": "error",
                        "text": "{0} key not available".format(self.key_name),
                        "id": "KEY_NOT_AVAILABLE",
                        "status": falcon.HTTP_INTERNAL_SERVER_ERROR
                    }
                )
                return False
        key = self._loaded_keys.get()
        self.build()
        return key

    def build(self):
        if self._loaded_keys.empty():
            key, url = tools.load_key(self.key_name, self._graph, load_url=self.load_url)
            if key:
                if self.load_url:
                    self._url = url
                self._loaded_keys.put(key)
                return True
            else:
                self._build_status = "No valid API keys found of type {}".format(self.key_name)
                return False
        else:
            return True

    def value(self, command_obj):
        """
        Increment the usage of the api key in the database and return it to the plugin

        :param command_obj:
        :return api_key: The api key 
        """
        if self.load_url:
            return self._key, self._url
        else:
            return self._key


class WeatherAPI(APIKey):
    key_name = "weather"


class WolframAPI(APIKey):
    key_name = "wolfram"

class CommandObject(Argument):
    """
    The command object
    
    """
    def value(self, command_obj):
        return command_obj


class CommandText(Argument):
    """
    The plain text of the command, what the user submitted
    
    """
    def value(self, command_obj):
        return command_obj.text


class CommandParsed(Argument):
    """
    The spacy parsed version of the command
    
    """
    def value(self, command_obj):
        return command_obj.parsed


class CommandCreated(Argument):
    """
    The datetime object representing when the command class was instantiated
    
    """
    def value(self, command_obj):
        return command_obj.created


class CommandUID(Argument):
    """
    The unique identifier of the command
    
    """
    def value(self, command_obj):
        return command_obj.uid


class UserData(Argument):
    """
    The users node in the database
    
    """
    def value(self, command_obj):
        return self._user_data


class ClientID(Argument):
    """
    The id of the client the user submitted the command from
    """
    def value(self, command_obj):
        return self._client


class Setting(Argument):
    """
    A base class that pulls a setting defined by self.setting_name from the user
    """
    setting_name = None
    _setting_raw_value = None
    _setting_value = None

    def setting_modifier(self):
        self._setting_value = self._setting_raw_value
        return True

    def build(self):
        # Load the setting from the database
        user_data = self._user_data
        user_settings = user_data["settings"]
        if self.setting_name in user_settings.keys():
            self._setting_raw_value = user_settings[self.setting_name]
            setting_passed = self.setting_modifier()
            return setting_passed
        else:
            error_string = "Couldn't find setting {} for user".format(self.setting_name)
            self._build_status = error_string
            self.errors.append({
                "type": "error",
                "text": error_string,
                "id": "SETTING_ARGUMENT_INVALID"
            })
            return False

    def value(self, command_obj):
        return self._setting_value


class Location(Setting):
    setting_name = "location"

    def setting_modifier(self):
        """
        Try to build a geopy object out of the setting
        """
        # Check if location is provided by the dynamic data submitted to settings
        if "location" in self._session.dynamic.keys():
            location = self._session.dynamic["location"]
        else:
            location = self._setting_raw_value
        try:
            # Reverse the coordinates
            time_started = time.time()
            loc_object = geocoder.reverse((location["latitude"], location["longitude"]))
            time_finished = time.time()
            time_delta = round(time_finished-time_started, 2)
            log.debug("Built location object in {} seconds".format(time_delta))
            self._setting_value = loc_object
            return True
        except exc.GeopyError as loc_exception:
            log.info("Geopy exception {0} with location {1}".format(loc_exception.args, location))
            error_string = "Failed to build a location from coordinates {}".format(location)
            self._build_status = error_string
            self.errors.append({
                "type": "error",
                "text": error_string,
                "id": "LOCATION_BUILD_FAILED"
            })
            return False


class TempUnit(Setting):
    setting_name = "temp_unit"


class TimeZone(Setting):
    setting_name = "timezone"

    def setting_modifier(self):
        self._setting_value = timezone(self._setting_raw_value)
        return True

    def value(self, command_obj):
        return datetime.datetime.now(self._setting_value)

# Build a list of argument classes in the file
# Iterate through the classes
for c in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    # Check that the parent is the Argument class
    if inspect.getmro(c[1]) == Argument:
        argument_list.append(c)
log.debug("Loaded {0} classes: {1}".format(len(argument_list), argument_list))