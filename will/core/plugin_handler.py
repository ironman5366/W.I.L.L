#Builtin imports
import importlib
import logging
import os
import sys

# Internal imports
from will.exceptions import *

log = logging.getLogger()

plugin_subscriptions = []

plugin_names = []


class Plugin:
    """
    A basic plugin class. Implements the two required functions, exec and check.
    """

    name = None
    arguments = []
    response_arguments = []

    def exec(self, **kwargs):
        """
        Return the needed plugin value
        
        :param kwargs: The argument values, in key value format 
        
        """
        raise NotImplementedError("Master plugin class should not be executed")

    def check(self, command_obj):
        """
        Basic check to see if the command fits the plugin
        Check functions should be minimal and quick.
        
        :param command_obj: 
        :return bool: A bool defining whether the plugin fits the command
        """
        name_lower = self.name.lower()
        for word in command_obj.parsed:
            if word.lemma_.lower() == name_lower:
                return True
        return True


class ResponsePlugin:
    """
    A plugin that won't be called in normal conditions
    """
    def check(self):
        return False
class PythonLoader:
    '''The class that loads the plugins'''

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        """
        Use importlib to import the plugin file

        """
        if self.is_plugin():
            log.debug("Loading plugin: {0}".format(self.file_path))
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

def subscribe():
    """
    Provides a decorator for subscribing plugin to commands

    """

    def wrap(f):
        # Subscribe the plugin, and while processing them pluck out the default plugin
        # So it doesn't have to be searched for later
        assert type(f) == Plugin
        # Instantiate the plugin
        instantiated_plugin = f()
        # Get the plugin name and arguments
        name = instantiated_plugin.name
        if name in plugin_names:
            error_string = "Name {0} has already been registered in plugin subscriptions. Plugin names must be " \
                           "unique identifiers.".format(name)
            log.error(error_string)
            raise PluginError(error_string)
        else:
            plugin_subscriptions.append(instantiated_plugin)
            return f

    return wrap

def process_plugin(path):
    """
    Process and import the plugins

    :param path:
    """
    log.debug("Processing plugin {0}".format(path))
    python_loader = PythonLoader(path)
    try:
        python_loader.load()
    except IOError:
        return

def load(dir_path):
    """
    Run the plugin loader on processed plugins

    :param dir_path:
    """
    log.debug("Finding plugins in directory {0}".format(dir_path))
    plugins = [os.path.join(dir_path, module_path)
               for module_path in os.listdir(dir_path)]
    log.debug("Found {0} plugins".format(len(plugins)))
    [process_plugin(path) for path in plugins]
    return plugin_subscriptions

