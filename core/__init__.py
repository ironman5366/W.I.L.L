#Builtin modules
import logging
import os

#Internal modules
try:
    import core.plugin_handler as plugin_handler
except ImportError:
    import plugin_handler
    import parser
import core.notification as notification
from exceptions import *

log = logging.getLogger()

class core:
    def __init__(self, configuration_data):
        self.configuration_data = configuration_data
        plugin_configuration = self.configuration_data["plugins"]
        error_cause = None
        # Validate the plugin configuration
        try:
            error_cause = "dir"
            assert type(plugin_configuration["dir"]) == str
            assert os.path.isdir(plugin_configuration["dir"])
        except (KeyError, AssertionError):
            error_string = "Plugin configuration is invalid. Please check the {0} field.".format(error_cause)
            log.error(error_string)
            raise ConfigurationError(error_string)
        self.plugins = plugin_handler.load(plugin_configuration["dir"])

