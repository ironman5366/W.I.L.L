#Builtin imports
import logging
import threading
import time
#External imports
from py2neo import Graph, Path
#Internal imports
from exceptions import *
from userspace import cache_utils

log = logging.getLogger()

class userspace():

    def event_loop(self):
        while self.running:
            # List of user dicts
            users = self.graph.run("match (u:User) return (u)").data()
            for user in users:
                # If the user is online, make sure that everything they need is cached
                # Properties that need to be cached will be of the type DataStore
                if user["online"]:
                    datastores = self.graph.run("match (u)-[r]->(d:DataStore) return (d)")
                    for datastore in datastores:
                        last_cached = datastore["last_cached"]
                        # If it hasn't been cached in the past 5 minutes, start a new thread to cache it
                        if time.time()-last_cached >= 300:
                            cache_thread = threading.Thread(target=self.cache_manager.cache_one(datastore))
                            cache_thread.start()
                            self.cache_threads.append(cache_thread)
            time.sleep(self.loop_wait)

    def configure_loop(self):
        assert self.graph
        assert self.configuration_data
        # The amount of time the user space should wait between each loop
        loop_wait = 0.1
        if "loop_wait" in self.configuration_data.keys():
            loop_setting = self.configuration_data["loop_wait"]
            if type(loop_setting) in (int, float):
                loop_wait = loop_setting
            elif type(loop_setting) == str:
                if loop_setting.is_digit():
                    loop_wait = float(loop_setting)
                else:
                    error_str = "Loop setting {0} is a string and can't be converted to a float"
                    log.error(error_str)
                    raise ConfigurationError(error_str)
            else:
                error_str = "Unsupported type {0} for setting loop_wait".format(type(loop_setting))
                log.error(error_str)
                raise ConfigurationError(error_str)
        self.loop_wait = loop_wait
    def __init__(self, configuration_data):
        self.configuration_data = configuration_data
        log.debug("Loading user database")
        db_configuration = self.configuration_data["db"]
        error_cause = None
        try:
            error_cause = "host"
            assert type(db_configuration["host"]) == str
            error_cause = "port"
            assert type(db_configuration["port"]) == int
            error_cause = "user"
            assert type(db_configuration["user"]) == str
            error_cause = "password"
            assert type(db_configuration["password"]) == str
        except (KeyError, AssertionError):
            error_string = "Database configuration is invalid. Please check the {0} field".format(error_cause)
            log.error(error_string)
            raise CredentialsError(error_string)
        graph = Graph(
            host=db_configuration["host"],
            port=db_configuration["port"],
            user=db_configuration["user"],
            password=db_configuration["password"])
        self.graph = graph
        log.debug("Successfully connected to database at {0}:{1} with username {2}".format(
            db_configuration["host"],
            db_configuration["port"],
            db_configuration["user"]
        ))
        log.debug("Checking for custom user loop preferences and running the event loop and monitor")
        # Configure the loop settings
        self.configure_loop()
        # Shutdown switch
        self.running = True
        event_thread = threading.Thread(target=self.event_loop)
        self.event_thread = event_thread
        event_thread.start()
        self.cache_manager = cache_utils.cache(graph)
        self.cache_threads = []
        log.debug("Started event loop thread")
