# Builtin imports
import logging
import uuid
import datetime
import queue
import time

# Internal imports
from will.core import arguments
from will import tools

# External imports
import falcon
import requests

log = logging.getLogger()

graph = None

sessions = {}

plugins = []

ended_sessions = []

session_manager = None

# Pull the user data from the database, find what plugins they have enabled, and cache all the data for the user


class Notification:

    # TODO: check the users notification preferences

    def email(self, mailgun_key, mailgun_url):
        """
        Send an email to the user

        :param mailgun_key:
        :param mailgun_url:
        """
        email = self.user_data["settings"]["email"]
        first_name = self.user_data["first_name"]
        last_name = self.user_data["last_name"]
        return requests.post(
            mailgun_url,
            auth=("api", mailgun_key),
            data={"from": "will <postmaster@willbeddow.com>",
                  "to": "{0} {1} <{2}>".format(first_name, last_name, email),
                  "subject": self.summary,
                  "text": self.message})

    @property
    def time_reached(self):
        return time.time() >= self.trigger_time

    @property
    def summary(self):
        if not self._summary:
            # Use the first 5 words of the message for a summary
            if " " in self.message:
                message_words = self.message.split(" ")
                if len(message_words) >= 5:
                    self._summary = message_words[0:4]
                else:
                    self._summary = self.message
            else:
                self._summary = self.message
            self._summary = tools.ascii_encode(self._summary)
        return self._summary

    def __init__(self, message, title, trigger_time, scope, user_data, summary=None):
        # Decode the message and the title into ascii for maximum compatibility
        self.title = tools.ascii_encode("W.I.L.L - "+title)
        self.message = tools.ascii_encode(message)
        self.scope = scope
        self._summary = summary
        self.created = datetime.datetime.now()
        self.uid = uuid.uuid1()
        self.trigger_time = trigger_time
        self.user_data = user_data


class Command:

    parent = None
    allow_response = False
    plugin = None
    responses = []
    ents = {}

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
        # Use spacy's ent recognition
        for ent in self.parsed.ents:
            self.ents.update({
                ent.label_: ent.text
            })


class Session:

    instantiated = False
    _user_data = None
    commands = {}
    arguments = {}
    notifications = queue.Queue()

    def __init__(self, username, client_id, dynamic):
        """
        Instantiate a session and add metadata

        :param username:
        :param client_id:
        :param dynamic: A dict of dynamic variables
        """
        # Make sure the graph has been loaded before the class is instantiated
        assert graph
        self.username = username
        self.dynamic = dynamic
        self.client_id = client_id
        self.created = datetime.datetime.now()
        self.last_reloaded = datetime.datetime.now()
        # Generate a session id and add self to the sessions dictionary
        self.session_id = str(uuid.uuid4())
        # Add the argument builder to the build queue in the session manager class
        session_manager.build_queue.put(self)
        # Update the sessions dictionary with the instance, keyed by the session id
        sessions.update({
            self.session_id: self
        })

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
        
        :param command_id: A command uid that represents an instantiated command within this session
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

    def notification(self, message, trigger_time, title="", scope="all"):
        # TODO: check scope
        not_object = Notification(message, title, trigger_time, scope)
        self.notifications.put(not_object)

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
        if self.instantiated:
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

        # If the plugin hasn't been built yet, wait until it has been
        else:
            log.debug("Session {} was called before it was ready".format(self.session_id))
            return {
                "errors":
                    [{
                        "type": "error",
                        "status": falcon.HTTP_SERVICE_UNAVAILABLE,
                        "text": "Session {} has not yet finished building required arguments. Please wait before "
                                "submitting commands".format(self.session_id),
                        "id": "SESSION_NOT_READY"
                    }]
            }

    def logout(self):
        """
        Finish the session

        :return bool: a bool indicating whether the logout was successful
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
    def stale(self):
        return ((datetime.datetime.now()-self.last_reloaded).total_seconds >= 900)

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

    def __str__(self):
        session_data = "Session {0}:\n\n{1}".format(self.session_id, self.report)
        return session_data

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
        log.debug("Reloading data for session {0} belonging to user {1}".format(self.session_id, self.username))
        # Next time user_data and authentication are accessed they'll be reloaded
        self._user_data = None
        self.last_reloaded = datetime.datetime.now()

    def build_arguments(self):
        for argument in arguments.argument_list:
            # Build the argument
            instantiated_argument = argument(self.user_data, self.client_id, self, graph)
            self.arguments.update({type(instantiated_argument).__name__, instantiated_argument})
        self.instantiated = True

