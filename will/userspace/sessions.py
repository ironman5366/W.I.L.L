# Builtin imports
import logging
import uuid
import datetime
import threading
import time

# Internal imports
from will import tools
from will.core import arguments

# External imports
import falcon

log = logging.getLogger()

graph = None

sessions = {}

plugins = []

# Pull the user data from the database, find what plugins they have enabled, and cache all the data for the user


class Command:

    @property
    def age(self):
        """
        The age of the command
        
        :return age_delta: a timedelta representing how long the command has existed 
        """
        return (datetime.datetime.now()-self.created).total_seconds()

    def __init__(self, command):
        """
        Set basic command information, and assign a unique identifier for later reference
        
        :param command: The plaintext of the command
        """
        # A unique identifier for the command
        self.uid = uuid.uuid1()
        # Parse the command with spacy
        self.parsed = tools.parser(command)
        self.verbs = [w.lemma_.lower() for w in self.parsed if w.pos_ == "VERB"]
        # The plaintext of the command
        self.text = command
        # The time the command was created
        self.created = datetime.datetime.now()


class Session:
    _user_data = None
    commands = {}
    _arguments = {}
    responses = {}

    def set_response(self, command_id, response_plugin):
        """
        Set a response object in the class data
        
        :param command_id:
        :param response_plugin: 
        
        """
        # TODO: assert that it's a member of the plugin
        self.responses.update({command_id: response_plugin})

    def _make_command(self, command_text):
        """
        Create a command class and update the internal command dictionary accordingly
        
        :param command_text: The plaintext of the command
        :return command_class: The instantiated command class 
        """
        log.debug("Instantiating command {0}".format(command_text))
        command_class = Command(command_text)
        self.commands.update({
            command_class.uid: command_class
        })
        return command_class

    def process_response(self, command_id, response_text):
        if command_id in self.responses.keys():
            log.debug("Processing response {0} to command {1}".format(
                command_id, response_text
            ))
            # Form a command object out of the response, and call it like a normal plugin
            response_command = self._make_command(response_text)
            response_plugin = self.responses[command_id]
            return self._call_plugin(response_plugin, response_command)
        else:
            return {
                "errors":
                    [{
                        "type": "error",
                        "id": "COMMAND_ID_INVALID",
                        "status": falcon.HTTP_BAD_REQUEST,
                        "text": "Command id {0} did not register for a response".format(command_id)
                    }]
            }
    def _call_plugin(self, plugin, command_obj):
        """
        Call a plugin after finding it
        
        :param plugin: A plugin class object 
        :return response: The answer, what the user will see
        """
        # Check the plugins arguments
        plugin_arguments = plugin.arguments
        # Search own arguments for that
        passed_args = {}
        for argument in plugin_arguments:
            arg_name = type(argument).__name__
            session_argument = self._arguments[arg_name]
            # Get the cached value of the argument
            arg_value = session_argument.value(command_obj)
            passed_args.update({arg_name: arg_value})
        # Run the found plugin
        try:
            response = plugin.exec(passed_args)
            response_keys = response.keys()
            if "data" not in response_keys and "errors" not in response_keys:
                log.warning("Plugin {0} returned a malformed response {1}".format(plugin.name, response))
                response = {
                    "errors":
                        [{
                            "type": "error",
                            "id": "PLUGIN_RESPONSE_MALFORMED",
                            "status": falcon.HTTP_INTERNAL_SERVER_ERROR,
                            "text": "Plugin {0} returned a malformed response".format(plugin.name)
                        }]
                }
        except Exception as ex:
            exception_type, exception_args = (type(ex).__name__, ex.args)
            error_string = "Plugin {plugin_name} threw a {error_type} error, with arguments {arguments}. The error " \
                           "was triggered the command {error_command} from user {error_user}".format(
                            plugin_name=plugin.name,
                            error_type=exception_type,
                            arguments=exception_args,
                            error_command=command_obj.text,
                            error_user=self.user_data["username"])
            log.warning(error_string)
            response = {
                "errors":
                    [{
                        "type": "error",
                        "id": "PLUGIN_ERROR",
                        "status": falcon.HTTP_INTERNAL_SERVER_ERROR,
                        "text": "Plugin {0} returned an error.".format(
                            plugin.name
                        )
                    }]
            }
        # The response is an API suitable dictionary
        return response

    def command(self, command_str):
        """
        Run a command in the context of the session
        
        :param command_str: The raw command 
        :return result: The result of the command 
        """
        command_obj = self._make_command(command_str)
        # See which plugins match
        matching_plugins = []
        for plugin in plugins:
            # Call the plugins check function to see if it matches the command
            if plugin.check(command_obj):
                matching_plugins.append(plugin)
        match_len = len(matching_plugins)
        log.debug("Found {0} matching plugins for command {1}".format(match_len, command_obj.uid))
        final_plugin = None
        # If exactly 1 plugin was found
        if match_len == 1:
            final_plugin = matching_plugins[0]
        # TODO: set a response to ask the user
        elif match_len >= 2:
            pass
        # If no plugins were found
        # TODO: use the chatbot or implement search or both using a setting
        else:
            pass
        return self._call_plugin(final_plugin, command_obj)

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


    def reload(self):
        """
        Recache data for the user

        """
        log.debug("Reloading data for session belonging to user {0}".format(self.username))
        # Next time user_data and authentication are accessed they'll be reloaded
        self._user_data = None
        self._auth_done = False
        self.last_reloaded = datetime.datetime.now()

    def _build_arguments(self):
        for argument in arguments.argument_list:
            # Build the argument
            instantiated_argument = argument(self.user_data, self.client_id, self, graph)
            self._arguments.update({type(instantiated_argument).__name__, instantiated_argument})

    def __init__(self, username, client_id):
        """
        Instantiate a session and add metadata

        :param username: 
        :param client_id: 
        """
        # Make sure the graph has been loaded before the class is instantiated
        assert graph
        self.username = username
        self.client_id = client_id
        self.created = datetime.datetime.now()
        self.last_reloaded = self.created
        # Generate a session id and add self to the sessions dictionary
        self.session_id = uuid.uuid4()
        # Build arguments
        self._build_arguments()
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