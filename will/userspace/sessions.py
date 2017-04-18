# Builtin imports
import logging
import uuid
import datetime
import threading
import time

# Internal imports
from will import tools

log = logging.getLogger()

graph = None

sessions = {}

plugins = []

# Pull the user data from the database, find what plugins they have enabled, and cache all the data for the user

class Session:
    _user_data = None
    commands = {}
    arguments = []

    def _check_plugins(self, command_uid):
        """
        Run 
        
        :param command_uid: The command identifier
        """
        command_obj = self.commands[command_uid]
        parsed_command = command_obj["parse"]
        # Go through the words in the commands and see if any match the plugins
        for plugin in plugins:
            check_function = plugin["check"]
            # TODO: add a way that a check function can optionally request more arguments.
            # Possibly just build the command object and submit it
            if check_function(parsed_command):
                return plugin["function"]
        return False

    def command(self, command_str):
        """
        Run a command in the context of the session
        
        :param command_str: The raw command 
        :return result: The result of the command 
        """
        # Generate an id for this command
        command_uid = uuid.uuid1()
        self.commands.update({
            command_uid: {
                "id": command_uid,
                "text": command_str,
                "parse": tools.parser(command_str)
            }
        })
        log.debug("Created command object for command {0}, starting parsing".format(command_str))
        # TODO: possibly add more responses than just plugins.
        steps = [self._check_plugins]
        for step in steps:
            response = step()
            if response:
                if callable(response):
                    # TODO: check the plugin chain and call it with the appropriate arguments
                    pass
                else:
                    result = str(response)
                break
        return result


    def logout(self):
        """
        Finish the session

        :return bool: a bool indicating whether the logout was sucessful 
        """
        # Determine whether the user has any other active sessions
        user_still_online = False
        for session_id, session in sessions.items():
            if session_id != self.session_id:
                if session.username == self.username:
                    user_still_online = True
                    break
        # Change the database accordingly
        session = graph.session()
        session.run(
            "MATCH (u:User {username: {username}})"
            "SET u.online={online}",
            {
                "username": self.username,
                "online": user_still_online
            }
        )
        session.close()
        # Delete self
        if self.session_id in sessions.keys():
            del sessions[self.session_id]
            return True
        else:
            log.error("Logout called for session that wasn't instantiated")
            return False

    @property
    def report(self):
        """
        Basic information about the session, suitable for a detailed view in an admin console

        :return report: 
        """
        report_string = "Id:{session_id}\nUser:{user}\nCommands Processed:{command_len}\nCreated:{created}".format(
            session_id=self.session_id,
            user=self.username,
            command_len=len(self.commands),
            created=self.created
        )
        return report_string

    def _build_arguments(self):
        pass

    @property
    def user_data(self):
        """
        User data from the database. If there's none cached, match it from the db and return it.

        :return user_data: 
        """
        if self._user_data:
            return self._user_data
        else:
            session = graph.session()
            user_node = session.run(
                "MATCH (u:User {username: {username}}) RETURN (u)",
                {"username": self.username}
            )
            session.close()
            if user_node:
                user_data = user_node[0]
                self._user_data = user_data
                return user_data
            return False


    def reload(self):
        """
        Recache data for the user

        """
        log.debug("Reloading data for session belonging to user {0}".format(self.username))
        # Next time user_data and authentication are accessed they'll be reloaded
        self._user_data = None
        self._auth_done = False
        self.last_reloaded = datetime.datetime.now()

    def __init__(self, username, client_id):
        """
        Instantiate a session and add metadata

        :param username: 
        :param password: 
        :param client: 
        """
        # Make sure the graph has been loaded before the class is instantiated
        assert graph
        self.username = username
        self.client_id = client_id
        self.created = datetime.datetime.now()
        self.last_reloaded = self.created
        # Generate a session id and add self to the sessions dictionary
        self.session_id = uuid.uuid4()
        sessions.update({
            self.session_id: self
        })

class Monitor:
    # Kill switch for the monitor thread
    running = True

    @property
    def report(self):
        """
        Generate information about the session monitor

        :return report_string: The string containing the report 
        """
        session = graph.session()
        users_online = session.run(
            "MATCH (u:User {online: true}) RETURN (u)"
        )
        session.end()
        num_users_online = len(users_online)
        sessions_num = len(sessions)
        report_string = "{0} users online, with {1} active sessions".format(
            num_users_online, sessions_num
        )
        return report_string

    def _monitor(self):
        """
        A monitoring thread that reloads data for each session when it gets to old

        """
        log.debug("Starting session monitor thread")
        while self.running:
            # Iterate through the sessions
            for session_id, session in sessions.items():
                current_time = datetime.datetime.now()
                # Check if it was last reloaded more than an hour ago
                if current_time - session.last_reloaded.total_seconds() >= 3600:
                    session.reload()
            # Session monitoring is low priority so it can run infrequently
            time.sleep(30)

    def __init__(self):
        """
        Start the _monitor thread

        """
        # Start the monitoring thread
        monitor_thread = threading.Thread(target=self._monitor)
        monitor_thread.start()