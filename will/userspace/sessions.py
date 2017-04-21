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

ended_sessions = []

# Pull the user data from the database, find what plugins they have enabled, and cache all the data for the user


class Command:

    parent = None
    allow_response = False
    plugin = None
    responses = []

    @property
    def age(self):
        """
        The age of the command
        
        :return age_delta: a timedelta representing how long the command has existed 
        """
        return (datetime.datetime.now()-self.created).total_seconds()

    def response(self, new_command):
        if self.allow_response:
            new_command_obj = Command(new_command)
            new_command_obj.plugin = self.plugin
            new_command_obj.parent = self
            self.responses.append(new_command_obj)
            self.allow_response = False
            return True
        else:
            return False

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
    arguments = {}

    @property
    def argument_errors(self):
        """
        Give information about cached argument errors and wipe the cached data
        
        :return errors: A error response object with information about the argument errors
        """
        errors = []
        for argument in self.arguments.values():
            errors += argument.errors
            argument.errors = []
        log.debug("Fetched cached information about {0} argument errors, serving it to the user".format(
            len(errors)
        ))
        return {
            "errors": errors,
            "meta":
                {"text": "All argument errors served. It is possible that not all of these must be fixed to run "
                         "the plugin, however they should be fixed for best usage."}
        }

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
        """
        Route a response to a plugin query
        
        :param command_id: A command uid that represents an instantiated command within this esssion
        :param response_text: The text of the response
        :return answer: The answer the plugin returned 
        """
        if command_id in self.commands.keys():
            log.debug("Processing response {0} to command {1}".format(
                response_text, command_id
            ))
            command_class = self.commands[command_id]
            # Form a command object out of the response, and call it like a normal plugin
            if command_class.response(response_text):
                command_plugin = command_class.plugin
                self.commands.update({command_class.uid: command_class})
                return self._call_plugin(command_plugin, command_class, method="response")
            else:
                return {
                    "errors":
                        [{
                            "type": "error",
                            "id": "COMMAND_RESPONSE_INVALID",
                            "status": falcon.HTTP_BAD_REQUEST,
                            "text": "Command id {0} did not register for a response".format(command_id)
                        }]
                }

        else:
            return {
                "errors":
                    [{
                        "type": "error",
                        "id": "COMMAND_ID_INVALID",
                        "status": falcon.HTTP_BAD_REQUEST,
                        "text": "Command id {0} does not exist in this session".format(command_id)
                    }]
            }
    def _call_plugin(self, plugin, command_obj, method="exec"):
        """
        Call a plugin after finding it.
        Additionally, make sure none of the arguments are in an errored state
        
        :param plugin: A plugin class object 
        :return response: The answer, what the user will see
        """
        # Check the plugins arguments
        plugin_arguments = plugin.arguments
        # Search own arguments for that
        passed_args = {}
        for argument in plugin_arguments:
            arg_name = argument.name
            session_argument = self.arguments[arg_name]
            # Get the cached value of the argument
            arg_value = session_argument.value(command_obj)
            # Check if the plugin was built successfully
            if arg_value:
                passed_args.update({arg_name: arg_value})
            # There's an argument error. Use this opportunity to collect argument error information and return it
            else:
                log.debug("Argument {0} threw an error while processing a command for user {1}. Fetching all "
                          "cached argument errors".format(
                    arg_name, self._user_data["username"]
                ))
                response = self.argument_errors
                return response
        # Run the found plugin
        try:
            # Link the command to a plugin
            command_obj.plugin = plugin
            if method == "exec":
                response = plugin.exec(passed_args)
            elif method == "response":
                response = plugin.response(passed_args)
            else:
                raise NameError("Method {0} does not exist in the plugin".format(method))
            response_keys = response.keys()
            # if the command went through succesfully, update it with metadata
            if "data" in response.keys():
                response["data"].update({
                    "command_id": command_obj.uid
                })
            elif "errors" not in response_keys:
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
        elif match_len >= 2:
            command_obj.allow_response = True
            return {
                "data":
                    {
                        "type": "response",
                        "id": "PLUGIN_RESPONSE_REQUIRED",
                        "text": "Which plugin would you like to run?",
                        "options": [p.name for p in matching_plugins]
                    }
            }
        # If no plugins were found
        # TODO: use the chatbot or implement search or both using a setting
        else:
            if "default_plugin" in self._user_data["settings"].keys():
                pass
            else:
                return {
                    "errors": [{
                        "type": "error",
                        "status": falcon.HTTP_INTERNAL_SERVER_ERROR,
                        "text": "Settings for user {0} didn't contain a default plugin"
                    }]
                }
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
        ended_sessions.append(self.session_id)
        # Delete self
        if self.session_id in sessions.keys():
            del sessions[self.session_id]
            return True
        else:
            log.error("Logout called for session that wasn't properly instantiated")
            return False

    @property
    def age(self):
        return (datetime.datetime.now()-self.created).total_seconds()
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
            self.arguments.update({type(instantiated_argument).__name__, instantiated_argument})

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