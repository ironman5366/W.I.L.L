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


class SessionData(Argument):
    def value(self, command_obj):
        return self._session


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
    """
    A base class that pulls a setting defined by self.setting_name from the user
    """
    setting_name = None
    _setting_value = None

    def build(self):
        # Load the setting from the database
        user_data = self._user_data
        user_settings = user_data["settings"]
        if self.setting_name in user_settings.keys():
            self._setting_value = user_settings[self.setting_name]
        else:
            error_string = "Couldn't find setting {} for user".format(self.setting_name)
            self._build_status = error_string
            self.errors.append({
                "type": "error",
                "text": error_string,
                "id": "SETTING_ARGUMENT_INVALID"
            })

    def value(self, command_obj):
        return self._setting_value


class TempUnit(Setting):
    setting_name = "temp_unit"


class TimeZone(Setting):
    setting_name = "timezone"

    # Use most of the build code from the Settings parent, but also build a timezone object
    def build(self):
        # Load the setting from the database
        user_data = self._user_data
        user_settings = user_data["settings"]
        if self.setting_name in user_settings.keys():
            self._setting_value = user_settings[self.setting_name]
            self._timezone_obj = timezone(self._setting_value)
        else:
            error_string = "Couldn't find setting {} for user".format(self.setting_name)
            self._build_status = error_string
            self.errors.append({
                "type": "error",
                "text": error_string,
                "id": "SETTING_ARGUMENT_INVALID"
            })

    def value(self, command_obj):
        return datetime.datetime.now(self._timezone_obj)


class Site(Argument):
    """
    A standardized site caching argument for a site that releases articles
    """

    site_type = None
    _site_url = None
    _site_cache = None
    # The time in seconds before a site needs to be recached
    cache_time = 43200
    num_articles = 5

    def _compile_site(self):
        session = self._graph.session()
        log.debug("Compiling site {0}".format(self._site_url))
        try:
            site_object = newspaper.build(self._site_url, memoize_articles=False)
            articles_index = self.num_articles-1
            top_articles = site_object.articles[0:articles_index]
            output_strs = []
            for article in top_articles:
                article_url = article.url
                log.debug("Building article object")
                article_object = newspaper.Article(article_url)
                log.debug("Downloading the article")
                article_object.download()
                log.debug("Parsing the article")
                article.parse()
                article.nlp()
                article_str = "{0} ({1})\n{2}\n".format(
                    tools.ascii_encode(article.title),
                    tools.ascii_encode(article_url),
                    tools.ascii_encode(article.summary))
                output_strs.append(article_str)
            final_output = "\n--\n".join(output_strs)
            # Save the final output before returning it
            session.run("MATCH (s:Site {url: {site_url}})"
                        "SET s.value = {output}"
                        "SET s.timestamp = {timestamp}",
                        {"site_url": self._site_url,
                         "output": final_output,
                         "timestamp": time.time()}
                        )
            return final_output
        except Exception as ex:
            exception_args, exception_type = (ex.args, type(ex).__name__)
            error_string = "Attempted compilation of site {0} raised a {1} error with arguments {2}".format(
                self._site_url, exception_type, exception_args
            )
            self._build_status = error_string
            self.errors.append({
                "type": "error",
                "id": "ARGUMENT_SITE_COMPILE_FAIL",
                "text": error_string,
                "status": falcon.HTTP_INTERNAL_SERVER_ERROR
            })
            return False
        finally:
            session.close()

    def _cache(self):
        """
        Cache a site
        """
        log.debug("Caching articles from site {0} for user {1}".format(self._site_url, self._user_data["username"]))
        # Check to see if the site has been recently cached
        session = self._graph.session()
        site_caches = session.run("MATCH (s:Site {url: {site_url}}) RETURN (s)",
                                  {"site_url": self._site_url})
        session.close()
        # If the site has been cached
        if site_caches:
            cache = site_caches[0]
            # Check the timestamp of the cache
            cache_timestamp = cache["timestamp"]
            current_time = time.time()
            # Check if it was cached within the cache interval
            time_delta = current_time-cache_timestamp
            # The cache is expired, reload the cache
            if time_delta >= self.cache_time:
                self._site_cache = self._compile_site()
            # If everything is in order, return the cached site
            else:
                self._site_cache = cache["value"]
        # Create the cache
        else:
            self._site_cache = self._compile_site()
        return self._site_cache

    def value(self, command_obj):
        return self._site_cache

    def build(self):
        user_data = self._user_data
        user_sites = user_data["sites"]
        if self.site_type in user_sites.keys():
            self._site_url = user_sites[self.site_type]
            return self._cache
        else:
            error_string = "Couldn't a {} site within user saved sites".format(self.site_type)
            self._build_status = error_string
            self.errors.append({
                "type": "error",
                "text": error_string,
                "id": "SITE_ARGUMENT_INVALID"
            })
            return False


class News(Site):
    site_type = "news"


# Build a list of argument classes in the file
# Iterate through the classes
for c in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    # Check that the parent is the Argument class
    if inspect.getmro(c[1]) == Argument:
        argument_list.append(c)
log.debug("Loaded {0} classes: {1}".format(len(argument_list), argument_list))