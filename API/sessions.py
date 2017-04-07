# Builtin imports
import logging
import uuid
import datetime
import threading
import time

# External imports
import bcrypt

log = logging.getLogger()

graph = None

sessions = {}


class Session:

    session_id = None
    _user_data = None
    _auth_done = False
    _authenticated = False
    commands = []

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

    @property
    def _auth(self):
        """
        Authentication
        
        :return: 
        """
        if self._auth_done:
            return self._authenticated
        else:
            user_data = self.user_data
            self._auth_done = True
            if user_data:
                pw_hash = user_data["password"]
                pw_check = bcrypt.checkpw(self._password, pw_hash)
                if pw_check:
                    log.debug("Logged in user {0} successfully".format(self.username))
                    self._authenticated = True
                    return True
                else:
                    log.debug("Failed login attempt for user {0}".format(self.username))
            self._authenticated = False
            return False

    def start_session(self):
        """
        Generate a session id, update the database to show that the user is online, and add self to 
        
        :return bool: A bool indicating whether authentication was sucessful and the session started 
        """
        if self._auth:
            session_id = uuid.uuid1()
            self.session_id = session_id
            # Mark that the user is online in the database
            session = graph.session()
            session.run(
                "MATCH (u:User {username: {username})"
                "SET u.online=true",
                {"username": self.username}
            )
            session.close()
            sessions.update({
                self.session_id: self
            })
            return True
        else:
            return False

    def reload(self):
        """
        Reload possibly old data in a session
        
        """
        log.debug("Reloading data for session belonging to user {0}".format(self.username))
        # Next time user_data and authentication are accessed they'll be reloaded
        self._user_data = None
        self._auth_done = False
        self.last_reloaded = datetime.datetime.now()

    def __init__(self, username, password, client):
        """
        Instantiate a session and add metadata
        
        :param username: 
        :param password: 
        :param client: 
        """
        # Make sure the graph has been loaded before the class is instantiated
        assert graph
        # Generate a session id
        self.username = username
        self._password = password
        self.client = client
        self.created = datetime.datetime.now()
        self.last_reloaded = self.created


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
                if current_time-session.last_reloaded.total_seconds() >= 3600:
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