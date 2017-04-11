#Builtin imports
# External imports
import importlib
import logging
import os
import sys

# Internal imports
from will.exceptions import *

log = logging.getLogger()

plugin_subscriptions = {}

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

def subscribe(name, check):
    """
    Provides a decorator for subscribing plugin to commands

    :param name: The unique name of the plugin
    :param check: A pointer to the function that will check if the plugin should be run for a command or event
    """

    def wrap(f):
        # Subscribe the plugin, and while processing them pluck out the default plugin
        # So it doesn't have to be searched for later
        assert type(name) == str
        assert callable(check)
        if name in plugin_subscriptions.keys():
            error_string = "Name {0} has already been registered in plugin subscriptions. Plugin names must be " \
                           "unique identifiers.".format(name)
            log.error(error_string)
            raise PluginError(error_string)
        else:
            subscription_data = {
                name:
                    {
                        "name": name,
                        "check": check,
                        "function": f
                    }
            }
            log.debug("Appending subscription data {0} to plugin subscriptions".format(subscription_data))
            plugin_subscriptions.update(subscription_data)
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

