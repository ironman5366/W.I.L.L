#Builtin imports
import logging
import threading
import time

# Internal imports
from will.exceptions import *
from will.userspace import sessions, cache_utils

# External imports
from neo4j.v1 import GraphDatabase, basic_auth


log = logging.getLogger()

running = True


def configure_loop(graph, configuration_data):
    # The amount of time the user space should wait between each loop
    loop_wait = 1
    if "loop_wait" in configuration_data.keys():
        loop_setting = configuration_data["loop_wait"]
        if type(loop_setting) in (int, float):
            loop_wait = loop_setting
        elif type(loop_setting) == str:
            if loop_setting.is_digit():
                loop_wait = float(loop_setting)
            else:
                error_str = "Loop setting {0} is a string and can't be converted to a float".format(loop_setting)
                log.error(error_str)
                raise ConfigurationError(error_str)
        else:
            error_str = "Unsupported type {0} for setting loop_wait".format(type(loop_setting))
            log.error(error_str)
            raise ConfigurationError(error_str)
    loop_wait = loop_wait
    return loop_wait

def start(configuration_data, plugins):
    sessions.plugins = plugins
    log.debug("Loading user database")
    db_configuration = configuration_data["db"]
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
    graph = GraphDatabase.driver("bolt://{host}:{port}".format(
        host=db_configuration["host"],
        port=db_configuration["port"]),
        auth=basic_auth(
            db_configuration["user"],
            db_configuration["password"]
        )
    )
    graph = graph
    log.debug("Successfully connected to database at {0}:{1} with username {2}".format(
        db_configuration["host"],
        db_configuration["port"],
        db_configuration["user"]
    ))
    log.debug("Loading cache configuration")
    cache_configuration = configuration_data["cache"]
    error_cause = None
    try:
        error_cause = "threads"
        assert type(cache_configuration["threads"]) == int
    except (KeyError, AssertionError):
        error_string = "Cache configuration is invalid. Please check the {0} field".format(error_cause)
        log.error(error_string)
        raise ConfigurationError(error_string)
    # TODO: write a custom event loop/session monitor
    loop_wait = configure_loop(graph, configuration_data)
    cache_manager = cache_utils.cache(plugins, graph, cache_configuration["threads"])
    # Load caches for all datastores, public and private
    datastores = graph.session().run("MATCH (d:DataStore) return (d)")
    cache_manager.cache_multi(datastores)
    #event_thread = threading.Thread(event_loop, args=(loop_wait, graph, configuration_data))
    #event_thread = event_thread
    #event_thread.start()
    log.debug("Started event loop thread")