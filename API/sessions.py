#Builtin imports
import logging
import uuid
import datetime

#External imports
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
        # Determine whether the user has any other active sessions
        user_still_online = any([x.username == self.username for x in sessions.values()])
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
        del sessions[self.session_id]

    @property
    def report(self):
        """
        Basic information about the session, suitable for a detailed view in an admin console
        
        :return report: 
        """
        report_string = "Id:{session_id}\nUser:{user}\nCommands Processed:{command_len}\n"
    @property
    def user_data(self):
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
        :return: 
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

    def __init__(self, username, password, client):
        # Make sure the graph has been loaded before the class is instantiated
        assert (graph)
        # Generate a session id
        self.username = username
        self._password = password
        self.client = client
        self.created = datetime.datetime.now()

# TODO: session manager thread that goes through and reloads data from old sessions, and logs out sessions that haven't been used