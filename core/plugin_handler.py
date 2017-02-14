#Builtin imports
import logging
import os
import sys
import time
import traceback

#External imports
import importlib

log = logging.getLogger()

dir_path = 'core/plugins'

plugin_subscriptions = []

command_plugins = {}

default_plugin_data = None


class subscriptions():
    '''
    Manage plugin subscriptions and events
    '''
    def call_plugin(self, plugin_function, event):
        """
        Call a plugin

        :param plugin_function:
        :param event:
        :return: a response object
        """
        log.debug("Calling function {0} with event data {1}".format(
            plugin_function, event
        ))
        #Call the plugin. If there's a response, return it. If there's not, return "Done"
        try:
            response = plugin_function(event)
            assert type(response) == dict
        except Exception as call_exception:
            response = {"type": "error", "text": None, "data": {}}
            exc_type, exc_value, exc_traceback = sys.exc_info()
            user_table = event["user_table"]
            #If the user is an adminstrator, give them the full error message.
            #If not, just let them know that an error occurred
            #Log the error regardless
            error_string = repr(traceback.format_exception(exc_type, exc_value,
                                                  exc_traceback))
            log.error(error_string)
            if user_table["admin"]:
                response["text"] = error_string
            else:
                response["text"] = "An error occurred while executing plugin"
        if not response:
            response = {"type": "success", "text": "Done", "data":{}}
        #Send the message
        return response

    def process_event(self, event, db):
        """
        Select the right plugin for a command event and run it

        :param event:
        :param db:
        :return a response object:
        """
        user_data = db["users"]
        time.sleep(0.1)
        log.debug("Processing event {0}".format(event))
        #If the queue is empty, pass
        assert type(event) == dict
        event.update(dict(db=db))
        event_command = event["command"]
        log.debug("Event session is {0}".format(event["session"]))
        username = event["session"]["username"]
        log.info("Processing event with command {0}, user {1}".format(
            event_command, username))
        user_table = user_data.find_one(username=username)
        event.update({"user_table":user_table})
        event.update({"username":username})
        found_plugins = []
        default_plugin_name = user_table["default_plugin"]
        def plugin_check(plugin):
            '''Run the plugins check function to see if it's true'''
            log.debug(plugin)
            check_function = plugin["check"]
            log.debug("Running check_function {0} on plugin {1}".format(
                check_function, plugin))
            if check_function(event):
                log.info("Plugin {0} matches command {1}".format(
                    plugin, event_command
                ))
                if plugin["name"] != default_plugin_name:
                    found_plugins.append(plugin)
        #Map the subscribed plugins to the function that runs their check functions
        list(map(plugin_check, plugin_subscriptions))
        #How many plugins match the command data
        plugin_len = len(found_plugins)
        if plugin_len == 1:
            plugin = found_plugins[0]
            log.info("Running plugin {0}".format(plugin))
            plugin_function = plugin['function']
            #Call the plugin
            return self.call_plugin(plugin_function,event)
        elif plugin_len > 1:
            #Ask the user which one they want to run
            plugin_names = {}
            map(lambda plugin_name: plugin_names.update(
                {"name": plugin_name["name"],"function":plugin_name["function"]
                                                         }))
            #Check which plugin the user wants to run and then run that
            log.info("Checking which plugin the user wants to run, found plugins {0}".format(
                plugin_names
            ))
            interface.check_plugins(plugin_names,event)
        else:
            default_plugin = user_table["default_plugin"]
            #I wish I had a more efficient way to do this
            default_plugin_func = None
            for i in plugin_subscriptions:
                if i["name"] == default_plugin:
                    default_plugin_func = i["function"]
                    break
            if default_plugin_func:
                #Call the default plugin
                return self.call_plugin(default_plugin_func, event)
            else:
                error_message = "Couldn't find defafult plugin {0} in plugin list {1}".format(
                    default_plugin, plugin_subscriptions
                )
                #Send the error message to the user
                log.error(error_message)
                return {"type": "error", "text":error_message, "data": {}}

def process_plugins(path):
    """
    Process and import the plugins

    :param path:
    """
    log.info("In process plugins")
    log.info("Processing plugin {0}".format(path))
    python_loader = PythonLoader(path)
    try:
        python_loader.load()
    except IOError:
        return

def subscribe(subscription_data):
    """
    Provides a decorator for subscribing plugin to commands

    :param subscription_data: A dict containing the name and check function
    """
    assert(type(subscription_data) == dict)
    def wrap(f):
        #Subscrbe the plugin, and while processing them pluck out the default plugin
        #So it doesn't have to be searched for later
        log.info("Subscribing function {0} to data {1}".format(
            f, subscription_data
        ))
        subscription_data.update({
            'function': f
        })
        log.info("Appending subscription data {0} to plugin subscriptions".format(subscription_data))
        plugin_subscriptions.append(subscription_data)
    return wrap

def load(dir_path, DB):
    """
    Run the plugin loader on processed plugins

    :param dir_path:
    :param DB:
    """
    log.info("Finding plugins in directory {0}".format(dir_path))
    plugins = [os.path.join(dir_path, module_path)
                       for module_path in os.listdir(dir_path)]
    log.info("Found {0} plugins".format(len(plugins)))
    [process_plugins(path) for path in plugins]
    map(process_plugins, plugins)
    log.info("Finished parsing and loading plugins, processing subscriptions")

class PythonLoader:
    '''The class that loads the plugins'''

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        """
        Use importlib to import the plugin file

        """
        if self.is_plugin():
            log.info("Loading plugin: {0}".format(self.file_path))
            self.update_path()
            importlib.import_module(self.import_name())

    def is_plugin(self, fs_tools=os.path):
        """
        Determine whether a file in the plugin directory is a plugin

        :param fs_tools:
        :return boolean:
        """
        if fs_tools.exists(self.file_path):
            if fs_tools.isfile(self.file_path) and \
                    self.file_path.endswith('.py'):
                return True
            if fs_tools.isdir(self.file_path):
                init_file = os.path.join(self.file_path, "__init__.py")
                if fs_tools.exists(init_file) and fs_tools.isfile(init_file):
                    return True
        return False

    def import_name(self):
        """
        Properly format a plugin name for import

        :return a file path:
        """
        if self.file_path.endswith('.py'):
            return os.path.basename(self.file_path).split('.')[0]
        else:
            return os.path.basename(self.file_path)

    def update_path(self):
        """
        Append data to sys.path

        """
        lib_path = self._lib_path()
        if lib_path not in sys.path:
            sys.path.append(lib_path)

    def _lib_path(self):
        """
        Manipulates the file path

        :return updated file path:
        """
        return os.path.normpath(
            os.sep.join(os.path.normpath(self.file_path).split(os.sep)[:-1])
        )



