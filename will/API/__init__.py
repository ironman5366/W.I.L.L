# Builtin imports
import logging
import datetime

# External imports
import falcon

# Internal imports
from will.exceptions import *
from will.API import hooks, middleware, v1 ,router
from will.userspace import sessions
from itsdangerous import Signer, TimestampSigner

log = logging.getLogger()


class App:
    """
    The object representing the loaded API
    """
    _conf_loaded = False
    signer = None
    timestampsigner = None
    monitor_instance = None
    versions = [v1]

    def __init__(self, configuration_data, session_manager, db, app_callable=falcon.API):
        """
        Instantiate and build various components of the API and create the app object
        
        :param configuration_data: The loaded data from will.conf 
        :param session_manager: The session manager thread that is running curating sessions. Will be used by API 
        components
        :param db: The connection to mysql.
        :param app_callable: The WSGI instance to pass the middleware to. Adding it as a parameter allows things like
        mocking within unit testing, and other customization.
        """
        self.configuration_data = configuration_data
        self.session_manager = session_manager
        self.db = db
        hooks.db = db

        # Process the API settings
        self._load_configuration()
        # Build the middleware classes
        self.middleware = self._load_middleware()
        # Call the falcon API
        self.app = app_callable(
            middleware=self.middleware
        )
        router.process_routes(self.app)
        start_time = datetime.datetime.now()
        log.debug("Starting API at {}".format(start_time.strftime("%c")))
        for version in self.versions:
            version.db = db
            version.start_time = start_time


    def _load_middleware(self):
        """
        Instantiate the middleware classes
        :return middleware: A list containing the instantiated classes 
        """
        self.monitor_instance = middleware.MonitoringMiddleware(banned_ips=self.configuration_data["banned-ips"])
        return [
            self.monitor_instance,
            middleware.RequireJSON(),
            middleware.JSONTranslator(),
            middleware.AuthTranslator()
        ]

    def _load_configuration(self):
        """
        Go through relevant configuration keys and load it into the class, checking for correct types as it goes.
        Throw an error if any of the keys are missing or of the wrong type
        Required keys:
            - secret-key: str: the key that the HMAC signer will use
            - banned-ips: (list, set): an iterable of permanently banned ips that the API should always refuse requests
            from
        """
        try:
            error_cause = "secret-key"
            secret_key = self.configuration_data["secret-key"]
            assert type(secret_key) == str
            self.signer = Signer(secret_key)
            self.timestampsigner = TimestampSigner(secret_key)
            hooks.signer = self.signer

            v1.signer = self.signer
            v1.timestampsigner = self.timestampsigner
            error_cause = "banned-ips"
            assert type(self.configuration_data["banned-ips"]) in (list, set)
        except (KeyError, AssertionError):
            error_string = "Please ensure that {0} is properly defined in your configuration_file.".format(error_cause)
            log.error(error_string)
            raise ConfigurationError(error_string)
        self._conf_loaded = True

    def kill(self):
        """
        Kill the API and logout of all of the sessions
        
        """
        log.debug("Kill called, ending {} sessions".format(len(sessions.sessions)))
        for session in sessions.sessions:
            session.logout()
        self.session_manager.running = False
        # Kill the monitoring middleware ban thread
        self.monitor_instance.running = False