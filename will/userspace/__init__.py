# Builtin imports
import logging
import datetime

# Internal imports
from will.exceptions import *
from will.schema import *
from will.userspace import sessions, session_manager, notifications

# External imports
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

log = logging.getLogger()

running = True
db = None


def get_engine(uri, echo):
    options = {
        'pool_recycle': 3600,
        'pool_size': 10,
        'pool_timeout': 30,
        'max_overflow': 30,
        'echo': echo,
    }
    return create_engine(uri, **options)


def key_cache():
    """
    Go through neo4j, check for keys that are renewed, and give them a new timestamp
    """
    session = db()
    keys = session.query(APIKey).all()
    dt = datetime.datetime.now()
    for key in keys:
        # Check if it's been more than the refresh value of the key since it's been refreshed
        if (dt - key.timestamp).total_seconds() >= key.refresh:
            key.usages = 0
            key.timestamp = dt
    session.commit()


def start(configuration_data, plugins):
    global db
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
    connection_url = "mysql://{username}:{password}@{db_url}/W.I.L.L".format(
        username=db_configuration["user"],
        password=db_configuration["password"],
        db_url=db_configuration["host"]
    )
    engine = create_engine(connection_url)
    db = sessionmaker(bind=engine)
    log.debug("Successfully connected to database at {0}:{1} with username {2}".format(
        db_configuration["host"],
        db_configuration["port"],
        db_configuration["user"]
    ))
    session = db()
    # Check whether the database is initialized, and initialize it if it isn't
    official_clients = session.query(Client).filter_by(official=True)
    if not official_clients:
        # Throw an error
        raise DBNotInitializedError("Connected to database at {0}:{1}, but couldn't find any official clients. "
                                    "To initialize the database, please run "
                                    "python3 create_db.py and go through the setup process")

    # Refresh the API keys
    key_cache()
    session_class = session_manager.SessionManager(db)
    # Put the session manager into the sessions file
    sessions.session_manager = session_class
    sessions.db = db
    # Instantiate the notification manager
    log.debug("Pulling cached notifications from database...")
    not_mangaer = notifications.NotificationHandler(db)
    sessions.notification_manager = not_mangaer
    log.debug("Finished loading userspace")
    return session_class
