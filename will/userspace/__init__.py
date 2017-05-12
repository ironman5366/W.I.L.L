#Builtin imports
import logging
import threading
import time

# Internal imports
from will.exceptions import *
from will.userspace import sessions, session_manager

# External imports
from neo4j.v1 import GraphDatabase, basic_auth


log = logging.getLogger()

running = True
graph = None


def key_cache():
    """
    Go through neo4j, check for keys that are renewed, and give them a new timestamp
    """
    session = graph.session()
    for key in session.run("MATCH (k:APIKey) return (k)"):
        # Check if it's been more than the refresh value of the key since it's been refreshe
        if time.time()-key["timestamp"] >= key["refresh"]:
            session.run("MATCH (k:APIKey {value: {value}})"
                        "set k.usages=0"
                        "set k.timestamp=timestamp();",
                        {"value": key["value"]})
    session.close()

def start(configuration_data, plugins):
    global graph
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
    connection_url = "bolt://{host}:{port}".format(
        host=db_configuration["host"],
        port=db_configuration["port"]
    )
    log.debug("Connecting to database at {}".format(connection_url))
    graph = GraphDatabase.driver(connection_url,
        auth=basic_auth(
            db_configuration["user"],
            db_configuration["password"]
        )
    )
    log.debug("Successfully connected to database at {0}:{1} with username {2}".format(
        db_configuration["host"],
        db_configuration["port"],
        db_configuration["user"]
    ))
    # Refresh the API keys
    key_cache()
    session_class = session_manager.SessionManager(graph)
    # Load caches for all datastores, public and private
    log.debug("Started event loop thread")
    return session_class