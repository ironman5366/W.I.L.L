#Builtin imports
import logging
import os
import sys
import time
import threading

#External imports
import importlib
from Queue import Queue
import dataset

#Internal imports
import main
import interface

log = logging.getLogger()

dir_path = 'plugins'

plugin_subscriptions = []

command_plugins = {}

default_plugin_data = None

events_queue = Queue()

db = dataset.connect('sqlite:///will.db')

class subscriptions():
    '''Manage plugin subscriptions and events'''
    def call_plugin(self, plugin_function, event):
        '''Call the plugin'''
        log.debug("Calling function {0} with event data {1}".format(
            plugin_function, event
        ))
        #Call the plugin. If there's a response, return it. If there's not, return "Done"
        response = plugin_function(event)
        if not response:
            response = "Done"
        response = str(response)
        log.info("Plugin response is {0}".format(response))
        #Send the message
        interface.send_message(event["bot"],event["update"].message.chat.id,response)

    def subscriptions_thread(self):
        '''The seperate thread that monitors the events queue'''
        log.info("In subscriptions thread, starting loop")
        db = dataset.connect('sqlite:///will.db')
        user_data = db["userdata"]
        while True:
            time.sleep(0.1)
            #If the queue is empty, pass
            if not events_queue.empty():
                event = events_queue.get()
                assert type(event) == dict
                event_command = event["command"]
                username = event['update'].message.from_user.username
                log.info("Processing event with command {0}, user {1}".format(
                    event_command, username))
                user_table = user_data.find_one(username=username)
                event.update({"user_table":user_table})
                command_lower = event_command.lower()
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
                map(plugin_check, plugin_subscriptions)
                #How many plugins match the command data
                plugin_len = len(found_plugins)
                if plugin_len == 1:
                    plugin = found_plugins[0]
                    log.info("Running plugin {0}".format(plugin))
                    plugin_function = plugin['function']
                    #Call the plugin
                    self.call_plugin(plugin_function,event)
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
                        self.call_plugin(default_plugin_func, event)
                    else:
                        error_message = "Couldn't find defafult plugin {0} in plugin list {1}".format(
                            default_plugin, plugin_subscriptions
                        )
                        #Send the error message to the user
                        log.error(error_message)
                        interface.send_message(event["bot"], event["chat_data"]["chat_id"], error_message)

    def send_event(self, event):
        '''Take incoming event'''
        log.debug("Received event {0} of type {1}".format(
            event, type(event)
        ))
        assert(type(event) == dict)
        assert "command" in event.keys()
        command = event["command"]
        log.info("Putting event for command {0} in event queue".format(
            command
        ))
        events_queue.put(event)

    def initialize(self):
        '''Start the subscriptions thread'''
        log.info("Starting plugin subscription monitoring thread")
        s_thread = threading.Thread(target=self.subscriptions_thread)
        s_thread.start()
        log.info("Started subscriptions thread")

def process_plugins(path):
    '''Process and import the plugins'''
    log.info("Processing plugin {0}".format(path))
    python_loader = PythonLoader(path)
    try:
        python_loader.load()
    except IOError:
        return

def subscribe(subscription_data):
    '''Wrapper for adding plugins to my event system'''
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
        plugin_subscriptions.append(subscription_data)
    return wrap

def load(dir_path):
    '''Loads plugins'''
    log.info("Finding plugins in directory {0}".format(dir_path))
    plugins = lambda: (os.path.join(dir_path, module_path)
                       for module_path in os.listdir(dir_path))
    map_plugins(plugins())
    log.info("Finished parsing and loading plugins, processing subscriptions")
    subscriptions().initialize()
    log.info("Plugin initialization finished")

def map_plugins(plugin_paths):
    log.info("Mapping plugins to processing function")
    map(lambda plugin: process_plugins(plugin), plugin_paths)

class PythonLoader:
    '''The class that loads the plugins'''

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        if self.is_plugin():
            log.info("Loading plugin: {0}".format(self.file_path))
            self.update_path()
            importlib.import_module(self.import_name())

    def is_plugin(self, fs_tools=os.path):
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
        if self.file_path.endswith('.py'):
            return os.path.basename(self.file_path).split('.')[0]
        else:
            return os.path.basename(self.file_path)

    def update_path(self):
        lib_path = self._lib_path()
        if lib_path not in sys.path:
            sys.path.append(lib_path)

    def _lib_path(self):
        return os.path.normpath(
            os.sep.join(os.path.normpath(self.file_path).split(os.sep)[:-1])
        )



