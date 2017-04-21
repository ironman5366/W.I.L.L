#Builtin imports
import logging, sys, inspect, queue

# External imports
import falcon

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
        
        :param user_data: 
        :param client: 
        :param session: 
        """
        self._graph = graph
        self._user_data = user_data
        self._client = client
        self._session = session
        self.name = type(self).__name__
        # If _build returns false, there's an error, and the user should be notified
        build_valid = self.build()
        if not build_valid:
            # Raise an argument error
            # Inject the error into the session
            self.errors = [
                {
                    "type": "error",
                    "id": "ARGUMENT_BUILD_FAILED",
                    "text": "The build for argument {0} failed, and the user must address the issue. The build "
                    "provided the following information about the failure: {1}".format(
                        self.name, self._build_status
                    ),
                    "status": falcon.HTTP_CONFLICT
                }
            ]

# TODO: passive method of argument error

class APIKey(Argument):
    """
    Base class that represents an API key argument
    
    """

    key_name = None
    _loaded_keys = queue.Queue(maxsize=1)

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
            session = self._graph.session()
            valid_keys = session.run("MATCH (a:APIKey {name: {name}) WHERE a.usages < a.max_usages or a.max_usages is "
                                     "null",
                                     {"name": self.key_name})
            if valid_keys:
                session.close()
                key = valid_keys[0]
                # Increment the key usage
                key_value = key["value"]
                session.run("MATCH (a:APIKey {value: {value}}) SET a.usages = a.usages+1",
                            {"value": key_value})
                session.close()
                self._loaded_keys.put(key_value)
            else:
                session.close()
                self._build_status = "No valid API keys found of type {0}".format(self.key_name)
                return False

    def value(self, command_obj):
        """
        Increment the usage of the api key in the database and return it to the plugin
        
        :param command_obj: 
        :return api_key: The api key 
        """
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


class Location(Argument):

    def build(self):
        """
        Determine the users best method of getting the location, and add to the cache queue
        
        
        """
        # Check if the client provides a location
        # TODO: standardized location form
        # TODO: a recaching queue for currently online clients
        client_id = self._client
        session = self._graph.session()
        client_node = session.run("MATCH (c:Client {client_id: {client_id}}) return (c)",
                                  {"client_id": client_id})
        # The client the user is currently using provides a location, and that should be used
        if client_node and "location" in client_node.keys():
            location = client_node["location"]
            self._location = location
            return True
        # The client doesn't provide a location, check for other clients and run accuracy calculations
        else:
            pass
        # Regardless, close the session
        session.close()
    def value(self, command_obj):
        """
        Return the built location
        
        :return self._location: 
        """
        return self._location

class Setting(Argument):
    setting_name = None
    def build(self):
        # Load the setting from the database
        user_data = self._user_data
        user_settings = user_data["settings"]
class News(Argument):
    def build(self):
        user_data = self._user_data
        user_news_site = user_data["settings"]["news_site"]

# Build a list of argument classes in the file
# Iterate through the classes
for c in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    # Check that the parent is the Argument class
    if inspect.getmro(c)[1] == Argument:
        argument_list.append(c)
log.debug("Loaded {0} classes: {1}".format(len(argument_list), argument_list))