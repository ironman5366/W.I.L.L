#Builtin imports
import logging, sys, inspect

log = logging.getLogger()

argument_list = []

class Argument:

    def _build(self):
        """
        Use the class data to determine what the best source of data is, and define a callable object to fetch
        the data from
         
        """
        pass

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
        self._build()

# TODO: passive method of argument error

class ResponseFunction(Argument):
    def value(self, command_obj):
        """
        Expose the pointer to the set_response function
        
        :return self._session.set_response: The pointer 
        """
        return self._session.set_response

class APIKey(Argument):
    """
    Base class that represents an API key argument
    
    """

    key_name = None

    @property
    def _key(self):
        session = self._graph.session()

        valid_keys = session.run("MATCH (a:APIKey {name: {name}) WHERE a.usages < a.max_usages or a.max_usages is null",
                                 {"name": self.key_name})

        if valid_keys:
            session.close()
            key = valid_keys[0]
            # Increment the key usage
            key_value = key["value"]
            session.run("MATCH (a:APIKey {value: {value}}) SET a.usages = a.usages+1",
                        {"value": key_value})
            session.close()
            return key_value
        else:
            session.close()
            # TODO: implement passive argument error
            raise NotImplementedError("Passive argument errors not yet implemented")

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

    def _build(self):
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

# Build a list of argument classes in the file
# Iterate through the classes
for c in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    # Check that the parent is the Argument class
    if inspect.getmro(c)[1] == Argument:
        argument_list.append(c)
log.debug("Loaded {0} classes: {1}".format(len(argument_list), argument_list))